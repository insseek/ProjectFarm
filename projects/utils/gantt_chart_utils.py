from datetime import timedelta
from copy import deepcopy
from django.db.models import Sum, IntegerField, When, Case, Q

from gearfarm.utils.datetime_utils import is_workday, get_days_count_between_date, get_date_by_timedelta_days
from projects.models import ProjectGanttChart, GanttTaskCatalogue, GanttTaskTopic, GanttRole


def only_workday_date(start_date, end_date):
    only_workday = is_workday(start_date) and is_workday(end_date)
    return only_workday


# 日期天数
def stage_days_count_by_date(start_date, end_date, only_workday=None):
    if only_workday is None:
        only_workday = only_workday_date(start_date, end_date)
    days_count = get_days_count_between_date(start_date, end_date, only_workday=only_workday)
    return days_count


# 阶段的日期天数
def stage_days_count(schedule, start_field, end_field, only_workday=None):
    start_date = getattr(schedule, start_field)
    end_date = getattr(schedule, end_field)
    return stage_days_count_by_date(start_date, end_date, only_workday=only_workday)


# 阶段是否只工作日
def stage_only_workday(schedule, start_field, end_field):
    start_date = getattr(schedule, start_field)
    end_date = getattr(schedule, end_field)
    return only_workday_date(start_date, end_date)


# 项目检查点列表的模板数据
# base_time 基准时间 对应项目日程表中不同阶段时间点
# timedelta 时间间隔 检查点与基准时间的时间间隔 以天计算

PROJECT_SCHEDULE_FIELDS = (
    {"field_name": "start_time", "verbose_name": "项目启动"},
    {"field_name": "prd_confirmation_time", "verbose_name": "原型确认"},

    {"field_name": "ui_start_time", "verbose_name": "设计开始"},
    {"field_name": "ui_confirmation_time", "verbose_name": "设计确认"},
    {"field_name": "dev_start_time", "verbose_name": "开发开始"},
    {"field_name": "dev_completion_time", "verbose_name": "开发结束"},
    {"field_name": "test_start_time", "verbose_name": "测试开始"},
    {"field_name": "test_completion_time", "verbose_name": "测试结束"},
    {"field_name": "delivery_time", "verbose_name": "交付审核"},
)

STAGE_CHOICES = (
    ('prd', '原型'),
    ('design', '设计'),
    ('development', '开发'),
    ('test', '测试'),
    ('acceptance', '验收')
)

GANTT_CHART_TASK_TEMPLATES = {
    'prd': [
        {
            'name': '原型制作',
            'role': {'role_type': "manager", "name": "项目经理"},
            'start_time': {'base_time': 'start_date', 'time_delta': {'days': 0}},
            'expected_finish_time': {'base_time': 'start_date', 'time_delta': {'days': 3}},
        },
        {
            'name': '原型客户沟通确认',
            'role': {'role_type': "manager", "name": "项目经理"},
            'start_time': {'base_time': 'start_date', 'time_delta': {'days': 4}},
            'expected_finish_time': {'base_time': 'start_date', 'time_delta': {'days': 5}},
        },
        {
            'name': 'PRD制作',
            'role': {'role_type': "manager", "name": "项目经理"},
            'start_time': {'base_time': 'start_date', 'time_delta': {'days': 6}},
            'expected_finish_time': {'base_time': 'end_date', 'time_delta': {'days': -2}},
        },

        {
            'name': 'PRD客户沟通确认',
            'role': {'role_type': "manager", "name": "项目经理"},
            'start_time': {'base_time': 'end_date', 'time_delta': {'days': -1}},
            'expected_finish_time': {'base_time': 'end_date', 'time_delta': {'days': 0}},
        },
        {
            'name': '确认开发方案',
            'role': {'role_type': "manager", "name": "项目经理"},
            'start_time': {'base_time': 'end_date', 'time_delta': {'days': 0}},
            'expected_finish_time': {'base_time': 'end_date', 'time_delta': {'days': 1}},
        },
        {
            'name': '确认开发计划排期',
            'role': {'role_type': "manager", 'name': '项目经理'},
            'start_time': {'base_time': 'end_date', 'time_delta': {'days': 1}},
            'expected_finish_time': {'base_time': 'end_date', 'time_delta': {'days': 2}},
        },

    ],

    'design': [
        {
            'name': '设计需求沟通（与客户和设计师）',
            'role': {'role_type': 'manager', 'name': '设计'},
            'start_time': {'base_time': 'start_date', 'time_delta': {'days': 0}},
            'expected_finish_time': {'base_time': 'start_date', 'time_delta': {'days': 0}},
        },
        {
            'name': '设计风格输出',
            'role': {'role_type': 'designer', 'name': '设计'},
            'start_time': {'base_time': 'start_date', 'time_delta': {'days': 0}},
            'expected_finish_time': {'base_time': 'start_date', 'time_delta': {'days': 2}},
        },
        {
            'name': '设计风格客户沟通确认',
            'role': {'role_type': 'manager', 'name': '项目经理'},
            'start_time': {'base_time': 'start_date', 'time_delta': {'days': 3}},
            'expected_finish_time': {'base_time': 'start_date', 'time_delta': {'days': 3}},
        },
        {
            'name': '设计图输出',
            'role': {'role_type': 'designer', 'name': '设计'},
            'start_time': {'base_time': 'start_date', 'time_delta': {'days': 4}},
            'expected_finish_time': {'base_time': 'end_date', 'time_delta': {'days': -2}},
        },
        {
            'name': '设计图客户沟通确认',
            'role': {'role_type': 'manager', 'name': '项目经理'},
            'start_time': {'base_time': 'end_date', 'time_delta': {'days': -1}},
            'expected_finish_time': {'base_time': 'end_date', 'time_delta': {'days': 0}},
        },
    ],
    'development': [
        {
            'name': '测试用例输出',
            'role': {"role_type": "test", "name": "测试"},
            'start_time': {'base_time': 'start_date', 'time_delta': {'days': 0}},
            'expected_finish_time': {'base_time': 'start_date', 'time_delta': {'days': 2}},
        },
        {
            'name': '阶段冒烟测试',
            'role': {'role_type': "manager", "name": "项目经理"},
            'start_time': {'base_time': 'end_date', 'time_delta': {'days': -1}},
            'expected_finish_time': {'base_time': 'end_date', 'time_delta': {'days': -1}},
        },
        {
            'name': '阶段测试',
            'role': {"role_type": "test", "name": "测试"},
            'start_time': {'base_time': 'end_date', 'time_delta': {'days': 0}},
            'expected_finish_time': {'base_time': 'end_date', 'time_delta': {'days': 0}},
        },
        {
            'name': 'P0 BUG修复',
            'role': {"role_type": "developer", "name": "工程师"},
            'start_time': {'base_time': 'end_date', 'time_delta': {'days': -1}},
            'expected_finish_time': {'base_time': 'end_date', 'time_delta': {'days': 0}},
        },
    ],

    'test': [
        {
            'name': '冒烟测试',
            'role': {'role_type': "manager", 'name': '项目经理'},
            'start_time': {'base_time': 'start_date', 'time_delta': {'days': 0}},
            'expected_finish_time': {'base_time': 'start_date', 'time_delta': {'days': 1}},
        },
        {
            'name': '全量测试',
            'role': {"role_type": "test", "name": "测试"},
            'start_time': {'base_time': 'start_date', 'time_delta': {'days': 2}},
            'expected_finish_time': {'base_time': 'end_date', 'time_delta': {'days': 0}},
        },
        {
            'name': 'UI走查',
            'role': {'role_type': 'designer', 'name': '设计'},
            'start_time': {'base_time': 'start_date', 'time_delta': {'days': 3}},
            'expected_finish_time': {'base_time': 'end_date', 'time_delta': {'days': 0}},
        },

    ],
    'acceptance': [
        {
            'name': '客户验收',
            'role': {'role_type': 'manager', 'name': '项目经理'},
            'start_time': {'base_time': 'start_date', 'time_delta': {'days': 0}},
            'expected_finish_time': {'base_time': 'end_date', 'time_delta': {'days': 0}},
        },
        {
            'name': '项目复盘',
            'role': {'role_type': 'manager', 'name': '项目经理'},
            'start_time': {'base_time': 'start_date', 'time_delta': {'days': 5}},
            'expected_finish_time': {'base_time': 'start_date', 'time_delta': {'days': 7}},
        },
        {
            'name': '正式环境全量测试',
            'role': {"role_type": "test", "name": "测试"},
            'start_time': {'base_time': 'end_date', 'time_delta': {'days': 1}},
            'expected_finish_time': {'base_time': 'end_date', 'time_delta': {'days': 2}},
        }
    ],

}


# 通过模板中start_time、expected_finish_time构造日期
def build_gantt_task_start_end_time(build_data, schedule, only_workday=False):
    base_time_field = build_data['base_time']
    time_delta_days = build_data['time_delta']['days']
    start_time = getattr(schedule, base_time_field)
    result_date = get_date_by_timedelta_days(start_time, time_delta_days, only_workday=only_workday)
    return result_date


def rebuild_project_gantt_role(project, role_data, gantt_chart=None):
    '''项目人员修改后 甘特图角色的名称及绑定的人员随之变化
                项目人员修改后  自动创建新的甘特图角色
                原项目人员   未完成的甘特图任务  自动分配给新的项目人员
                原项目人员   已完成的甘特图任务  保持不变
                原项目人员   如果没有任何甘特图任务   自动删除其对应的甘特图角色'''
    gantt_chart = gantt_chart if gantt_chart else getattr(project, 'gantt_chart', None)
    role_name = role_data['name']
    role_type = role_data['field_name']
    role_user = getattr(project, role_type, None)
    role_name = role_name + '-' + role_user.username if role_user else role_name

    # 已存在对应项目成员的角色
    exists_roles = GanttRole.objects.filter(gantt_chart=gantt_chart, role_type=role_type)

    if exists_roles.exists():
        # 项目成员存在
        if role_user:
            # 将没有绑定用户的角色绑定用户
            exists_roles.filter(Q(user=role_user) | Q(user=None)).update(user=role_user, name=role_name)
            new_member_roles = GanttRole.objects.filter(gantt_chart=gantt_chart, role_type=role_type,
                                                        user=role_user)
            new_member_role = new_member_roles.first()
            if not new_member_role:
                new_member_role = GanttRole.objects.create(gantt_chart=gantt_chart, role_type=role_type,
                                                           name=role_name, user=role_user)
            # 将该项目成员对应的角色清理成一个
            for role in new_member_roles:
                if role.id != new_member_role.id:
                    role.task_topics.update(role=new_member_role)
                    if not role.task_topics.exists():
                        role.delete()

            # 将绑定了其他项目成员的角色的未完成任务转给新角色
            other_roles = GanttRole.objects.filter(gantt_chart=gantt_chart, role_type=role_type).exclude(
                user=role_user)
            for other_role in other_roles:
                other_role.task_topics.filter(is_dev_done=False, is_done=False).update(role=new_member_role)
                if not other_role.task_topics.exists():
                    other_role.delete()
        # 项目成员不存在
        else:
            pass
    else:
        GanttRole.objects.create(gantt_chart=gantt_chart, role_type=role_type,
                                 name=role_name, user=role_user)


def init_project_gantt_roles(project):
    gantt_chart = getattr(project, 'gantt_chart', None)
    if gantt_chart:
        # 甘特图角色
        for role_data in project.PROJECT_MEMBERS_FIELDS:
            role_type = role_data['field_name']
            # 项目导师不创建甘特图角色
            if role_type == 'mentor':
                continue
            rebuild_project_gantt_role(project, role_data, gantt_chart)


def get_gantt_role_by_template(project, gantt_chart, role_data):
    role_name = role_data['name']
    role_type = role_data['role_type']
    role_user = getattr(project, role_type, None)
    role_name = role_name + '-' + role_user.username if role_user else role_name
    gantt_role = GanttRole.objects.filter(gantt_chart=gantt_chart, role_type=role_type,
                                          name=role_name, user=role_user).first()
    if not gantt_role:
        gantt_role = GanttRole.objects.create(gantt_chart=gantt_chart, role_type=role_type,
                                              name=role_name, user=role_user)
    return gantt_role


def init_gantt_task_by_template(project, gantt_chart, stage, catalogue, topic_data, topic_number, create_new=True):
    role_data = topic_data['role']
    gantt_role = get_gantt_role_by_template(project, gantt_chart, role_data)
    topic_name = topic_data['name']
    exists_topics = None
    # 不创建新的  只更新未完成的任务时间
    if not create_new:
        exists_topics = GanttTaskTopic.objects.filter(gantt_chart=gantt_chart, catalogue=catalogue, name=topic_name,
                                                      role=gantt_role, auto_created=True,
                                                      is_dev_done=False, is_done=False)
        if not exists_topics.exists():
            return

    if create_new:
        topic_number = topic_number or get_current_gantt_catalogue_task_max_number(catalogue) + 1
    stage_start_date = getattr(stage, 'start_date')
    stage_end_date = getattr(stage, 'end_date')
    only_workday = stage_only_workday(stage, 'start_date', 'end_date')
    start_time_data = topic_data['start_time']
    expected_finish_time_data = topic_data['expected_finish_time']

    start_time = build_gantt_task_start_end_time(start_time_data, stage, only_workday)
    expected_finish_time = build_gantt_task_start_end_time(expected_finish_time_data, stage,
                                                           only_workday)

    # 如果 甘特图任务结束时间比起始时间小；取起始时间   （起始时间基于项目开始时间+n; 结束时间基于阶段结束时间-n）
    if expected_finish_time < start_time:
        if start_time > stage_end_date:
            start_time = stage_end_date
        expected_finish_time = start_time
        timedelta_days = 1
    elif expected_finish_time == start_time:
        timedelta_days = 1
    else:
        timedelta_days = get_days_count_between_date(start_time, expected_finish_time,
                                                     only_workday=only_workday)
    if create_new:
        GanttTaskTopic.objects.create(
            gantt_chart=gantt_chart,
            catalogue=catalogue,
            role=gantt_role,
            name=topic_name,
            start_time=start_time,
            only_workday=only_workday,
            timedelta_days=timedelta_days,
            expected_finish_time=expected_finish_time,
            number=topic_number,
            auto_created=True,
        )
    else:
        exists_topics.filter(is_dev_done=False, is_done=False).update(start_time=start_time,
                                                                      only_workday=only_workday,
                                                                      timedelta_days=timedelta_days,
                                                                      expected_finish_time=expected_finish_time)


def init_gantt_catalogue_by_template(gantt_chart, project_stage, catalogue_number):
    catalogue = GanttTaskCatalogue.objects.filter(gantt_chart=gantt_chart, project_stage=project_stage,
                                                  auto_created=True).first()
    catalogue_name = project_stage.name
    if not catalogue:
        if catalogue_number is None:
            catalogue_number = get_current_gantt_catalogue_max_number(gantt_chart) + 1
        catalogue = GanttTaskCatalogue.objects.create(gantt_chart=gantt_chart,
                                                      project_stage=project_stage,
                                                      name=catalogue_name,
                                                      auto_created=True,
                                                      number=catalogue_number)
    return catalogue


# 初始化甘特图模板
def init_project_gantt_template(project):
    # 项目阶段
    gantt_chart, created = ProjectGanttChart.objects.get_or_create(project_id=project.id)
    project_stages = project.project_stages.order_by('index')
    # 甘特图角色
    init_project_gantt_roles(project)
    catalogue_number = get_current_gantt_catalogue_max_number(gantt_chart) + 1
    for project_stage in project_stages:
        catalogue_number += 1
        build_project_stage_gantt_chart(project, gantt_chart, project_stage, catalogue_number)


def build_project_stage_gantt_chart(project, gantt_chart, project_stage, catalogue_number=None):
    catalogue_number = catalogue_number or get_current_gantt_catalogue_max_number(gantt_chart) + 1
    catalogue = init_gantt_catalogue_by_template(gantt_chart, project_stage, catalogue_number)
    stage_type = project_stage.stage_type
    tasks_template = GANTT_CHART_TASK_TEMPLATES[stage_type]
    topic_number = 1
    for topic_data in tasks_template:
        init_gantt_task_by_template(project, gantt_chart, project_stage, catalogue, topic_data, topic_number)
        topic_number += 1
    project_stage.gantt_chart_built = True
    project_stage.save()


def update_project_gantt_template(project):
    '''
    根据最新项目阶段更新甘特图模板
    1. 增加的阶段：生成新的
    2. 删除阶段
        1. 不修改甘特图
    3. 修改的阶段  对应的分类下的任务
        1. 若已经勾选完成，不更新时间（有一个勾选就算）
        2. 若未勾选完成，且模版任务的任务名称，角色未被修改
            1. 按照新的时间节点更新时间
    :param project:
    :return:
    '''
    # 甘特图角色
    init_project_gantt_roles(project)
    # 项目阶段
    gantt_chart, created = ProjectGanttChart.objects.get_or_create(project_id=project.id)
    project_stages = project.project_stages.order_by('index')
    for project_stage in project_stages:
        if not project_stage.gantt_chart_built:
            build_project_stage_gantt_chart(project, gantt_chart, project_stage)
        else:
            catalogue = project_stage.gantt_chart_catalogues.first()
            if catalogue:
                stage_type = project_stage.stage_type
                tasks_template = GANTT_CHART_TASK_TEMPLATES[stage_type]
                for topic_data in tasks_template:
                    init_gantt_task_by_template(project, gantt_chart, project_stage, catalogue, topic_data, None,
                                                create_new=False)


def get_current_gantt_catalogue_task_max_number(task_catalogue):
    max_number = 0
    topics = task_catalogue.task_topics.all().order_by('-number')
    if topics.exists():
        max_number = topics.first().number
    return max_number


def get_current_gantt_catalogue_max_number(project_gantt):
    max_number = 0
    if project_gantt:
        task_catalogues = project_gantt.task_catalogues.all().order_by('-number')
        if task_catalogues.exists():
            max_number = task_catalogues.first().number
    return max_number


def get_current_gantt_task_or_catalogue_next_siblings(gantt_task):
    current_number = gantt_task.number
    if hasattr(gantt_task, 'catalogue') and gantt_task.catalogue:
        previous_siblings = gantt_task.catalogue.task_topics.filter(number__gte=current_number).exclude(
            pk=gantt_task.id)
    else:
        project_gantt = gantt_task.gantt_chart
        previous_siblings = project_gantt.task_catalogues.filter(number__gte=current_number).exclude(pk=gantt_task.id)
    gantt_tasks = sorted(previous_siblings, key=lambda task: task.number, reverse=False)
    return gantt_tasks


def get_current_gantt_task_or_catalogue_next_sibling(gantt_task):
    gantt_tasks = get_current_gantt_task_or_catalogue_next_siblings(gantt_task)
    if gantt_tasks:
        return gantt_tasks[0]
    return None


def get_current_gantt_task_or_catalogue_previous_siblings(gantt_task):
    current_number = gantt_task.number
    if hasattr(gantt_task, 'catalogue') and gantt_task.catalogue:
        previous_siblings = gantt_task.catalogue.task_topics.filter(number__lte=current_number).exclude(
            pk=gantt_task.id)
    else:
        project_gantt = gantt_task.gantt_chart
        previous_siblings = project_gantt.task_catalogues.filter(number__lte=current_number).exclude(pk=gantt_task.id)
    gantt_tasks = sorted(previous_siblings, key=lambda task: task.number, reverse=True)
    return gantt_tasks


def get_current_gantt_task_or_catalogue_previous_sibling(gantt_task):
    gantt_tasks = get_current_gantt_task_or_catalogue_previous_siblings(gantt_task)
    if gantt_tasks:
        return gantt_tasks[0]
    return None


def move_up_current_gantt_task_or_catalogue_next_siblings(gantt_task):
    next_siblings = get_current_gantt_task_or_catalogue_next_siblings(gantt_task)
    for task in next_siblings:
        task.number = task.number - 1
        task.save()
