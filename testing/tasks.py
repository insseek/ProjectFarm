# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import json
from copy import deepcopy

from celery import shared_task
from datetime import datetime, timedelta, date

from django.utils import timezone
from django.conf import settings

from gearfarm.utils.common_utils import this_month_start, this_month_end, get_1st_of_next_month, \
    get_first_day_of_last_month
from projects.models import Project
from notifications.utils import create_notification, create_top_user_notification
from testing.models import ProjectTag, Bug, ProjectTestCase, TestPlanCase, TestDayStatistic, TestMonthStatistic, \
    TestDayBugStatistic


# 当项目有未关闭bug的时候推送给项目经理，测试人员
@shared_task
def send_project_undone_bugs_notification_to_manager_and_test():
    today = timezone.now().date()
    day = today
    for project in Project.ongoing_projects():
        undone_bugs = project.bugs.filter(status__in=['pending', 'fixed'])
        if not undone_bugs.exists():
            continue
        pending_bugs = undone_bugs.filter(status='pending')
        fixed_bugs = undone_bugs.filter(status='fixed')
        day_zero = datetime(day.year, day.month, day.day, 0, 0, 0)
        day_end = datetime(day.year, day.month, day.day, 23, 59, 59)

        day_created_bugs = project.bugs.filter(created_at__gte=day_zero, created_at__lte=day_end)

        day_fixed_bugs = project.bugs.filter(fixed_at__gte=day_zero, fixed_at__lte=day_end)
        day_closed_bugs = project.bugs.filter(closed_at__gte=day_zero, closed_at__lte=day_end)

        content_temp = '【{project}】共{pending_count}个bug待修复，{fixed_count}个bug待确认修复。今日bug新增{day_created_count}个  ，修复{day_fixed_count}个，关闭{day_closed_count}个。'
        content = content_temp.format(project=project.name,
                                      pending_count=pending_bugs.count(),
                                      fixed_count=fixed_bugs.count(),
                                      day_created_count=day_created_bugs.count(),
                                      day_fixed_count=day_fixed_bugs.count(),
                                      day_closed_count=day_closed_bugs.count(),
                                      )
        url = settings.GEAR_TEST_SITE_URL + '/projects/{}/bugs/'.format(project.id)

        notification_users = set()
        if project.manager and project.manager.is_active:
            notification_users.add(project.manager)
        # 【test】
        project_tests = project.tests.all()
        for project_test in project_tests:
            if project_test.is_active:
                notification_users.add(project_test)

        for u in notification_users:
            create_notification(u, content, url=url, app_id='gear_test')


# 当项目有未关闭bug的时候推送给负责人
@shared_task
def send_project_undone_bugs_notification_to_assignee():
    for project in Project.ongoing_projects():
        undone_bugs = project.bugs.filter(status__in=['pending', 'fixed'])
        if not undone_bugs.exists():
            continue
        user_bug_dict = {}
        for bug in undone_bugs:
            assignee = bug.assignee
            if assignee and assignee.is_active:
                if assignee.id not in user_bug_dict:
                    user_bug_dict[assignee.id] = {
                        'assignee': assignee,
                        'pending_count': 0,
                        'fixed_count': 0
                    }
                if bug.status == 'pending':
                    user_bug_dict[assignee.id]['pending_count'] = user_bug_dict[assignee.id]['pending_count'] + 1
                else:
                    user_bug_dict[assignee.id]['fixed_count'] = user_bug_dict[assignee.id]['fixed_count'] + 1
        '''若有待修复bug，点击跳转到待修复页面，指派给选择该用户；
        若有已修复待确认bug，跳转到该页面，指派给选择该用户。 若两者都有，跳转到待修复页面。'''
        pending_url = settings.GEAR_TEST_SITE_URL + '/projects/{}/bugs/?bug_filter=pending'.format(project.id)
        fixed_url = settings.GEAR_TEST_SITE_URL + '/projects/{}/bugs/?bug_filter=fixed'.format(project.id)

        content_temp = '【{project}】中你有{pending_count}个bug待修复，{fixed_count}个bug待确认修复。'
        for item in user_bug_dict.values():
            assignee = item['assignee']
            pending_count = item['pending_count']
            fixed_count = item['fixed_count']
            url = pending_url if pending_count else fixed_url
            content = content_temp.format(project=project.name,
                                          pending_count=pending_count,
                                          fixed_count=fixed_count,
                                          )
            create_top_user_notification(assignee, content, url=url, is_important=True, app_id='gear_test')


@shared_task
def clear_invalid_project_tags():
    tags = ProjectTag.objects.all()
    for tag in tags:
        if not tag.is_default:
            if any([tag.test_cases.exists(), tag.plan_cases.exists(), tag.bugs.exists()]):
                continue
            tag.delete()


def build_project_today_pending_bugs_statistics(project):
    bugs = project.bugs.all()
    build_today_pending_bugs_statistics(bugs)


@shared_task
def build_today_pending_bugs_statistics(queryset=None):
    pending_bugs = Bug.pending_bugs(queryset=queryset)
    today = timezone.now().date()
    bugs_statistics = {}
    # bugs_statistics = {
    #     "project_id": {
    #         "P0": 22,
    #         "P1": 13,
    #         "P2": 14,
    #         'P3': 23,
    #         "total": 72,
    #     }
    # }
    # 统计不同级别下每天bug待修复数量
    project_template = {"total": 0}
    for k, v in Bug.PRIORITY_CHOICES:
        project_template[k] = 0

    for bug in pending_bugs:
        project_id = bug.project.id
        priority = bug.priority
        if project_id not in bugs_statistics:
            bugs_statistics[project_id] = deepcopy(project_template)
        bugs_statistics[project_id][priority] += 1
        bugs_statistics[project_id]['total'] += 1

    # bug按优先级统计
    for project_id, bug_data in bugs_statistics.items():
        statistic, created = TestDayBugStatistic.objects.get_or_create(date=today,
                                                                       project_id=project_id)
        statistic.bugs_detail = json.dumps(bug_data)
        statistic.save()


# statistic_type='month' 以月为单位统计
def build_test_statistics(start_date, end_date, statistic_type='day'):
    today = timezone.now().date()
    if not end_date:
        end_date = today
    elif end_date > today:
        end_date = today
    if not start_date:
        start_date_choices = []
        first_bug = Bug.objects.order_by('created_at').first()
        first_case = ProjectTestCase.objects.order_by('created_at').first()
        if first_case:
            start_date_choices.append(first_case.created_at.date())
        if first_bug:
            start_date_choices.append(first_bug.created_at.date())
        if start_date_choices:
            start_date = min(start_date_choices)
    if not all([start_date, end_date]):
        return
    if start_date > end_date:
        return
    # TestDayStatistic
    # {
    #     "date": "2019-10-01",
    #     "opened_bugs": 10,
    #     "closed_bugs": 15,
    #     "created_cases": 0,
    #     'executed_cases': 0,
    #     "projects_detail":
    #         [
    #             {"id": 1, "name": "我是项目一", "opened_bugs": 9, "closed_bugs": 10, "created_cases": 0,
    #              'executed_cases': 0},
    #             {"id": 1, "name": "我是项目二", "opened_bugs": 1, "closed_bugs": 5, "created_cases": 0, 'executed_cases': 0}
    #         ]
    # }
    bugs = Bug.objects.all()
    test_cases = ProjectTestCase.objects.filter(is_active=True)
    test_plan_cases = TestPlanCase.objects.all()
    current_date = start_date
    while current_date <= end_date:
        if statistic_type == 'month':
            month_start = this_month_start(current_date)
            today_month_start = this_month_start()
            if month_start != today_month_start:
                if TestMonthStatistic.objects.filter(month_first_day=month_start).exists():
                    current_date = get_1st_of_next_month(current_date)
                    continue
        else:
            # 如果已存在 就不统计了
            if current_date != today:
                if TestDayStatistic.objects.filter(date=current_date).exists():
                    current_date = current_date + timedelta(days=1)
                    continue
        # 时间
        start_day_zero = datetime(current_date.year, current_date.month, current_date.day, 0, 0, 0)
        end_day_end = datetime(current_date.year, current_date.month, current_date.day, 23, 59, 59)
        if statistic_type == 'month':
            start_day_zero = this_month_start(current_date)
            end_day_end = this_month_end(current_date)

        # 创建的bug
        created_bugs = bugs.filter(created_at__gte=start_day_zero, created_at__lte=end_day_end)
        reopened_bugs = bugs.filter(reopened_at__gte=start_day_zero, reopened_at__lte=end_day_end)
        closed_bugs = bugs.filter(closed_at__gte=start_day_zero, closed_at__lte=end_day_end)
        created_cases = test_cases.filter(created_at__gte=start_day_zero, created_at__lte=end_day_end)
        executed_cases = test_plan_cases.filter(executed_at__gte=start_day_zero,
                                                executed_at__lte=end_day_end)
        test_day_statistics_dict = {}
        # bug_test_case_day_statistic = {
        #     "top_user_id": {
        #         "opened_bugs": 22,
        #         "closed_bugs": 13,
        #         "created_cases": 14,
        #         'executed_cases': 23,
        #         'projects_detail': {378: {"id": 378, "name": "tsingke", "opened_bugs": 12, "closed_bugs": 5,
        #                              "created_cases": 6, 'executed_cases': 13},
        #                             432: {"id": 432, "name": "SKF4U-SFE", "opened_bugs": 1,"closed_bugs": 17,
        #                              "created_cases": 7, 'executed_cases': 10}}
        #     }
        # }
        # 新增bug统计
        test_day_statistic_template = {
            "opened_bugs": 0,
            "closed_bugs": 0,
            "created_cases": 0,
            'executed_cases': 0,
            'projects_detail': {}
        }
        for bug in created_bugs:
            if not bug.creator:
                continue
            top_user_id = bug.creator.id
            project = bug.project
            project_id = bug.project.id
            if top_user_id not in test_day_statistics_dict:
                test_day_statistics_dict[top_user_id] = deepcopy(test_day_statistic_template)
            current_statistic_data = test_day_statistics_dict[top_user_id]
            projects_detail = current_statistic_data["projects_detail"]
            if project_id not in projects_detail:
                projects_detail[project_id] = {"id": project.id,
                                               "name": project.name,
                                               "opened_bugs": 0,
                                               "closed_bugs": 0,
                                               "created_cases": 0,
                                               'executed_cases': 0,
                                               }
            project_detail = projects_detail[project_id]
            project_detail["opened_bugs"] = project_detail["opened_bugs"] + 1
            current_statistic_data["opened_bugs"] = current_statistic_data["opened_bugs"] + 1

        # 激活的bug也是新增
        for bug in reopened_bugs:
            if not bug.reopened_by:
                continue
            top_user_id = bug.reopened_by.id
            project = bug.project
            project_id = bug.project.id
            if top_user_id not in test_day_statistics_dict:
                test_day_statistics_dict[top_user_id] = deepcopy(test_day_statistic_template)
            current_statistic_data = test_day_statistics_dict[top_user_id]
            projects_detail = current_statistic_data["projects_detail"]
            if project_id not in projects_detail:
                projects_detail[project_id] = {"id": project.id,
                                               "name": project.name,
                                               "opened_bugs": 0,
                                               "closed_bugs": 0,
                                               "created_cases": 0,
                                               'executed_cases': 0,
                                               }
            project_detail = projects_detail[project_id]
            project_detail["opened_bugs"] = project_detail["opened_bugs"] + 1
            current_statistic_data["opened_bugs"] = current_statistic_data["opened_bugs"] + 1

        # 关闭bug统计
        for bug in closed_bugs:
            if not bug.closed_by:
                continue
            top_user_id = bug.closed_by.id
            project = bug.project
            project_id = bug.project.id
            if top_user_id not in test_day_statistics_dict:
                test_day_statistics_dict[top_user_id] = deepcopy(test_day_statistic_template)
            current_statistic_data = test_day_statistics_dict[top_user_id]
            projects_detail = current_statistic_data["projects_detail"]
            if project_id not in projects_detail:
                projects_detail[project_id] = {
                    "id": project.id,
                    "name": project.name,
                    "opened_bugs": 0,
                    "closed_bugs": 0,
                    "created_cases": 0,
                    'executed_cases': 0,
                }
            project_detail = projects_detail[project_id]
            project_detail["closed_bugs"] = project_detail["closed_bugs"] + 1
            current_statistic_data["closed_bugs"] = current_statistic_data["closed_bugs"] + 1

        # 新增用例统计
        for case in created_cases:
            if not case.creator:
                continue
            top_user_id = case.creator.id
            project = case.project
            project_id = case.project.id
            if top_user_id not in test_day_statistics_dict:
                test_day_statistics_dict[top_user_id] = deepcopy(test_day_statistic_template)
            current_statistic_data = test_day_statistics_dict[top_user_id]
            projects_detail = current_statistic_data["projects_detail"]
            if project_id not in projects_detail:
                projects_detail[project_id] = {
                    "id": project.id,
                    "name": project.name,
                    "opened_bugs": 0,
                    "closed_bugs": 0,
                    "created_cases": 0,
                    'executed_cases': 0,
                }
            project_detail = projects_detail[project_id]
            project_detail["created_cases"] = project_detail["created_cases"] + 1
            current_statistic_data["created_cases"] = current_statistic_data["created_cases"] + 1

        # 执行计划用例次数统计
        for case in executed_cases:
            if not case.executor:
                continue
            top_user_id = case.executor.id
            project = case.project
            project_id = case.project.id
            if top_user_id not in test_day_statistics_dict:
                test_day_statistics_dict[top_user_id] = deepcopy(test_day_statistic_template)
            current_statistic_data = test_day_statistics_dict[top_user_id]
            projects_detail = current_statistic_data["projects_detail"]
            if project_id not in projects_detail:
                projects_detail[project_id] = {
                    "id": project.id,
                    "name": project.name,
                    "opened_bugs": 0,
                    "closed_bugs": 0,
                    "created_cases": 0,
                    'executed_cases': 0,
                }
            project_detail = projects_detail[project_id]
            project_detail["executed_cases"] = project_detail["executed_cases"] + 1
            current_statistic_data["executed_cases"] = current_statistic_data["executed_cases"] + 1

        # 创建每月的统计数据
        if statistic_type == 'month':
            month_str = datetime.strftime(current_date, '%Y-%m')
            month_start = this_month_start(current_date)
            for top_user_id, test_day_statistic_data in test_day_statistics_dict.items():
                statistic, created = TestMonthStatistic.objects.get_or_create(month=month_str,
                                                                              month_first_day=month_start,
                                                                              operator_id=top_user_id)
                statistic.opened_bugs = test_day_statistic_data['opened_bugs']
                statistic.closed_bugs = test_day_statistic_data['closed_bugs']
                statistic.created_cases = test_day_statistic_data['created_cases']
                statistic.executed_cases = test_day_statistic_data['executed_cases']
                statistic.projects_detail = json.dumps(
                    sorted(test_day_statistic_data['projects_detail'].values(),
                           key=lambda x: x['id'], reverse=False), ensure_ascii=False)
                statistic.save()
        # 创建今日统计数据
        else:
            for top_user_id, test_day_statistic_data in test_day_statistics_dict.items():
                statistic, created = TestDayStatistic.objects.get_or_create(date=current_date,
                                                                            operator_id=top_user_id)
                statistic.opened_bugs = test_day_statistic_data['opened_bugs']
                statistic.closed_bugs = test_day_statistic_data['closed_bugs']
                statistic.created_cases = test_day_statistic_data['created_cases']
                statistic.executed_cases = test_day_statistic_data['executed_cases']
                statistic.projects_detail = json.dumps(
                    sorted(test_day_statistic_data['projects_detail'].values(),
                           key=lambda x: x['id'], reverse=False), ensure_ascii=False)
                statistic.save()

        if statistic_type == 'month':
            current_date = get_1st_of_next_month(current_date)
        else:
            current_date = current_date + timedelta(days=1)


@shared_task
def build_yesterday_test_statistics():
    yesterday = date.today() - timedelta(days=1)
    build_test_statistics(start_date=yesterday, end_date=yesterday, statistic_type='day')


@shared_task
def build_today_test_statistics():
    day = date.today()
    build_test_statistics(start_date=day, end_date=day, statistic_type='day')


@shared_task
def rebuild_all_test_statistics():
    end_date = timezone.now().date()
    start_date = None
    start_date_choices = []
    first_bug = Bug.objects.order_by('created_at').first()
    first_case = ProjectTestCase.objects.order_by('created_at').first()
    if first_case:
        start_date_choices.append(first_case.created_at.date())
    if first_bug:
        start_date_choices.append(first_bug.created_at.date())
    if start_date_choices:
        start_date = min(start_date_choices)
    if start_date:
        build_test_statistics(start_date, end_date, statistic_type='day')
        build_test_statistics(start_date, end_date, statistic_type='month')


@shared_task
def build_last_month_test_statistics():
    start_date = get_first_day_of_last_month()
    end_date = this_month_end(start_date)
    build_test_statistics(start_date, end_date, statistic_type='month')
