# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from celery import shared_task

from datetime import datetime, timedelta

from django.conf import settings
from django.core.cache import cache
from django.shortcuts import timezone

from developers.tasks import build_project_gitlab_user_id_period_gitlab_commits
from projects.models import Project
from developers.models import DailyWork


@shared_task
def rebuild_ongoing_projects_developers_recent_seven_days_gitlab_commits_cache_data():
    '''
    觉察当下 当下执著本源本真
    体验刹那 刹那专注清净自在
    安心睡觉 专注吃饭 认真做事 真心待人
    爱生命 就得运动 敲代码 也要瞧瞧身体
    :return:更新进行中项目开发者近7天的gitlab commit数据
    '''
    seven_days_ago_str = (datetime.now() - timedelta(days=7)).strftime(settings.DATE_FORMAT)
    today_str = datetime.now().strftime(settings.DATE_FORMAT)
    for project in Project.ongoing_projects():
        project_id = project.id
        for job in project.job_positions.all():
            p_g_keys = set()
            developer = job.developer
            gitlab_user_id = developer.gitlab_user_id
            if gitlab_user_id:
                p_g_key = "p_{}_u_{}".format(project_id, gitlab_user_id)
                if p_g_key not in p_g_keys:
                    project_user_commits_cache_key = 'p_{}_u_{}_gitlab_commits'.format(project_id, gitlab_user_id)
                    position_gitlab_commits = build_project_gitlab_user_id_period_gitlab_commits(project_id,
                                                                                                 gitlab_user_id,
                                                                                                 seven_days_ago_str,
                                                                                                 today_str)
                    cache.set(project_user_commits_cache_key, position_gitlab_commits, 60 * 60)
                    p_g_keys.add(p_g_key)


@shared_task
def rebuild_ongoing_projects_developers_today_daily_works_cache_data():
    '''
    更新进行中项目开发者今日打卡数据
    :param projects_data:
    :return:
    '''
    today = timezone.now().date()
    today_str = today.strftime(settings.DATE_FORMAT)

    for project in Project.ongoing_projects():
        project_id = project.id
        for job in project.job_positions.all():
            developer_id = job.developer_id
            cache_key_template = 'project_{}_{}_'.format(project_id, developer_id) + '{day_str}_daily_work'
            today_cache_key = cache_key_template.format(day_str=today_str)
            developer_daily_work = DailyWork.objects.filter(project_id=project_id,
                                                            developer_id=developer_id).exclude(status='pending')
            today_item = developer_daily_work.filter(day=today).first()
            today_data = {'status_display': today_item.status_display,
                          'status': today_item.status} if today_item else None
            cache.set(today_cache_key, today_data, 60 * 60)
