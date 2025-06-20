# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from copy import deepcopy
from datetime import datetime, timedelta
from pprint import pprint
import json
from functools import wraps
import logging

from django.utils.decorators import available_attrs, decorator_from_middleware
from django.core.cache import cache
from django.conf import settings
from celery import shared_task

from geargitlab.gitlab_client import GitlabClient
from notifications.utils import create_notification

# from developers.models import Developer
# from projects.models import ProjectLinks, Project


logger = logging.getLogger()

LEVEL_CHOICES = {
    10: 'Guest',
    20: 'Report',
    30: 'Developer',
    40: 'Maintainer',
    50: 'Owner',
}


def clean_git_commits_issues(raise_exception=False):
    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(*args, **kwargs):
            result = view_func(*args, **kwargs)
            from projects.models import Project
            ongoing_project_ids = set(Project.ongoing_projects().values_list('id', flat=True))
            commits = cache.get('farm_projects_git_commits', {})
            issues = cache.get('farm_projects_git_issues', {})
            for project_id in list(commits.keys()):
                if project_id in ongoing_project_ids:
                    continue
                project = Project.objects.filter(pk=project_id)
                if project.exists():
                    project = project.first()
                    if project.done_at:
                        done_at_str = project.done_at.strftime('%Y-%m-%d')
                        previous_date_str = (datetime.now() - timedelta(days=8)).strftime('%Y-%m-%d')
                        if done_at_str < previous_date_str:
                            commits.pop(project_id, None)

            for project_id in list(issues.keys()):
                if project_id in ongoing_project_ids:
                    continue
                project = Project.objects.filter(pk=project_id)
                if project.exists():
                    project = project.first()
                    if project.done_at:
                        done_at_str = project.done_at.strftime('%Y-%m-%d')
                        previous_date_str = (datetime.now() - timedelta(days=15)).strftime('%Y-%m-%d')
                        if done_at_str < previous_date_str:
                            issues.pop(project_id, None)
            cache.set('farm_projects_git_commits', commits, None)
            cache.set('farm_projects_git_issues', issues, None)
            return result

        return _wrapped_view

    return decorator


# 用户相关开始

def get_gitlab_user_data(user_id):
    if not user_id:
        return
    gitlab_users = cache.get('gitlab-users', {})
    if user_id in gitlab_users:
        user_data = gitlab_users[user_id]
        if 'committers' not in user_data:
            user_data['committers'] = [{'committer_name': user_data['name'], 'committer_email': user_data['email']},
                                       {'committer_name': user_data['username'], 'committer_email': user_data['email']}]
            cache.set('gitlab-users', gitlab_users, None)
        return user_data
    return crawl_gitlab_user_data(user_id)


def get_gitlab_user_simple_data(user_id):
    if not user_id:
        return
    gitlab_users = cache.get('gitlab-users', {})
    if user_id in gitlab_users:
        user_data = gitlab_users[user_id]
    else:
        user_data = crawl_gitlab_user_data(user_id)
    if user_data:
        gitlab_user_data = {}
        fields = ["id", 'username', 'name', "state", 'web_url']
        for field in fields:
            gitlab_user_data[field] = user_data.get(field)
        return gitlab_user_data


def get_user_data(user):
    gitlab_user_data = {}
    fields = ["id", 'username', 'name', "state", "email", "is_admin", 'web_url']
    for field in fields:
        gitlab_user_data[field] = getattr(user, field)
    token = user.impersonationtokens.create({'name': 'farm_token', 'scopes': ['api']})
    gitlab_user_data['token'] = token.token
    gitlab_user_data['token_id'] = token.id

    gitlab_user_data['committers'] = [{'committer_name': user.name, 'committer_email': user.email},
                                      {'committer_name': user.username, 'committer_email': user.email}]
    return gitlab_user_data


def update_user_data(user, user_data, update_token=False):
    fields = ["id", 'username', 'name', "state", "email", "is_admin", 'web_url']
    for field in fields:
        user_data[field] = getattr(user, field)
    if update_token:
        token = user.impersonationtokens.create({'name': 'farm_token', 'scopes': ['api']})
        user_data['token'] = token.token
        user_data['token_id'] = token.id
    if 'committers' not in user_data:
        user_data['committers'] = [{'committer_name': user.name, 'committer_email': user.email},
                                   {'committer_name': user.username, 'committer_email': user.email}]
    return user_data


# 爬取所有活跃用户gitlab数据
@shared_task
def crawl_all_gitlab_active_users(update_token=False):
    gitlab_users = cache.get('gitlab-users', {})
    existed_user_set = set(gitlab_users.keys())
    if settings.GITLAB_ADMIN_PRIVATE_TOKEN:
        client = GitlabClient()

        all_active_users = client.get_all_active_users()
        active_user_set = set()

        for user in all_active_users:
            user_id = user.id
            if user_id in gitlab_users:
                new_user_data = deepcopy(gitlab_users[user_id])
                update_user_data(user, new_user_data, update_token=update_token)
            else:
                new_user_data = get_user_data(user)

            new_user_data['projects'] = []
            new_user_data['groups'] = []
            if new_user_data['state'] == 'active':
                try:
                    projects, groups = client.get_user_projects_groups(private_token=new_user_data['token'])
                    new_user_data['projects'] = [project.id for project in projects]
                    new_user_data['groups'] = [group.id for group in groups]
                except Exception as e:
                    logger.error(str(e))

            active_user_set.add(user_id)
            gitlab_users[user_id] = new_user_data

        blocked_user_set = existed_user_set - active_user_set
        for user_id in blocked_user_set:
            user = client.get_user(user_id=user_id)
            if user:
                new_user_data = deepcopy(gitlab_users[user_id])
                update_user_data(user, new_user_data, update_token=update_token)
                new_user_data['projects'] = []
                new_user_data['groups'] = []
                if new_user_data['state'] == 'active':
                    try:
                        projects, groups = client.get_user_projects_groups(private_token=new_user_data['token'])
                        new_user_data['projects'] = [project.id for project in projects]
                        new_user_data['groups'] = [group.id for group in groups]
                    except Exception as e:
                        logger.error(str(e))

                gitlab_users[user_id] = new_user_data
        cache.set('gitlab-users', gitlab_users, None)
    return gitlab_users


# 更新单个用户的gitlab数据
@shared_task
def crawl_gitlab_user_data(user_id):
    gitlab_users = cache.get('gitlab-users', {})
    gitlab_projects = cache.get('gitlab-projects', {})
    gitlab_groups = cache.get('gitlab-groups', {})
    new_user_data = None
    if settings.GITLAB_ADMIN_PRIVATE_TOKEN:
        client = GitlabClient()
        user = client.get_user(user_id=user_id)
        if user:
            if user_id in gitlab_users:
                new_user_data = deepcopy(gitlab_users[user_id])
                update_user_data(user, new_user_data)
            else:
                new_user_data = get_user_data(user)

            new_user_data['projects'] = []
            new_user_data['groups'] = []
            if new_user_data['state'] == 'active':
                try:
                    projects, groups = client.get_user_projects_groups(private_token=new_user_data['token'])
                    for project in projects:
                        if project.id not in gitlab_projects:
                            gitlab_projects[project.id] = get_project_data(project)
                        new_user_data['projects'].append(project.id)

                    for group in groups:
                        if group.id not in gitlab_groups:
                            gitlab_groups[group.id] = get_group_data(group)
                        new_user_data['groups'].append(group.id)
                except Exception as e:
                    logger.error(str(e))

            gitlab_users[user_id] = new_user_data
            cache.set('gitlab-users', gitlab_users, None)
            cache.set('gitlab-projects', gitlab_projects, None)
            cache.set('gitlab-groups', gitlab_groups, None)
    return new_user_data


# 用户相关结束


def get_gitlab_project_members(project):
    members = project.members.list(all=True)
    owner = project.owner if hasattr(project, 'owner') else None
    project_member_data = {}
    for member in members:
        member_data = {}
        fields = ["id", 'username', 'name', "state", 'web_url', 'access_level']
        for field in fields:
            member_data[field] = getattr(member, field)
        member_data['access_level_display'] = LEVEL_CHOICES.get(member_data['access_level'], None)
        project_member_data[member.id] = member_data
    if owner:
        if owner['id'] not in project_member_data:
            project_member_data[owner['id']] = owner
        project_member_data[owner['id']]['access_level'] = 50
        project_member_data[owner['id']]['access_level_display'] = LEVEL_CHOICES[50]
    return project_member_data


def get_gitlab_project_data(project_id):
    gitlab_projects = cache.get('gitlab-projects', {})
    if project_id in gitlab_projects:
        return gitlab_projects[project_id]
    return crawl_gitlab_project_data(project_id)


def get_gitlab_group_data(group_id):
    gitlab_groups = cache.get('gitlab-groups', {})
    if group_id in gitlab_groups:
        return gitlab_groups[group_id]
    return crawl_gitlab_group_data(group_id)


def get_project_data(project):
    project_data = {'type': 'project'}
    fields = ["id", 'name_with_namespace', 'name', "web_url"]
    for field in fields:
        project_data[field] = getattr(project, field)
    project_data['members'] = get_gitlab_project_members(project)
    return project_data


def get_group_data(group):
    group_data = {'type': 'group'}
    fields = ["id", 'name', "web_url"]
    for field in fields:
        group_data[field] = getattr(group, field)
    group_data['members'] = get_gitlab_project_members(group)
    group_data['projects'] = [project.id for project in group.projects.list(all=True)]
    return group_data


# 更新所有项目的gitlab数据
@shared_task
def crawl_all_gitlab_projects():
    gitlab_projects = cache.get('gitlab-projects', {})
    gitlab_groups = cache.get('gitlab-groups', {})

    if settings.GITLAB_ADMIN_PRIVATE_TOKEN:
        client = GitlabClient()
        all_projects = client.get_all_projects()
        all_groups = client.get_all_groups()

        for project in all_projects:
            gitlab_projects[project.id] = get_project_data(project)

        for group in all_groups:
            gitlab_groups[group.id] = get_group_data(group)

        cache.set('gitlab-projects', gitlab_projects, None)
        cache.set('gitlab-groups', gitlab_groups, None)

    return (gitlab_projects, gitlab_groups)


@shared_task
def crawl_gitlab_project_data(project_id):
    if not settings.GITLAB_ADMIN_PRIVATE_TOKEN:
        return
    gitlab_projects = cache.get('gitlab-projects', {})
    client = GitlabClient()
    project = client.get_project(project_id=project_id)
    if project:
        project_data = get_project_data(project)
        gitlab_projects[project.id] = project_data
        cache.set('gitlab-projects', gitlab_projects, None)
        return project_data


@shared_task
def crawl_gitlab_group_data(group_id):
    if not settings.GITLAB_ADMIN_PRIVATE_TOKEN:
        return
    gitlab_groups = cache.get('gitlab-groups', {})
    client = GitlabClient()
    group = client.get_group(group_id=group_id)
    if group:
        group_data = get_group_data(group)
        gitlab_groups[group.id] = group_data
        cache.set('gitlab-groups', gitlab_groups, None)
        return group_data


@shared_task
def crawl_recent_updated_gitlab_projects():
    if not settings.GITLAB_ADMIN_PRIVATE_TOKEN:
        return
    gitlab_projects = cache.get('gitlab-projects', {})
    gitlab_groups = cache.get('gitlab-groups', {})

    group_id_set = set()
    project_group_id_set = set()

    client = GitlabClient()
    groups = client.get_groups(per_page=30)
    projects = client.get_projects(per_page=30, order_by='updated_at', sort='desc')

    for project in projects:
        if project.namespace and project.namespace.get('kind', None) == 'group':
            project_group_id_set.add(project.namespace['id'])
        gitlab_projects[project.id] = get_project_data(project)

    for group in groups:
        gitlab_groups[group.id] = get_group_data(group)
        group_id_set.add(group.id)
    for group_id in project_group_id_set:
        if group_id not in group_id_set:
            group = client.get_group(group_id)
            gitlab_groups[group.id] = get_group_data(group)

    cache.set('gitlab-projects', gitlab_projects, None)
    cache.set('gitlab-groups', gitlab_groups, None)


def check_farm_project_gitlab_project(farm_project_id=None, project=None):
    if not farm_project_id and not project:
        return
    from projects.models import ProjectLinks
    farm_projects_git_commits = cache.get('farm_projects_git_commits', {})
    farm_projects_git_issues = cache.get('farm_projects_git_issues', {})
    if project:
        farm_project_id = project.id
    project_links = ProjectLinks.objects.filter(project_id=farm_project_id)
    if not project_links.exists():
        farm_projects_git_commits.pop(farm_project_id, None)
        farm_projects_git_issues.pop(farm_project_id, None)
        cache.set('farm_projects_git_commits', farm_projects_git_commits, None)
        cache.set('farm_projects_git_issues', farm_projects_git_issues, None)
        return
    project_links = project_links.first()
    if not project_links.gitlab_group_id and not project_links.gitlab_project_id:
        farm_projects_git_commits.pop(farm_project_id, None)
        farm_projects_git_issues.pop(farm_project_id, None)
        cache.set('farm_projects_git_commits', farm_projects_git_commits, None)
        cache.set('farm_projects_git_issues', farm_projects_git_issues, None)
        return
    farm_project = project_links.project
    return farm_project


# 清除已完成项目的测试数据
# def build_ongoing_projects_commits_issues(projects):
#     git_commits = cache.get('farm_projects_git_commits', {})
#     git_issues = cache.get('farm_projects_git_issues', {})
#     new_commits = {}
#     new_issues = {}
#     project_keys = set(projects.values_list('id', flat=True))
#     for project_id in project_keys:
#         if project_id in git_commits:
#             new_commits[project_id] = git_commits[project_id]
#         if project_id in git_issues:
#             new_issues[project_id] = git_issues[project_id]
#     cache.set('farm_projects_git_commits', new_commits, None)
#     cache.set('farm_projects_git_issues', new_issues, None)


# 多项目 昨天 commits
@shared_task
def crawl_farm_projects_yesterday_git_commits():
    yesterday = datetime.today().date() - timedelta(days=1)
    crawl_farm_projects_day_git_commits(yesterday)


# 多项目 今天 commits
@shared_task
def crawl_farm_projects_today_git_commits():
    today = datetime.today().date()
    crawl_farm_projects_day_git_commits(today)


# 多项目一天 commits
def crawl_farm_projects_day_git_commits(day):
    from projects.models import Project
    ongoing_projects = Project.ongoing_projects()

    craw_dict = {}
    for project in ongoing_projects:
        farm_project = check_farm_project_gitlab_project(project=project)
        if not farm_project:
            continue
        git_group = farm_project.links.gitlab_group_id
        git_project = farm_project.links.gitlab_project_id
        if not any([git_group, git_project]):
            continue
        craw_key = 'group-{}'.format(git_group) if git_group else 'project-{}'.format(git_project)
        if craw_key in craw_dict:
            exist_farm_project_id = craw_dict[craw_key]['farm_project']
            farm_projects_git_commits = cache.get('farm_projects_git_commits', {})
            commits_data = farm_projects_git_commits.get(exist_farm_project_id, {})
            farm_projects_git_commits[farm_project.id] = deepcopy(commits_data)
            cache.set('farm_projects_git_commits', farm_projects_git_commits, None)

            continue

        crawl_farm_project_day_git_commits(farm_project.id, day, need_check=False)
        craw_dict[craw_key] = {'farm_project': farm_project.id}


# # 多项目多天 commits
@shared_task
def crawl_farm_projects_recent_days_git_commits(days_num=7):
    from projects.models import Project
    ongoing_projects = Project.ongoing_projects()

    # 多个项目绑定同一个gitlab项目
    craw_dict = {}

    for project in ongoing_projects:
        farm_project = check_farm_project_gitlab_project(project=project)
        if not farm_project:
            continue
        git_group = farm_project.links.gitlab_group_id
        git_project = farm_project.links.gitlab_project_id
        if not any([git_group, git_project]):
            continue
        craw_key = 'group-{}'.format(git_group) if git_group else 'project-{}'.format(git_project)
        if craw_key in craw_dict:
            exist_farm_project_id = craw_dict[craw_key]['farm_project']
            farm_projects_git_commits = cache.get('farm_projects_git_commits', {})
            data = farm_projects_git_commits.get(exist_farm_project_id, {})
            farm_projects_git_commits[farm_project.id] = deepcopy(data)
            cache.set('farm_projects_git_commits', farm_projects_git_commits, None)
            continue
        crawl_farm_project_recent_days_git_commits(farm_project.id, days_num=days_num, need_check=False)
        craw_dict[craw_key] = {'farm_project': farm_project.id}


# 单个项目多天 commits
@shared_task
def crawl_farm_project_recent_days_git_commits(project_id, days_num=7, need_check=True):
    if need_check:
        farm_project = check_farm_project_gitlab_project(project_id)
        if not farm_project:
            return
    for timedelta_day in range(days_num):
        today = datetime.today().date()
        day = today - timedelta(days=timedelta_day)
        crawl_farm_project_day_git_commits(project_id, day, need_check=False)


# 单个项目 一天 commits
def crawl_farm_project_day_git_commits(farm_project_id, day, need_check=True):
    if need_check:
        farm_project = check_farm_project_gitlab_project(farm_project_id)
        if not farm_project:
            return
    from projects.models import ProjectLinks
    project_links = ProjectLinks.objects.get(project_id=farm_project_id)
    farm_project = project_links.project
    farm_projects_git_commits = cache.get('farm_projects_git_commits', {})
    gitlab_client = GitlabClient()
    day_str = day.strftime(settings.DATE_FORMAT)

    git_project_ids = set()
    if project_links.gitlab_group_id:
        git_group_data = get_gitlab_group_data(project_links.gitlab_group_id)
        if git_group_data:
            git_project_ids = set(git_group_data['projects'])
    elif project_links.gitlab_project_id:
        git_project_ids.add(project_links.gitlab_project_id)

    if farm_project_id not in farm_projects_git_commits:
        farm_projects_git_commits[farm_project_id] = {'name': farm_project.name, 'every_data': {},
                                                      'committers': []}
    every_data = farm_projects_git_commits[farm_project_id]['every_data']
    committers = farm_projects_git_commits[farm_project_id]['committers']
    every_data[day_str] = {}
    for git_project_id in git_project_ids:
        commits_data = gitlab_client.get_project_day_commits_data(day, project_id=git_project_id)
        if commits_data:
            every_data[day_str][git_project_id] = commits_data
            for commit in commits_data.values():
                committer_name = commit['committer_name']
                committer_email = commit['committer_email']
                committer = {'committer_name': committer_name, 'committer_email': committer_email}
                if committer not in committers:
                    committers.append(committer)
    cache.set('farm_projects_git_commits', farm_projects_git_commits, None)
    return farm_projects_git_commits


# 多项目 昨天 issues
@shared_task
def crawl_farm_projects_yesterday_git_issues():
    yesterday = datetime.today().date() - timedelta(days=1)
    crawl_farm_projects_day_git_issues(yesterday)


# 多项目 今天 issues
@shared_task
def crawl_farm_projects_today_git_issues():
    today = datetime.today().date()
    crawl_farm_projects_day_git_issues(today)


# 多项目一天 issues
def crawl_farm_projects_day_git_issues(day):
    from projects.models import Project
    ongoing_projects = Project.ongoing_projects()
    craw_dict = {}
    for project in ongoing_projects:
        farm_project = check_farm_project_gitlab_project(project=project)
        if not farm_project:
            continue
        git_group = farm_project.links.gitlab_group_id
        git_project = farm_project.links.gitlab_project_id
        if not any([git_group, git_project]):
            continue
        craw_key = 'group-{}'.format(git_group) if git_group else 'project-{}'.format(git_project)
        if craw_key in craw_dict:
            exist_farm_project_id = craw_dict[craw_key]['farm_project']
            farm_projects_git_issues = cache.get('farm_projects_git_issues', {})
            data = farm_projects_git_issues.get(exist_farm_project_id, {})
            farm_projects_git_issues[farm_project.id] = deepcopy(data)
            cache.set('farm_projects_git_issues', farm_projects_git_issues, None)
            continue
        crawl_farm_project_day_git_issues(farm_project.id, day, need_check=False)
        craw_dict[craw_key] = {'farm_project': farm_project.id}


# # 多项目多天 issues
@shared_task
def crawl_farm_projects_recent_days_git_issues(days_num=14):
    from projects.models import Project
    ongoing_projects = Project.ongoing_projects()
    from django.core.mail import send_mail
    first_msg = json.dumps(list(ongoing_projects.values('id', 'name')), ensure_ascii=False)
    send_mail(
        subject='请注意这是Django邮件测试',
        message=first_msg,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=["fanping@chilunyc.com"]
    )

    craw_dict = {}
    for project in ongoing_projects:
        farm_project = check_farm_project_gitlab_project(project=project)
        if not farm_project:
            continue
        git_group = farm_project.links.gitlab_group_id
        git_project = farm_project.links.gitlab_project_id
        if not any([git_group, git_project]):
            continue
        craw_key = 'group-{}'.format(git_group) if git_group else 'project-{}'.format(git_project)
        if craw_key in craw_dict:
            exist_farm_project_id = craw_dict[craw_key]['farm_project']
            farm_projects_git_issues = cache.get('farm_projects_git_issues', {})
            issues_data = farm_projects_git_issues.get(exist_farm_project_id, {})
            farm_projects_git_issues[farm_project.id] = deepcopy(issues_data)
            cache.set('farm_projects_git_issues', farm_projects_git_issues, None)
            continue

        crawl_farm_project_recent_days_git_issues(farm_project.id, days_num=days_num, need_check=False)
        craw_dict[craw_key] = {'farm_project': farm_project.id}
    issues = cache.get('farm_projects_git_issues', {})

    msg = json.dumps(issues, ensure_ascii=False)
    send_mail(
        subject='请注意这是Django邮件测试',
        message=msg,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=["fanping@chilunyc.com"]
    )


# 单个项目多天 issues
@shared_task
def crawl_farm_project_recent_days_git_issues(project_id, days_num=14, need_check=True):
    if need_check:
        farm_project = check_farm_project_gitlab_project(project_id)
        if not farm_project:
            return
    for timedelta_day in range(days_num):
        today = datetime.today().date()
        day = today - timedelta(days=timedelta_day)
        crawl_farm_project_day_git_issues(project_id, day, need_check=False)


# 单个项目 一天 issues
def crawl_farm_project_day_git_issues(farm_project_id, day, need_check=True):
    if need_check:
        farm_project = check_farm_project_gitlab_project(farm_project_id)
        if not farm_project:
            return
    from projects.models import ProjectLinks
    project_links = ProjectLinks.objects.get(project_id=farm_project_id)
    farm_project = project_links.project
    farm_projects_git_issues = cache.get('farm_projects_git_issues', {})
    gitlab_client = GitlabClient()
    day_str = day.strftime(settings.DATE_FORMAT)

    if farm_project_id not in farm_projects_git_issues:
        farm_projects_git_issues[farm_project_id] = {'name': farm_project.name, 'id': farm_project.id, 'every_data': {},
                                                     'opened_issues': []}
    farm_project_git_issues = farm_projects_git_issues[farm_project_id]

    link_git_group_id = project_links.gitlab_group_id
    link_project_id = project_links.gitlab_project_id

    every_data = farm_project_git_issues['every_data']
    every_data[day_str] = {"opened_issues": [], "closed_issues": []}

    if link_git_group_id:
        opened_issues = gitlab_client.get_group_opened_issues_data(group_id=link_git_group_id)
        if opened_issues:
            farm_project_git_issues['opened_issues'] = opened_issues

        issues_data = gitlab_client.get_group_day_issues_data(day, group_id=link_git_group_id)
        if issues_data:
            every_data[day_str] = issues_data

    elif link_project_id:
        opened_issues = gitlab_client.get_project_opened_issues_data(project_id=link_project_id)
        if opened_issues:
            farm_project_git_issues['opened_issues'] = opened_issues

        issues_data = gitlab_client.get_project_day_issues_data(day, project_id=link_project_id)
        if issues_data:
            every_data[day_str] = issues_data

    cache.set('farm_projects_git_issues', farm_projects_git_issues, None)
    return farm_projects_git_issues


# 单个项目多天 commits issues
@shared_task
def crawl_farm_project_recent_days_git_commits_issues(project_id, days_num=7):
    farm_project = check_farm_project_gitlab_project(project_id)
    if farm_project:
        for timedelta_day in range(days_num):
            today = datetime.today().date()
            day = today - timedelta(days=timedelta_day)
            crawl_farm_project_day_git_commits(project_id, day, need_check=False)
            crawl_farm_project_day_git_issues(project_id, day, need_check=False)


# 进行中项目最近半小时demo commits
@shared_task
def crawl_farm_projects_recent_half_hour_git_demo_commits():
    farm_projects_demo_status = cache.get('farm_projects_demo_status', {})
    gitlab_client = GitlabClient()
    from projects.models import Project
    ongoing_projects = Project.ongoing_projects()
    craw_dict = {}
    for project in ongoing_projects:
        farm_project = check_farm_project_gitlab_project(project=project)
        if not farm_project:
            continue
        gitlab_group_id = farm_project.links.gitlab_group_id
        gitlab_project_id = farm_project.links.gitlab_project_id
        if not any([gitlab_group_id, gitlab_project_id]):
            continue
        craw_key = 'group-{}'.format(gitlab_group_id) if gitlab_group_id else 'project-{}'.format(gitlab_project_id)
        if craw_key in craw_dict:
            exist_farm_project_id = craw_dict[craw_key]['farm_project']
            farm_projects_demo_status[farm_project.id] = deepcopy(farm_projects_demo_status[exist_farm_project_id])
            continue

        farm_project_demo_status = farm_projects_demo_status.get(farm_project.id, {
            "status": "normal",
            "modified_at": datetime.now().strftime(
                settings.DATETIME_FORMAT),
            "last_commit": None,
            "need_alert": False
        })
        commits = []
        last_commit = None
        if gitlab_group_id:
            commits = gitlab_client.get_group_commits(group_id=gitlab_group_id,
                                                      start_time=datetime.now() - timedelta(minutes=30),
                                                      end_time=datetime.now(), ref_name='staging')
        elif gitlab_project_id:
            commits = gitlab_client.get_project_commits(project_id=gitlab_project_id,
                                                        start_time=datetime.now() - timedelta(minutes=30),
                                                        end_time=datetime.now(), ref_name='staging')

        if commits:
            commits = sorted(commits, key=lambda x: x.created_at, reverse=True)
        if commits:
            last_commit = commits[0]

        exists_commit_id = farm_project_demo_status['last_commit']['id'] if farm_project_demo_status[
            'last_commit'] else None

        if last_commit and exists_commit_id != last_commit.id:
            farm_project_demo_status['last_commit'] = last_commit.attributes

            if not farm_project.demo_status or farm_project.demo_status['status'] != 'maintaining':
                farm_project_demo_status['need_alert'] = True
                if farm_project.manager and farm_project.manager.is_active:
                    site_host = '' if settings.DEVELOPMENT else settings.SITE_URL
                    notification_url = site_host + '/'
                    content = "项目【{}】demo服务器有代码更新，请确认是否打开项目维护状态".format(farm_project.name)
                    create_notification(farm_project.manager, content, notification_url)

        farm_projects_demo_status[farm_project.id] = deepcopy(farm_project_demo_status)
        craw_dict[craw_key] = {'farm_project': farm_project.id}

    cache.set('farm_projects_demo_status', farm_projects_demo_status, None)
    return farm_projects_demo_status


# 单个项目最近半小时demo commits
@shared_task
def crawl_farm_project_recent_half_hour_git_demo_commits(project_id):
    farm_projects_demo_status = cache.get('farm_projects_demo_status', {})

    gitlab_client = GitlabClient()
    farm_project = check_farm_project_gitlab_project(project_id)
    if farm_project:
        gitlab_group_id = farm_project.links.gitlab_group_id
        gitlab_project_id = farm_project.links.gitlab_project_id
        if not any([gitlab_group_id, gitlab_project_id]):
            return
        farm_project_demo_status = farm_projects_demo_status.get(project_id, {
            "status": "normal",
            "modified_at": datetime.now().strftime(
                settings.DATETIME_FORMAT),
            "last_commit": None,
            "need_alert": False
        })
        commits = []
        last_commit = None
        if gitlab_group_id:
            commits = gitlab_client.get_group_commits(group_id=gitlab_group_id,
                                                      start_time=datetime.now() - timedelta(minutes=40),
                                                      end_time=datetime.now(), ref_name='staging', with_stats=False)
        elif gitlab_project_id:
            commits = gitlab_client.get_project_commits(project_id=gitlab_project_id,
                                                        start_time=datetime.now() - timedelta(minutes=40),
                                                        end_time=datetime.now(), ref_name='staging', with_stats=False)
        commits = sorted(commits, key=lambda x: x.created_at, reverse=True)
        if commits:
            last_commit = commits[0]

        exists_commit_id = farm_project_demo_status['last_commit']['id'] if farm_project_demo_status[
            'last_commit'] else None
        if last_commit and exists_commit_id != last_commit.id:
            farm_project_demo_status['last_commit'] = last_commit.attributes
            if not farm_project.demo_status or farm_project.demo_status['status'] != 'maintaining':
                farm_project_demo_status['need_alert'] = True
                if farm_project.manager and farm_project.manager.is_active:
                    site_host = '' if settings.DEVELOPMENT else settings.SITE_URL
                    notification_url = site_host + '/'
                    content = "项目【{}】demo服务器有代码更新，请确认是否打开项目维护状态".format(farm_project.name)
                    create_notification(farm_project.manager, content, notification_url)
        farm_projects_demo_status[farm_project.id] = deepcopy(farm_project_demo_status)

    cache.set('farm_projects_demo_status', farm_projects_demo_status, None)
    return farm_projects_demo_status


@shared_task
def reset_gitlab_data():
    cache.delete('farm_projects_git_issues')
