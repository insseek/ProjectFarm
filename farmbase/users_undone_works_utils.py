from django.db.models import Q
from datetime import datetime, timedelta

from django.utils import timezone

from projects.models import Project, GanttTaskTopic, TechnologyCheckpoint
from finance.models import JobContract
from playbook.models import CheckItem
from tasks.models import Task
from workorder.models import CommonWorkOrder
from farmbase.permissions_utils import has_function_perm, has_any_function_perms


# 待办事项
def get_user_today_undone_tasks(user=None, today=None, with_manage_project_tasks=False):
    today = today or timezone.now().date()

    tasks = Task.objects.filter(is_done=False, expected_at__lte=today)
    if user:
        tasks = tasks.filter(principal_id=user.id)
        if with_manage_project_tasks:
            my_project_tasks = Task.objects.none()
            for project in Project.ongoing_projects().filter(manager_id=user.id):
                my_project_tasks = my_project_tasks | project.undone_tasks().filter(
                    expected_at__lte=today)
            if my_project_tasks:
                tasks = tasks | my_project_tasks

    tasks = tasks.distinct()
    return tasks


# 甘特图任务
def get_user_today_undone_gantt_tasks(user=None, today=None, with_manage_project_tasks=False):
    today = today or timezone.now().date()
    projects = Project.ongoing_projects().order_by('created_at')
    tasks = GanttTaskTopic.objects.none()
    # 未完成的甘特图任务
    for project in projects:
        gantt_chart = getattr(project, 'gantt_chart', None)
        if not gantt_chart:
            continue
        project_tasks = gantt_chart.task_topics.filter(is_done=False, expected_finish_time__lte=today)
        if user:
            # 项目经理 展示自己的项目中的所有人的甘特图任务；其他人 只展示自己的
            if not (with_manage_project_tasks and project.manager_id == user.id):
                project_tasks = project_tasks.filter(is_dev_done=False, role__user_id=user.id)
        else:
            project_tasks = project_tasks.filter(is_dev_done=False)
        tasks = tasks | project_tasks
    return tasks


# Playbook任务
def get_user_today_undone_playbook_tasks(user=None, today=None, only_expected_date=False):
    today = today or timezone.now().date()
    # 未完成的Playbook任务
    '''
    参数only_expected_date：只统计有期望日期的Playbook任务
    1、未完成（按照优先级排序）（PMO>PM）
    （1）之前阶段的未完成任务
    （2）本阶段截止日期在今日及今日前的未完成任务
    （3）该阶段结束当天，显示当前阶段的所有未完成任务
    （4）先按照项目创建时间正序排序，项目中按照截止时间正序排列
    2、未来两天（按照优先级排序）（PMO>PM）
    （1）截止日期在未来两天的任务
    （2）与“到了截止日期的任务”处在相同阶段组的，无截止日期的任务
    '''
    playbook_check_items = []
    projects = Project.ongoing_projects().order_by('created_at')
    for project in projects:

        member_types = []
        # 过滤单个用户
        if user:
            if project.manager_id == user.id:
                member_types.append('manager')
            if project.product_manager_id == user.id:
                member_types.append('product_manager')
            if not member_types:
                continue
        stages = project.playbook_stages.order_by('index')
        # 过滤单个用户
        if user:
            stages = stages.filter(member_type__in=member_types).order_by('index')
        # 上一个阶段的任务全部统计
        # 当前阶段 如果是最后一天全部统计
        # 其他根据期望日期统计
        for num, stage in enumerate(stages):
            is_stage_end_date = stage.is_current_stage and stage.stage_end_date == today
            need_expected_date = only_expected_date or stage.is_next_stage or not is_stage_end_date
            need_today_done = stage.is_previous_stage or is_stage_end_date
            for check_group in stage.check_groups.order_by('index'):
                for check_item in check_group.check_items.filter(completed_at__isnull=True):
                    if need_expected_date:
                        if check_item.expected_date and check_item.expected_date <= today:
                            playbook_check_items.append(check_item)
                    elif need_today_done:
                        playbook_check_items.append(check_item)
    return playbook_check_items


# TPM检查点
def get_user_today_tpm_checkpoints_tasks(user=None, today=None):
    today = today or timezone.now().date()
    checkpoints = TechnologyCheckpoint.objects.none()
    projects = Project.ongoing_projects()
    # 过滤单个用户
    if user:
        projects = projects.filter(tpm_id=user.id)
    for p in projects:
        checkpoints = checkpoints | p.technology_checkpoints.filter(status='pending', expected_at__lte=today)
    return checkpoints


# 工单任务
def get_user_today_work_orders_tasks(user=None):
    '''
    1. 到截止日期仍未完成的工单数
    2. 工单已经完成了3天，仍未关闭的工单数
    3. 工单已经创建了24h仍未填写截止日期的工单数
    :param user:
    :return:
    '''
    work_orders = CommonWorkOrder.ongoing_work_orders()
    # 过滤单个用户
    if user:
        work_orders = CommonWorkOrder.user_principal_work_orders(user, queryset=work_orders)

    today = datetime.now().date()
    now = datetime.now()
    three_day_before = now - timedelta(days=3)
    undone_work_orders = work_orders.filter(
        Q(expiration_date__isnull=False) & Q(expiration_date__lte=today) & Q(status__in=[1, 2]))
    unclosed_work_orders = work_orders.filter(Q(done_at__lte=three_day_before) & Q(status=3))
    no_expected_work_orders = work_orders.filter(Q(expected_at__isnull=True) & Q(status__in=[1, 2]))

    return (undone_work_orders | unclosed_work_orders | no_expected_work_orders).distinct()


# 固定工程师合同中 未启动打款的
def get_user_developers_regular_contracts_undone_work_count(user):
    tomorrow = timezone.now().date() + timedelta(days=1)
    count = 0
    if has_any_function_perms(user, ['finance.view_all_regular_developer_contracts',
                                     'finance.view_my_regular_developer_contracts']):
        queryset = JobContract.signed_regular_contracts(user.principal_job_contracts.all())
    else:
        return 0
    for obj in queryset:
        obj_count = obj.payments.filter(status=0, expected_at__lte=tomorrow).count()
        count += obj_count
    return count
