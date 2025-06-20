from copy import deepcopy
from datetime import timedelta, datetime
from itertools import chain

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.cache import cache
from django.utils.cache import get_cache_key
from rest_framework.decorators import api_view

from farmbase.user_utils import get_user_projects
from developers.models import DailyWork
from dashboard.serializers import ProjectDashBoardSerializer
from developers.tasks import rebuild_ongoing_projects_dev_docs_checkpoints_status
from gearfarm.utils.farm_response import api_success, build_pagination_response, build_pagination_queryset_data
from farmbase.templatetags.mytags import my_active_projects
from projects.serializers import GanttTaskTopicSerializer, TechnologyCheckpointSerializer
from projects.models import Project, TechnologyCheckpoint
from projects.build_projects_extra_data import projects_data_add_positions_gitlab_commits_data, \
    build_projects_user_unread_comment_count, build_projects_user_daily_works_bugs_count, \
    projects_data_add_positions_daily_works_data, get_user_need_read_daily_works
from proposals.models import Proposal
from tasks.models import Task
from tasks.serializers import TaskSerializer
from testing.models import Bug
from playbook.models import CheckItem
from playbook.serializers import CheckItemSerializer
from farmbase.users_undone_works_utils import get_user_today_undone_tasks, get_user_today_undone_gantt_tasks, \
    get_user_today_work_orders_tasks, get_user_today_undone_playbook_tasks, get_user_today_tpm_checkpoints_tasks

PROPOSAL_STATUS_DICT = Proposal.PROPOSAL_STATUS_DICT


def get_user_groups_set(user):
    user_groups = list(user.groups.values_list('name', flat=True))
    user_groups_set = set(user_groups)
    if user.is_superuser:
        user_groups_set.add('超级管理员')
    return user_groups_set


@api_view(["GET"])
def modules(request):
    user = request.user

    data = ['statistics', 'tasks']
    modules_dict = (
        ("gantt_tasks", ["项目经理", "产品经理", '培训产品经理', "TPM", "远程TPM", "设计", "测试"]),
        ("playbook_tasks", ["项目经理", "产品经理", '培训产品经理']),
        ("tpm_checkpoints", ["TPM", "远程TPM"]),
        ("work_orders", []),
        ("leads", ["BD", "市场"]),
        ("proposals", ["BD", "市场", "产品经理", "培训产品经理"]),
        ("projects", ["项目经理", "产品经理", '培训产品经理', "TPM", "远程TPM", "设计", "测试", "超级管理员"])
    )

    user_groups_set = get_user_groups_set(user)
    for key, value in modules_dict:
        if not value:
            data.append(key)
        elif user_groups_set & set(value):
            data.append(key)
    return api_success(data)


@api_view(["GET"])
def my_undone_work_dashboard_statistics(request):
    user = request.user
    top_user_id = request.top_user.id
    # 待办事项
    tasks = get_user_today_undone_tasks(request.user, today=None, with_manage_project_tasks=True)
    # 甘特图任务
    gantt_tasks = get_user_today_undone_gantt_tasks(request.user, today=None, with_manage_project_tasks=True)
    # 未完成的Playbook任务
    playbook_tasks = get_user_today_undone_playbook_tasks(user, only_expected_date=False)
    # 工单
    work_orders = get_user_today_work_orders_tasks(user)
    # TPM检查点
    tpm_checkpoints = get_user_today_tpm_checkpoints_tasks(user)
    # 负责人是自己 待修改 已修复的bug
    bugs = Bug.objects.filter(assignee_id=top_user_id, status__in=['pending', 'fixed'])
    # 需要查看的日报
    daily_works = get_user_need_read_daily_works(user)

    full_result_data = {
        "tasks": len(tasks),
        "gantt_tasks": len(gantt_tasks),
        "playbook_tasks": len(playbook_tasks),
        'work_orders': len(work_orders),
        "tpm_checkpoints": len(tpm_checkpoints),
        "daily_works": len(daily_works),
        "bugs": len(bugs),
    }

    statistics_dict = {
        "tasks": [],
        "gantt_tasks": ["项目经理", "产品经理", '培训产品经理', "TPM", "远程TPM", "设计", "测试"],
        "playbook_tasks": ["项目经理", "产品经理", '培训产品经理'],
        "work_orders": [],
        "tpm_checkpoints": ["TPM", "远程TPM"],
        "daily_works": ["项目经理", "产品经理", '培训产品经理', "TPM", "远程TPM"],
        "bugs": ["项目经理", "产品经理", '培训产品经理', "TPM", "远程TPM", "设计", "测试"]
    }
    result_data = dict()
    user_groups_set = get_user_groups_set(user)
    for key, value in full_result_data.items():
        group_set = statistics_dict[key]
        if not group_set:
            result_data[key] = value
        elif user_groups_set & set(group_set):
            result_data[key] = value
    return api_success(result_data)


@api_view(["GET"])
def undone_tasks(request):
    today = timezone.now().date()
    next_two_day = today + timedelta(days=2)

    tasks = get_user_today_undone_tasks(request.user, today=next_two_day, with_manage_project_tasks=True)

    # 项目、需求、线索、其他  个人任务
    project_tasks_dict = {}
    proposal_tasks_dict = {}
    lead_tasks_dict = {}
    content_tasks_dict = {}
    personal_dict = {
        "model_name": '',
        "name": "个人任务"
    }
    content_object_model_dict = {
        'project': '项目',
        'proposal': '需求',
        'lead': '线索',
    }

    for t in tasks:
        if t.content_object:
            content_type = t.content_type.model
            if content_type == 'project':
                tasks_dict = project_tasks_dict
            elif content_type == 'proposal':
                tasks_dict = proposal_tasks_dict
            elif content_type == 'lead':
                tasks_dict = lead_tasks_dict
            else:
                tasks_dict = content_tasks_dict

            if t.object_id not in tasks_dict:
                model_name = content_object_model_dict.get(content_type, None) or t.content_object._meta.verbose_name
                tasks_dict[t.object_id] = {
                    "content_type": {
                        "app_label": t.content_type.app_label,
                        "model": t.content_type.model,
                        "model_verbose_name": model_name
                    },
                    "model_name": model_name,
                    "object_name": str(t.content_object),
                    "object_id": t.content_object.id,
                    "id": t.content_object.id,
                    "name": str(t.content_object),
                    "created_at": t.content_object.created_at.strftime(settings.DATETIME_FORMAT)
                }
            obj_data = tasks_dict[t.object_id]
        else:
            obj_data = personal_dict

        if t.expected_at <= today:
            if 'today' not in obj_data:
                obj_data['today'] = []
            obj_data['today'].append(t)
        else:
            if 'next_two_days' not in obj_data:
                obj_data['next_two_days'] = []
            obj_data['next_two_days'].append(t)

    result_statistics = {
        "today_count": 0,
        "next_two_days_count": 0,
        "result_data": []
    }
    result_data = result_statistics['result_data']

    project_list = sorted(project_tasks_dict.values(), key=lambda x: x['created_at'], reverse=False)
    proposal_list = sorted(proposal_tasks_dict.values(), key=lambda x: x['created_at'], reverse=False)
    lead_list = sorted(lead_tasks_dict.values(), key=lambda x: x['created_at'], reverse=False)
    content_list = sorted(content_tasks_dict.values(), key=lambda x: x['created_at'], reverse=False)
    personal_list = [personal_dict] if 'next_two_days' in personal_dict or 'today' in personal_dict else []

    for obj in chain(project_list, proposal_list, lead_list, content_list, personal_list):
        if 'today' in obj or 'next_two_days' in obj:
            if 'today' in obj:
                tasks = sorted(obj['today'], key=lambda x: x.expected_at)
                tasks_data = TaskSerializer(tasks, many=True).data
                obj['today'] = tasks_data
                obj['today_count'] = len(tasks)
                result_statistics['today_count'] = result_statistics['today_count'] + len(tasks)
            if 'next_two_days' in obj:
                tasks = sorted(obj['next_two_days'], key=lambda x: x.expected_at)
                tasks_data = TaskSerializer(tasks, many=True).data
                obj['next_two_days'] = tasks_data
                obj['next_two_days_count'] = len(tasks)
                result_statistics['next_two_days_count'] = result_statistics['next_two_days_count'] + len(tasks)
            result_data.append(obj)

    return api_success(data=result_statistics)


@api_view(['GET'])
def undone_gantt_chart_tasks(request):
    user = request.user
    today = timezone.now().date()
    projects = Project.ongoing_projects().order_by('created_at')
    next_two_day = today + timedelta(days=2)

    result_statistics = {
        "today_count": 0,
        "next_two_days_count": 0,
        "result_data": []
    }
    result_data = result_statistics['result_data']
    for project in projects:
        gantt_chart = getattr(project, 'gantt_chart', None)
        if not gantt_chart:
            continue
        # 项目经理  自己的项目中的所有人的甘特图任务  ；其他人 只展示自己的
        task_topics = gantt_chart.task_topics.filter(is_done=False, expected_finish_time__lte=next_two_day)
        if not project.manager_id == user.id:
            task_topics = task_topics.filter(role__user_id=user.id, is_dev_done=False)
        if not task_topics.exists():
            continue

        obj_data = {
            "id": project.id,
            "model_name": '项目',
            "name": project.name,
            "created_at": project.created_at.strftime(settings.DATETIME_FORMAT)
        }
        for t in task_topics:
            if t.expected_finish_time <= today:
                if 'today' not in obj_data:
                    obj_data['today'] = []
                obj_data['today'].append(t)
            else:
                if 'next_two_days' not in obj_data:
                    obj_data['next_two_days'] = []
                obj_data['next_two_days'].append(t)
        if 'today' in obj_data or 'next_two_days' in obj_data:
            if 'today' in obj_data:
                tasks = sorted(obj_data['today'], key=lambda x: x.expected_finish_time)
                obj_data['today'] = GanttTaskTopicSerializer(tasks, many=True).data
                obj_data['today_count'] = len(tasks)
                result_statistics['today_count'] = result_statistics['today_count'] + len(tasks)
            if 'next_two_days' in obj_data:
                tasks = sorted(obj_data['next_two_days'], key=lambda x: x.expected_finish_time)
                obj_data['next_two_days'] = GanttTaskTopicSerializer(tasks, many=True).data
                obj_data['next_two_days_count'] = len(tasks)
                result_statistics['next_two_days_count'] = result_statistics['next_two_days_count'] + len(tasks)
            result_data.append(obj_data)
    return api_success(data=result_statistics)


@api_view(['GET'])
def undone_playbook_tasks(request):
    user = request.user
    today = timezone.now().date()
    next_two_day = today + timedelta(days=2)
    next_three_day = today + timedelta(days=3)
    projects = Project.ongoing_projects().order_by('created_at')
    '''
    1、未完成（按照优先级排序）（PMO>PM）
    （1）之前阶段的未完成任务
    （2）本阶段截止日期在今日及今日前的未完成任务
    （3）该阶段结束当天，显示当前阶段的所有未完成任务
    （4）先按照项目创建时间正序排序，项目中按照截止时间正序排列
    2、未来两天（按照优先级排序）（PMO>PM）
    （1）截止日期在未来两天的任务
    （2）与“到了截止日期的任务”处在相同阶段组的，无截止日期的任务
    '''
    result_statistics = {
        "today_count": 0,
        "next_two_days_count": 0,
        "result_data": []
    }
    result_data = result_statistics['result_data']

    for project in projects:
        member_types = []
        if project.manager_id == user.id:
            member_types.append('manager')
        if project.product_manager_id == user.id:
            member_types.append('product_manager')
        if not member_types:
            continue
        obj_data = {
            "id": project.id,
            "model_name": '项目',
            "name": project.name,
            "created_at": project.created_at.strftime(settings.DATETIME_FORMAT)
        }
        for num, stage in enumerate(project.playbook_stages.filter(member_type__in=member_types).order_by('index')):
            # 上一个阶段的任务全部统计到今天任务
            if stage.is_previous_stage:
                for check_group in stage.check_groups.order_by('index'):
                    for check_item in check_group.check_items.filter(completed_at__isnull=True):
                        if 'today' not in obj_data:
                            obj_data['today'] = set()
                        obj_data['today'].add(check_item)
            # 当前阶段 如果是最后一天全部统计到今天任务；如果不是最后一天，根据期望日期统计
            elif stage.is_current_stage:
                is_stage_end_date = stage.stage_end_date == today
                for check_group in stage.check_groups.order_by('index'):
                    for check_item in check_group.check_items.filter(completed_at__isnull=True):
                        if is_stage_end_date:
                            if 'today' not in obj_data:
                                obj_data['today'] = set()
                            obj_data['today'].add(check_item)
                        elif check_item.expected_date:
                            if check_item.expected_date <= today:
                                if 'today' not in obj_data:
                                    obj_data['today'] = set()
                                obj_data['today'].add(check_item)
                            elif check_item.expected_date <= next_two_day:
                                if 'next_two_days' not in obj_data:
                                    obj_data['next_two_days'] = set()
                                obj_data['next_two_days'].add(check_item)
                                siblings = check_item.check_group.check_items.filter(
                                    completed_at__isnull=True, expected_date__isnull=True)
                                obj_data['next_two_days'] = obj_data['next_two_days'] | set(siblings)
            # 下一个阶段    根据期望日期统计
            elif stage.is_next_stage:
                for check_group in stage.check_groups.order_by('index'):
                    for check_item in check_group.check_items.filter(completed_at__isnull=True):
                        if check_item.expected_date:
                            if check_item.expected_date <= today:
                                if 'today' not in obj_data:
                                    obj_data['today'] = set()
                                obj_data['today'].add(check_item)
                            elif check_item.expected_date <= next_two_day:
                                if 'next_two_days' not in obj_data:
                                    obj_data['next_two_days'] = set()
                                obj_data['next_two_days'].add(check_item)
        if 'today' in obj_data or 'next_two_days' in obj_data:
            if 'today' in obj_data:
                tasks = sorted(obj_data['today'],
                               key=lambda x: (x.expected_date if x.expected_date else next_three_day))
                obj_data['today'] = CheckItemSerializer(tasks, many=True).data
                obj_data['today_count'] = len(tasks)
                result_statistics['today_count'] = result_statistics['today_count'] + len(tasks)
            if 'next_two_days' in obj_data:
                tasks = sorted(obj_data['next_two_days'],
                               key=lambda x: (x.expected_date if x.expected_date else next_three_day))
                obj_data['next_two_days'] = CheckItemSerializer(tasks, many=True).data
                obj_data['next_two_days_count'] = len(tasks)
                result_statistics['next_two_days_count'] = result_statistics['next_two_days_count'] + len(tasks)
            result_data.append(obj_data)
    return api_success(data=result_statistics)


@api_view(['GET'])
def undone_tpm_checkpoints(request):
    rebuild_ongoing_projects_dev_docs_checkpoints_status()
    today = timezone.now().date()
    next_two_day = today + timedelta(days=2)
    next_three_day = today + timedelta(days=3)
    # this_week = request.GET.get('this_week', None) in ['1', 'True', 'true', True, 1]
    tpm = request.user

    checkpoints = TechnologyCheckpoint.objects.none()
    for p in Project.ongoing_projects().filter(tpm_id=tpm.id):
        checkpoints = checkpoints | p.technology_checkpoints.filter(status='pending', expected_at__lte=next_two_day)

    project_tasks_dict = {}

    for t in checkpoints:
        tasks_dict = project_tasks_dict
        if t.project_id not in tasks_dict:
            tasks_dict[t.project_id] = {
                "id": t.project_id,
                "model_name": "项目",
                "name": t.project.name,
                "created_at": t.project.created_at.strftime(settings.DATETIME_FORMAT)
            }
        obj_data = tasks_dict[t.project_id]

        if t.expected_at <= today:
            if 'today' not in obj_data:
                obj_data['today'] = []
            obj_data['today'].append(t)
        else:
            if 'next_two_days' not in obj_data:
                obj_data['next_two_days'] = []
            obj_data['next_two_days'].append(t)

    result_statistics = {
        "today_count": 0,
        "next_two_days_count": 0,
        "result_data": []
    }
    result_data = result_statistics['result_data']

    project_list = sorted(project_tasks_dict.values(), key=lambda x: x['created_at'], reverse=False)

    for obj in project_list:
        if 'today' in obj or 'next_two_days' in obj:
            if 'today' in obj:
                tasks = sorted(obj['today'], key=lambda x: x.expected_at)
                tasks_data = TechnologyCheckpointSerializer(tasks, many=True).data
                obj['today'] = tasks_data
                obj['today_count'] = len(tasks)
                result_statistics['today_count'] = result_statistics['today_count'] + len(tasks)
            if 'next_two_days' in obj:
                tasks = sorted(obj['next_two_days'], key=lambda x: x.expected_at)
                tasks_data = TechnologyCheckpointSerializer(tasks, many=True).data
                obj['next_two_days'] = tasks_data
                obj['next_two_days_count'] = len(tasks)
                result_statistics['next_two_days_count'] = result_statistics['next_two_days_count'] + len(tasks)
            result_data.append(obj)
    return api_success(data=result_statistics)


@api_view(['GET', ])
def project_detail(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    data = ProjectDashBoardSerializer(project).data
    data = complete_project_data(data, request.user)
    return api_success(data)


@api_view(['GET', ])
def ongoing_projects(request):
    user = request.user
    if user.is_superuser:
        user_projects = Project.ongoing_projects().order_by('created_at')
    else:
        projects = Project.ongoing_projects()
        user_projects = get_user_projects(user, projects)
    projects_data, headers = build_pagination_queryset_data(request, user_projects, ProjectDashBoardSerializer)

    # 这里聚合了Gitlab、日报、Test多端数据
    # 你当静静的阅读的代码 想想如何让它更流畅
    # 快乐 肯定每个瞬间 要求永恒快乐
    # 肯定 肯定一切过去 要求永恒轮回
    projects_data = complete_projects_data(projects_data, user)
    return api_success(projects_data, headers=headers)


def complete_project_data(project_data, user):
    data = [project_data, ]
    data = complete_projects_data(data, user)
    return data[0]


def complete_projects_data(projects_data, user):
    # 登录用户的未读消息数量
    projects_data = build_projects_user_unread_comment_count(projects_data, user)
    # 登录用户的bugs、需要阅读的日报
    projects_data = build_projects_user_daily_works_bugs_count(projects_data, user)
    # 每个职位的日报数据
    projects_data = projects_data_add_positions_daily_works_data(projects_data)
    # 每个职位的gitlab代码提交数据
    # 定时任务的配合rebuild_ongoing_projects_developers_gitlab_commits_cache_data
    projects_data = projects_data_add_positions_gitlab_commits_data(projects_data, with_committers=False)
    return projects_data
