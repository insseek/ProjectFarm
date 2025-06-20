from datetime import datetime, timedelta
from copy import deepcopy

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from projects.models import Project
from developers.models import DailyWork

from developers.tasks import build_project_gitlab_user_id_period_gitlab_commits


def projects_data_add_positions_gitlab_commits_data(projects_data, with_committers=True):
    if not projects_data:
        return projects_data
    # 七天前
    seven_days_ago_str = (datetime.now() - timedelta(days=7)).strftime(settings.DATE_FORMAT)
    today_str = datetime.now().strftime(settings.DATE_FORMAT)

    gitlab_projects = cache.get('gitlab-projects', {})
    gitlab_groups = cache.get('gitlab-groups', {})

    for project_data in projects_data:
        bind_gitlab = project_data.get('links', None)
        if bind_gitlab:
            gitlab_group_id = bind_gitlab.get("gitlab_group_id", None)
            gitlab_project_id = bind_gitlab.get("gitlab_project_id", None)
            gitlab_project = None
            if gitlab_group_id:
                gitlab_project = gitlab_groups.get(gitlab_group_id, {})
            elif gitlab_project_id:
                gitlab_project = gitlab_projects.get(gitlab_project_id, {})
            project_data["gitlab_project"] = gitlab_project
            project_data["links"]["gitlab_project"] = gitlab_project

        # 每个项目中每个职位的提交代码数据
        if project_data.get('gitlab_project', None):
            pass
        else:
            continue
        project_id = project_data['id']
        # 项目的所有职位
        job_positions = project_data['job_positions']
        for position in job_positions:
            gitlab_user_id = position['developer']['gitlab_user_id']
            if not gitlab_user_id:
                continue
            # 缓存数据
            project_user_commits_cache_key = 'p_{}_u_{}_gitlab_commits'.format(project_id, gitlab_user_id)
            if project_user_commits_cache_key in cache:
                position_gitlab_commits = cache.get(project_user_commits_cache_key)
            else:
                position_gitlab_commits = build_project_gitlab_user_id_period_gitlab_commits(project_id,
                                                                                             gitlab_user_id,
                                                                                             seven_days_ago_str,
                                                                                             today_str)
                cache.set(project_user_commits_cache_key, deepcopy(position_gitlab_commits), 60 * 60)
            position['gitlab_commits'] = position_gitlab_commits

            # 职位的提交人的数据
            if with_committers:
                gitlab_users = cache.get('gitlab-users', {})
                if gitlab_user_id in gitlab_users:
                    gitlab_user_data = gitlab_users[gitlab_user_id]
                    committer_list = gitlab_user_data['committers']
                    position['committers'] = committer_list
                    position['developer']['committers'] = committer_list
                    position['developer']['gitlab_user'] = gitlab_user_data
        # 项目的提交人数据
        if with_committers:
            farm_projects_git_commits = cache.get('farm_projects_git_commits', {})
            project_committers = []
            if project_id in farm_projects_git_commits:
                project_git_commits = farm_projects_git_commits[project_id]
                project_committers = project_git_commits.get('committers', [])
            project_data['committers'] = project_committers
    return projects_data


def build_projects_user_unread_comment_count(projects_data, user):
    user_id = user.id
    comments_dict = cache.get('projects_users_read_comments_dict', {})
    now = datetime.now()
    for project_data in projects_data:
        # 当前用户未读评论数量
        project_id = project_data['id']
        project = Project.objects.get(pk=project_id)
        last_view_at = now
        if comments_dict and user_id in comments_dict and project_id in comments_dict[user_id]:
            last_view_at = comments_dict[user_id][project_data['id']]['last_view_at']
        unread_count = project.comments.exclude(author_id=user_id).filter(created_at__gt=last_view_at).count()
        project_data['unread_comment_count'] = unread_count
    return projects_data


def projects_data_add_positions_daily_works_data(projects_data):
    '''
    该工程师今日、昨日、前日打卡数据
    :param projects_data:
    :return:
    '''
    today = timezone.now().date()
    today_str = today.strftime(settings.DATE_FORMAT)
    yesterday = timezone.now().date() - timedelta(days=1)
    yesterday_str = yesterday.strftime(settings.DATE_FORMAT)
    the_day_before_yesterday = timezone.now().date() - timedelta(days=2)
    before_yesterday_str = the_day_before_yesterday.strftime(settings.DATE_FORMAT)
    if projects_data:
        for project_data in projects_data:
            project_id = project_data['id']
            job_positions = project_data['job_positions']
            for position in job_positions:
                developer_id = position['developer']['id']
                cache_key_template = 'project_{}_{}_'.format(project_id, developer_id) + '{day_str}_daily_work'
                today_cache_key = cache_key_template.format(day_str=today_str)
                yesterday_cache_key = cache_key_template.format(day_str=yesterday_str)
                before_yesterday_cache_key = cache_key_template.format(day_str=before_yesterday_str)

                developer_daily_work = DailyWork.objects.filter(project_id=project_id,
                                                                developer_id=developer_id).exclude(status='pending')
                if before_yesterday_cache_key not in cache:
                    before_item = developer_daily_work.filter(day=the_day_before_yesterday).first()
                    before_data = {'status_display': before_item.status_display,
                                   'status': before_item.status} if before_item else None
                    cache.set(before_yesterday_cache_key, before_data, 60 * 60 * 24)
                else:
                    before_data = cache.get(before_yesterday_cache_key)

                if yesterday_cache_key not in cache:
                    yesterday_item = developer_daily_work.filter(day=yesterday).first()
                    yesterday_data = {'status_display': yesterday_item.status_display,
                                      'status': yesterday_item.status} if yesterday_item else None
                    cache.set(yesterday_cache_key, yesterday_data, 60 * 60 * 24 * 2)
                else:
                    yesterday_data = cache.get(yesterday_cache_key)

                if today_cache_key not in cache:
                    today_item = developer_daily_work.filter(day=today).first()
                    today_data = {'status_display': today_item.status_display,
                                  'status': today_item.status} if today_item else None
                    cache.set(today_cache_key, today_data, 60 * 60)
                else:
                    today_data = cache.get(today_cache_key)

                position['recent_daily_works'] = {
                    "today": today_data,
                    "yesterday": yesterday_data,
                    "the_day_before_yesterday": before_data,
                }
    return projects_data


def build_projects_user_daily_works_bugs_count(projects_data, user):
    top_user_id = user.top_user.id
    for project_data in projects_data:
        project_id = project_data['id']
        project = Project.objects.get(pk=project_id)
        # 缓存
        cache_key = 'p_{}_u_{}_unread_daily_works_count'.format(project_id, top_user_id)
        if cache_key not in cache:
            data = len(get_user_need_read_daily_works(user, project=project))
            cache.set(cache_key, data, 60 * 60 * 12)
        project_data['unread_daily_works_count'] = cache.get(cache_key)
        project_data['undone_bugs_count'] = project.bugs.filter(assignee_id=top_user_id,
                                                                status__in=['pending', 'fixed']).count()
    return projects_data


def get_user_need_read_daily_works(user, project=None):
    daily_works = []
    if project:
        if user.id in [project.manager_id, project.product_manager_id, project.tpm_id]:
            for d in project.daily_works.exclude(status="pending").filter(
                    day__gte=timezone.now().date() + timedelta(days=-7)):
                if not d.browsing_histories.filter(visitor_id=user.id).exists():
                    daily_works.append(d)
    else:
        for project in Project.ongoing_projects():
            if user.id in [project.manager_id, project.product_manager_id, project.tpm_id]:
                for d in project.daily_works.exclude(status="pending").filter(
                        day__gte=timezone.now().date() + timedelta(days=-7)):
                    if not d.browsing_histories.filter(visitor_id=user.id).exists():
                        daily_works.append(d)
    return daily_works
