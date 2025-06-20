from datetime import timedelta
from copy import deepcopy

from django.contrib.auth.models import Group
from django.core.cache import cache
from django.db.models import Q

from logs.models import Log

# 项目技术检查点列表的模板数据
# base_time 基准时间 对应项目日程表中不同阶段时间点
# timedelta 时间间隔 检查点与基准时间的时间间隔 以天计算
TECHNOLOGY_CHECKPOINT_LINKED_LIST_TEMPLATE = [
    # {'name': '制定开发方案', 'base_time': 'start_date', 'time_delta': {'days': -3}, 'flag': 'sprint'},
    # {'name': '详细开发计划排期', 'base_time': 'start_date', 'time_delta': {'days': -3}, 'flag': 'sprint'},

    {'name': '工程师规范同步', 'base_time': 'start_date', 'time_delta': {'days': -3}, 'flag': None},
    {'name': 'Git配置', 'base_time': 'start_date', 'time_delta': {'days': -1}, 'flag': None},

    {'name': '开发资料准备', 'base_time': 'start_date', 'time_delta': {'days': -1}, 'flag': None},
    {'name': '开发测试环境部署', 'base_time': 'start_date', 'time_delta': {'days': 2}, 'flag': None},

    {'name': '数据库和API评审', 'base_time': 'start_date', 'time_delta': {'days': 1}, 'flag': 'sprint'},
    {'name': '代码审核', 'base_time': 'end_date', 'time_delta': {'days': -1}, 'flag': 'sprint'},
]

PROTOTYPE_TECHNOLOGY_CHECKPOINT_LINKED_LIST_TEMPLATE = [
    {'name': '制定开发方案', 'base_time': 'end_date', 'time_delta': {'days': 3}, 'flag': 'sprint'},
    {'name': '详细开发计划排期', 'base_time': 'end_date', 'time_delta': {'days': 3}, 'flag': 'sprint'},
]

TECHNOLOGY_CHECKPOINT_NAME_LIST = [
    '制定开发方案',
    '详细开发计划排期',
    '工程师规范同步',
    'Git配置',
    '开发资料准备',
    '开发测试环境部署',
    '数据库和API评审',
    '代码审核'
]

# TPM， 项目经理， 测试，
# 项目日程表 各阶段时间顺序列表
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


def init_project_stages_technology_checkpoints(project, stage_type):
    from projects.models import TechnologyCheckpoint

    if stage_type == 'prd':
        template = PROTOTYPE_TECHNOLOGY_CHECKPOINT_LINKED_LIST_TEMPLATE
    elif stage_type == 'development':
        template = TECHNOLOGY_CHECKPOINT_LINKED_LIST_TEMPLATE
    else:
        return

    stages = project.project_stages.filter(stage_type=stage_type).order_by('start_date')
    if stages:
        for checkpoint_data in template:
            name = checkpoint_data['name']
            flag = checkpoint_data['flag']
            base_date = checkpoint_data['base_time']
            if flag and flag == 'sprint':
                for index, stage in enumerate(stages):
                    expected_at = getattr(stage, base_date) + timedelta(
                        days=checkpoint_data['time_delta']['days'])
                    TechnologyCheckpoint.objects.create(project=project, name=name, expected_at=expected_at,
                                                        project_stage=stage)
            else:
                expected_at = getattr(stages[0], base_date) + timedelta(
                    days=checkpoint_data['time_delta']['days'])
                TechnologyCheckpoint.objects.create(project=project, name=name, expected_at=expected_at)


def init_project_technology_checkpoints(project):
    '''
    每个阶段重复的检查点应该绑定阶段 阶段起始结束日期更改的时候  未完成检查点应该变化
    '''
    init_project_stages_technology_checkpoints(project, 'prd')
    init_project_stages_technology_checkpoints(project, 'development')


def update_project_stages_technology_checkpoints(project, stage_type):
    from projects.models import TechnologyCheckpoint
    if stage_type == 'prd':
        template = PROTOTYPE_TECHNOLOGY_CHECKPOINT_LINKED_LIST_TEMPLATE
    elif stage_type == 'development':
        template = TECHNOLOGY_CHECKPOINT_LINKED_LIST_TEMPLATE
    else:
        return
    stages = project.project_stages.filter(stage_type=stage_type).order_by('start_date')
    new_checkpoint_ids = set()
    if stages:
        for checkpoint_data in template:
            name = checkpoint_data['name']
            flag = checkpoint_data['flag']
            base_date = checkpoint_data['base_time']
            if flag and flag == 'sprint':
                for index, stage in enumerate(stages):
                    checkpoint, created = TechnologyCheckpoint.objects.get_or_create(project=project, name=name,
                                                                                     project_stage=stage)
                    if checkpoint.status == 'pending':
                        expected_at = getattr(stage, base_date) + timedelta(
                            days=checkpoint_data['time_delta']['days'])
                        checkpoint.expected_at = expected_at
                        checkpoint.save()
                    new_checkpoint_ids.add(checkpoint.id)
            else:
                checkpoint, created = TechnologyCheckpoint.objects.get_or_create(project=project, name=name)
                if checkpoint.status == 'pending':
                    expected_at = getattr(stages[0], base_date) + timedelta(
                        days=checkpoint_data['time_delta']['days'])
                    checkpoint.expected_at = expected_at
                    checkpoint.save()
                new_checkpoint_ids.add(checkpoint.id)
    return new_checkpoint_ids


def update_project_technology_checkpoints(project):
    '''
    项目阶段被修改      项目阶段的TPM检查点应该调整
    * 5-8 *检查点*   需要绑定  某个开发阶段
* 新建项目/阶段调整   更新*未完成*的TPM检查点
    * 如果没有开发阶段： 不创建/删除本项目所有*未完成检查点*
    *
    * 如果有开发阶段
    * 1-4检查点
        * 如果1-4不存在
            * 取 *开始时间最早的开发阶段  生成1-4    生成本阶段的5-8*
        * 如果1-4 存在
            * 取 *开始时间最早的开发阶段  更新未完成1-4 TPM检查点的日期*
    * 新增开发阶段： 生成本阶段的5-8
    * 修改开发阶段（起始日期）：*更新 本阶段的未完成的5-8检查点*
    * 删除开发阶段：删除 *本阶段*  *未完成的5-8检查点*
    :param project:
    :return:
    '''

    prd_checkpoint_ids = update_project_stages_technology_checkpoints(project, 'prd')
    dev_checkpoint_ids = update_project_stages_technology_checkpoints(project, 'development')
    checkpoint_ids = prd_checkpoint_ids | dev_checkpoint_ids
    project.technology_checkpoints.exclude(Q(pk__in=checkpoint_ids) | Q(status='done')).delete()


def update_ongoing_projects_technology_checkpoints():
    from projects.models import Project
    ongoing_projects = Project.ongoing_projects()
    for p in ongoing_projects:
        update_project_technology_checkpoints(p)
