# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from celery import shared_task
from datetime import datetime, timedelta
from copy import deepcopy
from pprint import pprint
import re
import json

from django.core.cache import cache
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.shortcuts import reverse

from developers.serializers import DailyWorkWithNextDaySimpleSerializer
from developers.models import Developer, DailyWork, DocumentVersion
from farmbase.models import Team
from developers.utils import get_need_submit_daily_work
from projects.models import Project
from notifications.utils import create_notification, send_feishu_card_message_to_user, create_developer_notification
from notifications.tasks import send_feishu_message_to_all, send_feishu_message_to_individual
from developers.quip_document_html_parser import HTMLParser
from oauth.quip_utils import get_folders_docs
from geargitlab.tasks import get_gitlab_user_data

DEVELOPERS_EXTRA_CACHE_KEY = "developers-extra-data"


# 工程师一些额外数据  进行缓存
#  employability, -active_projects_len, -done_at_num, star_rating, project_total
#  可分配值、进行中项目数、最近完成项目完成时间、综合评分、参与的项目总数、合作伙伴
@shared_task
def update_developer_cache_data(developer_id):
    cache_key = DEVELOPERS_EXTRA_CACHE_KEY
    developer = Developer.objects.get(pk=developer_id)
    developers_data = cache.get(cache_key, {})
    developer_data = build_developer_cache_data(developer)
    developers_data[developer.id] = developer_data
    cache.set(cache_key, developers_data, None)
    return developers_data[developer.id]


def build_developer_cache_data(developer):
    employability = developer.employability
    partners = developer.get_partners()
    active_projects_count = developer.active_projects().count()
    project_done_date_str = developer.last_project.done_at.strftime(
        settings.DATETIME_FORMAT) if developer.last_project else None
    star_rating = developer.rebuild_star_rating()
    project_total = developer.project_total
    developer_data = {
        "employability": employability,
        "partners": partners,
        "star_rating": star_rating,
        "active_projects_count": active_projects_count,
        "last_project_done_date_str": project_done_date_str,
        "project_total": project_total
    }
    average_star_rating = star_rating['average'] if star_rating else 0
    done_at_num = int(re.sub(r"\D", "", project_done_date_str)) if project_done_date_str else 0
    employability_group = [employability, -active_projects_count, -done_at_num, average_star_rating, project_total]
    developer_data["employability_group"] = employability_group
    return developer_data


@shared_task
def update_developer_partners_cache_data(developer_id):
    developer = Developer.objects.get(pk=developer_id)
    developers_data = cache.get(DEVELOPERS_EXTRA_CACHE_KEY, {})
    if developer.id not in developers_data:
        update_developer_cache_data(developer)
    else:
        developers_data[developer.id]['partners'] = partners
    cache.set(DEVELOPERS_EXTRA_CACHE_KEY, developers_data, None)
    return partners


@shared_task
def update_developer_rate_cache_data(developer_id):
    developer = Developer.objects.get(pk=developer_id)
    rate = developer.rebuild_star_rating()
    developers_data = cache.get(DEVELOPERS_EXTRA_CACHE_KEY, {})
    if developer.id not in developers_data:
        update_developer_cache_data(developer)
    else:
        developers_data[developer.id]['star_rating'] = rate
    cache.set(DEVELOPERS_EXTRA_CACHE_KEY, developers_data, None)
    return rate


@shared_task
def update_all_developers_cache_data():
    developers_data = cache.get(DEVELOPERS_EXTRA_CACHE_KEY, {})
    developers = Developer.objects.all()
    for developer in developers:
        developer_data = build_developer_cache_data(developer)
        developers_data[developer.id] = developer_data
    cache.set(DEVELOPERS_EXTRA_CACHE_KEY, developers_data, None)
    return developers_data


@shared_task
def update_active_developers_cache_data():
    developers_data = cache.get(DEVELOPERS_EXTRA_CACHE_KEY, {})
    developers = Developer.objects.exclude(status='0')
    for developer in developers:
        developer_data = build_developer_cache_data(developer)
        developers_data[developer.id] = developer_data
    cache.set(DEVELOPERS_EXTRA_CACHE_KEY, developers_data, None)
    return developers_data


@shared_task
def build_yesterday_daily_work_gitlab_commits():
    yesterday = timezone.now().date() - timedelta(days=1)
    queryset = DailyWork.objects.filter(day=yesterday)
    queryset = DailyWork.valid_daily_works(queryset=queryset)
    for obj in queryset:
        project_id = obj.project_id
        gitlab_user_id = obj.developer.gitlab_user_id
        if gitlab_user_id:
            gitlab_commits = build_project_gitlab_user_id_day_gitlab_commits(project_id,
                                                                             gitlab_user_id,
                                                                             yesterday,
                                                                             with_commits=True)
            if gitlab_commits:
                obj.gitlab_commits = json.dumps(gitlab_commits, ensure_ascii=False)
                obj.save()


@shared_task
def build_yesterday_daily_work_absence_statistics():
    yesterday = timezone.now().date() - timedelta(days=1)
    ongoing_projects = Project.ongoing_projects()
    for project in ongoing_projects:
        developers = project.get_active_developers()
        for developer in developers:
            daily_work = DailyWork.objects.filter(project_id=project.id, developer_id=developer.id,
                                                  day=yesterday).first()
            if daily_work and daily_work.status in ['postpone', 'normal']:
                continue
            need_submit_daily_work = get_need_submit_daily_work(project, developer, yesterday)
            if need_submit_daily_work:
                daily_work, created = DailyWork.objects.get_or_create(project_id=project.id,
                                                                      developer_id=developer.id,
                                                                      day=yesterday)
                daily_work.status = 'absence'
                daily_work.need_submit_daily_work = True
                daily_work.save()


def build_project_daily_works_message(project_data):
    message = ''  # 站内消息
    feishu_card_fields = []  # 飞书消息
    if project_data['developers']:
        project_title = '【{}】'.format(project_data['name'])
        feishu_card_fields.append(project_title)
        message += '{}\n'.format(project_title)
        for developer_name, data in project_data['developers'].items():
            daily_work_data = data['daily_work']
            gitlab_commits = data['gitlab_commits']
            if daily_work_data:
                status = daily_work_data.get('status', 'normal')
                next_day_work = daily_work_data['next_day_work']
                leave_at = next_day_work.get('leave_at', None)
                return_at = next_day_work.get('return_at', None)
                status_display = "任务延期" if status == 'postpone' else '任务正常完成'
                if leave_at and return_at:
                    developer_msg = '{developer_name}:日报{status} 明日不在线时间：{leave_at}～{return_at}'.format(
                        developer_name=developer_name,
                        status=status_display,
                        leave_at=leave_at,
                        return_at=return_at)
                else:
                    developer_msg = '{}:日报{}'.format(developer_name, status_display)
            else:
                developer_msg = '{}:日报{}'.format(developer_name, "未提交")

            gitlab_commits_msg = "；代码未提交"
            if gitlab_commits and gitlab_commits['recent_committed_count']:
                gitlab_commits_msg = '；代码{}个commit、增加{}行、删除{}行'.format(
                    gitlab_commits['recent_committed_count'],
                    gitlab_commits['additions'],
                    gitlab_commits['deletions']
                )
            developer_msg += gitlab_commits_msg
            message += '{}\n'.format(developer_msg)
            feishu_card_fields.append(developer_msg)
    return message, feishu_card_fields


# 发送工程师日报给项目经理和TPM
@shared_task
def send_project_developer_daily_works_to_manager_and_tpm(to_send=True):
    today = timezone.now().date()
    today_str = today.strftime(settings.DATE_FORMAT)
    # # 周末不发送
    # if today.weekday() >= 5:
    #     return
    # 每个用户需要被提醒的项目
    users_projects_data = {}
    # 每个项目对应的日报数据
    projects_daily_works = {}
    # 每个项目对应的日报消息
    projects_messages = {}
    # #
    message_data_list = []

    user_message_dict = {}

    # 每个项目的工程师日报数据
    for project in Project.ongoing_projects():
        project_id = project.id
        # 项目中的工程师
        developers = project.get_active_developers()
        developers = set(developers)
        if developers:
            # 项目工程师的当天日报
            project_developers = {"id": project_id, 'name': project.name, "developers": {}}
            developers_data = project_developers['developers']
            for developer in developers:
                developer_name = developer.name
                if developer_name not in developers_data:
                    daily_work = DailyWork.objects.filter(project_id=project.id, developer_id=developer.id,
                                                          day=today).first()

                    daily_work = daily_work if daily_work and daily_work.status in ['postpone', 'normal'] else None

                    # 已写日报
                    if daily_work:
                        developers_data[developer_name] = {"daily_work": None, "gitlab_commits": None}
                        developers_data[developer_name]['daily_work'] = DailyWorkWithNextDaySimpleSerializer(
                            daily_work).data
                    else:
                        need_submit_daily_work = get_need_submit_daily_work(project, developer, today)
                        if not need_submit_daily_work:
                            continue
                        developers_data[developer_name] = {"daily_work": None, "gitlab_commits": None}
                    if developer.gitlab_user_id:
                        gitlab_user_id = developer.gitlab_user_id
                        gitlab_commits = build_project_gitlab_user_id_day_gitlab_commits(project_id,
                                                                                         gitlab_user_id,
                                                                                         today)
                        developers_data[developer_name]['gitlab_commits'] = gitlab_commits

            # 项目经理/TPM 对应的项目
            if developers_data:
                for member in set([project.manager, project.tpm]):
                    if member and member.is_active:
                        if member.id not in users_projects_data:
                            users_projects_data[member.id] = []
                        users_projects_data[member.id].append(project.id)
                # projects_daily_works[project.id] = project_developers
                project_message, project_feishu_msg = build_project_daily_works_message(project_developers)
                projects_messages[project.id] = {'message': project_message, 'feishu_message': project_feishu_msg}

    # 构造每个用户的消息内容
    for user_id, user_projects in users_projects_data.items():
        user = User.objects.filter(pk=user_id, is_active=True).first()
        if not user:
            continue
        # 站内消息
        message = ''
        # 飞书的组
        fields_groups = []
        for project_id in user_projects:
            if project_id in projects_messages:
                project_messages = projects_messages[project_id]
                project_message = project_messages['message']
                project_feishu_msg = project_messages['feishu_message']
                if project_message:
                    message += '{}\n'.format(project_message)
                if project_feishu_msg:
                    fields_groups.append(project_feishu_msg)

        first_project_id = str(user_projects[0] if user_projects else '')
        notification_link = settings.SITE_URL + '/developers/daily_works' + '?projectId=' + first_project_id
        feishu_link = settings.SITE_URL + '/mp/developers/daily_works/?projectId=' + first_project_id

        if message or fields_groups:
            user_message_dict[user_id] = {"username": user.username}
            if message:
                user_message_dict[user_id]["notification"] = {
                    "message": message,
                    "link": notification_link
                }
            if fields_groups:
                user_message_dict[user_id]["feishu"] = {
                    "fields_groups": fields_groups,
                    "link": feishu_link
                }

    # 给每个人发送自己的项目工程师日报
    for user_id, msg in user_message_dict.items():
        user = User.objects.filter(pk=user_id, is_active=True).first()
        if not user:
            continue

        # 发送站内信
        notification_data = msg.get('notification', None)
        if notification_data:
            message = notification_data['message']
            url = notification_data['link']
            if to_send:
                create_notification(user, message, url=url, is_important=True, send_feishu=False)

        # 发送飞书
        feishu_data = msg.get('feishu', None)
        if feishu_data:
            # 飞书卡片消息
            fields_groups = feishu_data['fields_groups']
            feishu_link = feishu_data['link']
            feishu_card_message_data = {
                "title": "工程师日报",
                "fields_groups": fields_groups,
                "link": feishu_link
            }
            if to_send:
                send_feishu_card_message_to_user(user, feishu_card_message_data)
            message_data_list.append(feishu_card_message_data)

    # 给每个团队的leader发送自己的团队组员的项目工程师日报
    teams = Team.objects.all()
    for team in teams:
        leader = team.leader
        team_msg = build_team_feishu_daily_works_msg(user_message_dict, team)
        if not team_msg:
            continue
        if to_send:
            if leader and leader.profile.feishu_user_id:
                send_feishu_card_message_to_user(leader, team_msg)

        message_data_list.append(team_msg)
    return message_data_list


def build_team_feishu_daily_works_msg(user_message_dict, team):
    if team.leader and team.leader.is_active:
        # 飞书卡片消息
        fields_groups = []
        members = team.members
        for member in members:
            if member.is_active:
                if member.id in user_message_dict:
                    msg = user_message_dict[member.id]
                    feishu_data = msg.get('feishu', None)
                    if feishu_data:
                        # 飞书卡片消息
                        member_fields_groups = deepcopy(feishu_data['fields_groups'])
                        for fields_group in member_fields_groups:
                            fields_group[0] = member.username + "：" + fields_group[0]
                        fields_groups.extend(member_fields_groups)
        if fields_groups:
            team_msg = {
                "title": "团队【{}】成员工程师日报".format(team.name),
                "fields_groups": fields_groups,
            }
            return team_msg
    return None


# 发送工程师日报提醒给工程师
@shared_task
def send_project_developer_daily_works_to_developers(to_send=True):
    today = timezone.now().date()
    # 每个开发者需要被提醒写日报的项目
    developers_projects = {}
    for project in Project.ongoing_projects():
        # 所有工程师
        developers = project.get_active_developers()
        developers = set(developers)
        if developers:
            for developer in developers:
                developer_id = developer.id
                daily_work = DailyWork.objects.filter(project_id=project.id, developer_id=developer.id,
                                                      day=today).first()
                if daily_work and daily_work.status in ['postpone', 'normal']:
                    continue
                # 应该写日报没有写
                need_submit_daily_work = get_need_submit_daily_work(project, developer, today)
                if need_submit_daily_work:
                    if developer_id not in developers_projects:
                        developers_projects[developer_id] = {
                            'id': developer_id,
                            'name': developer.name,
                            'projects': []
                        }
                    developers_projects[developer_id]['projects'].append({'id': project.id, 'name': project.name})

    day_str = today.strftime(settings.DATE_FORMAT)
    for developer_data in developers_projects.values():
        '【xxx项目名称】、【xxx项目名称】还未提交日报，请及时提交哦'
        # 消息
        developer_id = developer_data['id']
        developer = Developer.objects.filter(pk=developer_id).first()
        developer_projects = developer_data['projects']
        first_project_id = developer_projects[0]['id']
        projects_str = ['【{}】'.format(project['name']) for project in developer_projects]
        message = '、'.join(projects_str) + '还未提交日报，请及时提交哦'
        developer_url = settings.DEVELOPER_WEB_SITE_URL + '?day={}&projectId={}&developerId={}&activeTab=dailyWork'.format(
            day_str, first_project_id, developer_id)
        if to_send:
            create_developer_notification(developer, message, url=developer_url)
        developers_projects[developer_id]['message'] = {'message': message, 'url': developer_url}
    return developers_projects


@shared_task
def build_document_version_clean_html(version_id):
    version = DocumentVersion.objects.get(pk=version_id)
    if not version.clean_html and version.html:
        version.clean_html = HTMLParser(version.html).build_html()
        version.save()


@shared_task
def rebuild_developer_quip_documents():
    docs = get_folders_docs(settings.QUIP_DEVELOPER_DOCUMENTS_FOLDER_ID)
    doc_list = sorted(docs, key=lambda doc: doc['updated_usec'], reverse=True)
    cache.set('quip_developer_documents', doc_list, 60 * 10)
    return doc_list


@shared_task
def get_developer_quip_documents():
    doc_list = cache.get('quip_developer_documents', None)
    if not doc_list:
        doc_list = rebuild_developer_quip_documents()
    return doc_list


@shared_task
def rebuild_ongoing_projects_dev_docs_checkpoints_status(is_rebuild=False):
    is_rebuild = is_rebuild or cache.get('rebuild_ongoing_projects_dev_docs_checkpoints_status', False)
    if not is_rebuild:
        Project.rebuild_ongoing_projects_dev_docs_checkpoints_status()
        cache.set('rebuild_ongoing_projects_dev_docs_checkpoints_status', True, 60 * 10)


def build_project_gitlab_user_id_day_gitlab_commits(project_id, gitlab_user_id, day, with_commits=False):
    day_str = day.strftime(settings.DATE_FORMAT)
    data = build_project_gitlab_user_id_period_gitlab_commits(project_id, gitlab_user_id, day_str, day_str,
                                                              with_commits=with_commits)

    if data and data['commits']:
        data['commits'] = sorted(data['commits'], key=lambda x: x['created_at'], reverse=True)
    return data


def build_project_gitlab_user_id_period_gitlab_commits(project_id, gitlab_user_id, start_day_str, end_day_str,
                                                       with_commits=False):
    # gitlab用户  项目的commit数据  用户在项目中最近提交日期
    gitlab_users = cache.get('gitlab-users', {})
    farm_projects_git_commits = cache.get('farm_projects_git_commits', {})
    gitlab_recent_committed_dates = cache.get('gitlab_recent_committed_dates', {})

    # Gitlab用户数据
    if gitlab_user_id in gitlab_users:
        gitlab_user_data = gitlab_users[gitlab_user_id]
    else:
        gitlab_user_data = get_gitlab_user_data(gitlab_user_id)
        if not gitlab_user_data:
            return
    gitlab_user_changed = False
    if 'committers' not in gitlab_user_data:
        gitlab_user_changed = True
        gitlab_user_data['committers'] = [{'committer_name': gitlab_user_data['name'],
                                           'committer_email': gitlab_user_data['email']},
                                          {'committer_name': gitlab_user_data['username'],
                                           'committer_email': gitlab_user_data['email']}]

    projects_commit_changed = False
    # 最近提交日期
    recent_committed_date_key = 'p_{}_u_{}'.format(project_id, gitlab_user_id)
    origin_committed_date = gitlab_recent_committed_dates.get(recent_committed_date_key, None)
    position_git = {"recent_committed_date": origin_committed_date,
                    "recent_committed_count": 0,
                    "additions": 0, "deletions": 0,
                    "commits": []
                    }
    # 计算
    if project_id in farm_projects_git_commits:
        project_git_commits = farm_projects_git_commits[project_id]
        # 项目的提交者
        project_git_commits['committers'] = project_git_commits.get('committers', [])
        project_committers = project_git_commits['committers']
        # 遍历commit记录
        days_commits = project_git_commits["every_data"]
        days = sorted(days_commits.keys(), reverse=True)
        recent_dates = [day_str for day_str in days if end_day_str >= day_str >= start_day_str]
        for day_str in recent_dates:
            day_commits = days_commits[day_str]
            day_projects_commits = day_commits.values()
            for day_project_commits in day_projects_commits:
                for commit in day_project_commits.values():
                    committer_name = commit['committer_name']
                    committer_email = commit['committer_email']
                    committer = {'committer_name': commit['committer_name'],
                                 'committer_email': commit['committer_email']}
                    title = commit['title']
                    if committer_name == gitlab_user_data['username'] or committer_email == \
                            gitlab_user_data['email']:
                        if committer not in gitlab_user_data['committers']:
                            gitlab_user_data['committers'].append(committer)
                            gitlab_user_changed = True
                    # 项目提交人添加
                    if committer not in project_committers:
                        project_committers.append(committer)
                        projects_commit_changed = True
                    # 项目提交人添加
                    if committer in gitlab_user_data['committers']:
                        position_git['recent_committed_count'] = position_git[
                                                                     'recent_committed_count'] + 1
                        # 统计日期
                        if not position_git['recent_committed_date']:
                            position_git['recent_committed_date'] = commit["committed_date"]
                        elif commit["committed_date"] > position_git['recent_committed_date']:
                            position_git['recent_committed_date'] = commit["committed_date"]
                        if with_commits:
                            position_git['commits'].append(deepcopy(commit))
                        # merge 不统计增加删除
                        if re.search(r'Merge ((.+? )?)branch (.+?) into (.+?)', title):
                            continue
                        position_git['additions'] = position_git['additions'] + commit["stats"][
                            "additions"]
                        position_git['deletions'] = position_git['deletions'] + commit["stats"][
                            "deletions"]
    # 构造最近提交时间
    if position_git['recent_committed_date']:
        recent_committed_date = build_gitlab_committed_date(position_git['recent_committed_date'])
        position_git['recent_committed_date'] = recent_committed_date
        if origin_committed_date != recent_committed_date:
            gitlab_recent_committed_dates[recent_committed_date_key] = recent_committed_date
            cache.set('gitlab_recent_committed_dates', gitlab_recent_committed_dates, None)
    if gitlab_user_changed:
        gitlab_users[gitlab_user_id] = gitlab_user_data
        cache.set('gitlab-users', gitlab_users, None)
    if projects_commit_changed:
        cache.set('farm_projects_git_commits', farm_projects_git_commits, None)
    return position_git


def build_gitlab_committed_date(date_str):
    result_str = date_str
    if date_str:
        try:
            if '+08:00' in date_str:
                result_str = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%f+08:00").strftime(
                    settings.DATETIME_FORMAT)
            elif date_str.endswith('Z'):
                result_str = (datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ") + timedelta(
                    hours=8)).strftime(settings.DATETIME_FORMAT)
        except:
            pass

    return result_str
