from datetime import timedelta, datetime
from copy import deepcopy
from pprint import pprint

from django.core.cache import cache
from django.contrib.contenttypes.models import ContentType

from playbook.models import Stage, ChecklistItem, CheckItem, InfoItem, LinkItem, Template, TemplateStage, \
    TemplateCheckGroup, TemplateCheckItem, TemplateLinkItem
from projects.models import Project
from proposals.models import Proposal
from playbook.serializers import TemplateSerializer
from playbook.models import Stage as PlaybookStage


def reset_playbook_cache_data(online_template):
    if online_template.status == 'online':
        template_type = online_template.template_type
        cache_key = '{template_type}_playbook_template_data'.format(template_type=template_type)
        cache_data = cache.get(cache_key, {})
        stages_data = TemplateSerializer(online_template).data['stages']
        cache_data[online_template.member_type] = stages_data
        cache.set(cache_key, cache_data, None)
        return cache_data


def build_proposal_playbook_cache_data():
    proposal_playbook_templates = {}
    online_templates = Template.objects.filter(template_type='proposal', status='online', is_active=True)
    for online_template in online_templates:
        stages_data = TemplateSerializer(online_template).data['stages']
        proposal_playbook_templates[online_template.member_type] = stages_data
    cache.set('proposal_playbook_template_data', proposal_playbook_templates, None)
    return proposal_playbook_templates


def build_project_playbook_cache_data():
    project_playbook_templates = {}
    online_templates = Template.objects.filter(template_type='project', status='online', is_active=True)
    for online_template in online_templates:
        stages_data = TemplateSerializer(online_template).data['stages']
        project_playbook_templates[online_template.member_type] = stages_data
    cache.set('project_playbook_template_data', project_playbook_templates, None)
    return project_playbook_templates


def get_proposal_playbook_templates_data():
    data = cache.get('proposal_playbook_template_data', {})
    if not data:
        return build_proposal_playbook_cache_data()
    return data


def get_project_playbook_templates_data():
    data = cache.get('project_playbook_template_data', {})
    if not data:
        return build_project_playbook_cache_data()
    return data


def initialize_proposal_playbook(proposal):
    playbook_templates = get_proposal_playbook_templates_data()
    initialize_object_playbook(proposal, playbook_templates)


def migrate_projects_playbook():
    online_templates = Template.objects.filter(template_type='project', status='online', is_active=True)
    for template in online_templates:
        template.check_items.filter(period='sprint').update(period='once')
    build_project_playbook_cache_data()
    '''
    生成新的项目阶段后，将项目阶段与原来的playbook关联

    注意：有多个开发阶段的， 第一个开发阶段与当前playbook中开发阶段关联。
        对于其他开发阶段：
        如果项目在进行中，且本开发阶段未完成，则为其生成新的playbook任务；
        否则：绑定一个空的playbook开发阶段
    :return:
    '''
    today = datetime.now().date()
    projects = Project.objects.all()
    playbook_templates = get_project_playbook_templates_data()
    playbook_templates_dict = {}
    for member_type, stages_templates in playbook_templates.items():
        playbook_templates_dict[member_type] = {i['stage_code']: i for i in stages_templates}

    for project in projects:
        stages = project.project_stages.order_by('index')
        playbook_stages = project.playbook_stages.all()
        project_done = True if project.done_at or project.end_date <= today else False
        dev_stage_migrated = False
        stage_index = 0
        for stage_index, project_stage in enumerate(stages):
            stage_type = project_stage.stage_type
            if stage_type != 'development':
                playbook_stages.filter(stage_code=stage_type).update(
                    project_stage=project_stage,
                    index=stage_index
                )
            else:
                if not dev_stage_migrated:
                    playbook_stages.filter(stage_code=stage_type).update(
                        project_stage=project_stage,
                        index=stage_index
                    )
                    dev_stage_migrated = True
                else:
                    if not project_done and project_stage.end_date > today:
                        for member_type, template_dict in playbook_templates_dict.items():
                            stage_data = template_dict['development']
                            initialize_project_stage_playbook(project, project_stage, stage_data, stage_index,
                                                              member_type)
                    else:
                        for member_type in playbook_templates_dict:
                            PlaybookStage.objects.create(name=project_stage.name, index=stage_index,
                                                         project_stage=project_stage,
                                                         stage_code='development',
                                                         content_object=project, member_type=member_type)


def initialize_project_stage_playbook(project, project_stage, stage_data, stage_index, member_type):
    stage_name = project_stage.name
    playbook_stage = PlaybookStage.objects.create(name=stage_name, index=stage_index,
                                                  project_stage=project_stage,
                                                  stage_code=stage_data['stage_code'],
                                                  content_object=project, member_type=member_type)
    # 分组列表
    check_groups = stage_data['check_groups']
    for group_index, group_data in enumerate(check_groups):
        check_group = ChecklistItem.objects.create(description=group_data['description'], index=group_index,
                                                   stage=playbook_stage)
        # 检查项列表
        check_items = group_data['check_items']
        for check_item_index, check_item_data in enumerate(check_items):
            notice = check_item_data.get('notice', None)
            period = check_item_data.get('period', 'once')
            expected_date_base = check_item_data.get('expected_date_base', None)
            expected_date_base_timedelta_days = check_item_data.get('expected_date_base_timedelta_days', None)
            expected_weekday = check_item_data.get('expected_weekday', None)

            check_item = CheckItem.objects.create(type=check_item_data['type'],
                                                  description=check_item_data['description'],
                                                  period=period,
                                                  notice=notice,
                                                  expected_date_base=expected_date_base,
                                                  expected_date_base_timedelta_days=expected_date_base_timedelta_days,
                                                  expected_weekday=expected_weekday,
                                                  index=check_item_index, check_group=check_group)
            # 检查项的links
            check_item_links = check_item_data['links']
            for link_index, link_data in enumerate(check_item_links):
                LinkItem.objects.create(name=link_data['name'], url=link_data['url'],
                                        index=link_index, content_object=check_item)


def initialize_project_playbook(project):
    playbook_templates = get_project_playbook_templates_data()
    for member_type, stages_templates in playbook_templates.items():
        # 项目的 产品经理playbook停用
        if member_type == "product_manager":
            continue
        playbook_templates_dict = {i['stage_code']: i for i in stages_templates}
        project_stages = project.project_stages.order_by('index')
        for stage_index, project_stage in enumerate(project_stages):
            stage_data = playbook_templates_dict[project_stage.stage_type]
            initialize_project_stage_playbook(project, project_stage, stage_data, stage_index, member_type)


def update_project_playbook_for_schedule_with_member_type(project, member_type, stages_templates):
    playbook_templates_dict = {i['stage_code']: i for i in stages_templates}
    project_stages = project.project_stages.order_by('index')
    stage_index = 0
    for stage_index, project_stage in enumerate(project_stages):
        playbook_stages = project_stage.playbook_stages.filter(member_type=member_type)
        playbook_stages.update(name=project_stage.name, index=stage_index)
        if playbook_stages:
            for playbook_stage in playbook_stages:
                for check_group in playbook_stage.check_groups.all():
                    for check_item in check_group.check_items.all():
                        if not check_item.completed_at:
                            check_item.build_expected_date(to_save=True)
        else:
            stage_data = playbook_templates_dict[project_stage.stage_type]
            initialize_project_stage_playbook(project, project_stage, stage_data, stage_index, member_type)


def update_project_playbook_for_schedule(project, member_type=None):
    # 项目的 产品经理playbook停用
    if member_type == "product_manager":
        return
    playbook_templates = get_project_playbook_templates_data()
    if member_type and member_type in playbook_templates:
        stages_templates = playbook_templates[member_type]
        update_project_playbook_for_schedule_with_member_type(project, member_type, stages_templates)
    else:
        for member_type, stages_templates in playbook_templates.items():
            # 项目的 产品经理playbook停用
            if member_type == "product_manager":
                continue
            update_project_playbook_for_schedule_with_member_type(project, member_type, stages_templates)


def initialize_object_playbook(content_object, playbook_templates):
    for member_type, project_stages in playbook_templates.items():
        for stage_index, stage_data in enumerate(project_stages):
            # 阶段
            stage = Stage.objects.create(name=stage_data['name'], index=stage_index,
                                         stage_code=stage_data['stage_code'],
                                         content_object=content_object, member_type=member_type)
            # 分组列表
            check_groups = stage_data['check_groups']
            for group_index, group_data in enumerate(check_groups):
                check_group = ChecklistItem.objects.create(description=group_data['description'], index=group_index,
                                                           stage=stage)

                # 检查项列表
                check_items = group_data['check_items']
                for check_item_index, check_item_data in enumerate(check_items):
                    notice = check_item_data.get('notice', None)
                    period = check_item_data.get('period', 'once')

                    expected_date_base = check_item_data.get('expected_date_base', None)
                    expected_date_base_timedelta_days = check_item_data.get('expected_date_base_timedelta_days', None)
                    expected_weekday = check_item_data.get('expected_weekday', None)

                    check_item = CheckItem.objects.create(type=check_item_data['type'],
                                                          description=check_item_data['description'],
                                                          period=period,
                                                          notice=notice,
                                                          expected_date_base=expected_date_base,
                                                          expected_date_base_timedelta_days=expected_date_base_timedelta_days,
                                                          expected_weekday=expected_weekday,
                                                          index=check_item_index, check_group=check_group)
                    # 检查项的links
                    check_item_links = check_item_data['links']
                    for link_index, link_data in enumerate(check_item_links):
                        LinkItem.objects.create(name=link_data['name'], url=link_data['url'],
                                                index=link_index, content_object=check_item)


def build_playbook_template_form_origin_data(template_data, origin_stages):
    playbook_template = Template.objects.create(**template_data)
    for stage_index, stage_data in enumerate(origin_stages):
        # 阶段
        stage = TemplateStage.objects.create(playbook_template=playbook_template, name=stage_data['name'],
                                             stage_code=stage_data['stage_code'],
                                             index=stage_index)
        if 'check_groups' not in stage_data:
            continue
        # 分组列表
        check_groups = stage_data['check_groups']
        for group_index, group_data in enumerate(check_groups):
            check_group_description = group_data['description']
            origin_id = group_data.get('id', None)
            check_group = TemplateCheckGroup.objects.create(description=check_group_description,
                                                            index=group_index, playbook_template=playbook_template,
                                                            template_stage=stage, origin_id=origin_id)
            # 检查项列表
            check_items = group_data['check_items']
            for check_item_index, check_item_data in enumerate(check_items):
                check_item_type = check_item_data['type'] or None
                period = check_item_data.get('period', 'once')
                notice = check_item_data.get('notice', None)
                origin_id = check_item_data.get('id', None)
                check_item_description = check_item_data['description']

                expected_date_base = check_item_data.get('expected_date_base', None)
                expected_date_base_timedelta_days = check_item_data.get('expected_date_base_timedelta_days', None)
                expected_weekday = check_item_data.get('expected_weekday', None)

                check_item = TemplateCheckItem.objects.create(
                    type=check_item_type,
                    period=period,
                    expected_date_base=expected_date_base,
                    expected_date_base_timedelta_days=expected_date_base_timedelta_days,
                    expected_weekday=expected_weekday,

                    description=check_item_description,
                    notice=notice,
                    index=check_item_index,
                    template_check_group=check_group,
                    playbook_template=playbook_template,
                    origin_id=origin_id)
                # 检查项的links
                check_item_links = check_item_data.get('links', [])
                for link_index, link_data in enumerate(check_item_links):
                    TemplateLinkItem.objects.create(name=link_data['name'], url=link_data['url'],
                                                    index=link_index, template_check_item=check_item)
    return playbook_template


def build_empty_playbook_template(template_data):
    from proposals.models import Proposal
    template_type = template_data['template_type']
    stages_base = []
    if template_type == 'project':
        stages_base = TemplateStage.PROJECT_STAGES
    elif template_type == 'proposal':
        stages_base = Proposal.PROPOSAL_STATUS
    origin_stages = [{"stage_code": stage_code, "name": stage_name} for stage_code, stage_name in stages_base]

    playbook_template = build_playbook_template_form_origin_data(template_data, origin_stages)

    return playbook_template


def update_ongoing_project_proposal_playbook(model_name=None):
    if model_name == 'project':
        update_ongoing_project_playbook()
    elif model_name == 'proposal':
        update_ongoing_proposal_playbook()
    else:
        update_ongoing_project_playbook()
        update_ongoing_proposal_playbook()


def update_ongoing_proposal_playbook(member_type=None):
    playbook_templates = get_proposal_playbook_templates_data()
    proposals = Proposal.ongoing_proposals()
    proposal_type = ContentType.objects.get(app_label="proposals", model="proposal")
    update_existing_objects_playbook(proposals, playbook_templates, proposal_type, member_type=member_type)


def update_ongoing_project_playbook(member_type=None):
    projects = Project.ongoing_projects()
    for project in projects:
        update_project_playbook_for_schedule(project, member_type=member_type)


def update_existing_objects_playbook(projects, playbook_templates, project_type, member_type=None):
    for project in projects:
        update_existing_object_playbook(project, playbook_templates, project_type, member_type=member_type)


def update_existing_object_playbook(project, playbook_templates, project_type, reset_current_status=False,
                                    member_type=None):
    '''
    一、历史阶段不变
    二、当前阶段及之后阶段根据模版更新
    * 1、保留已完成任务 （ 如果是每周任务、Sprint任务；根据模版更新它的期望日期基准）
    * 2、删除未完成的任务组/任务
    * 3、新建当前及之后阶段的模版中所有新的任务 (排除已保留的 任务组名和任务名相同的任务 )
    :param project:
    :param playbook_templates:
    :param project_type:
    :param reset_current_status:
    :param member_type:
    :return:
    '''
    if member_type:
        if member_type not in playbook_templates:
            return
        templates_data = {member_type: playbook_templates[member_type]}
    else:
        templates_data = playbook_templates
    for member_type, project_stages in templates_data.items():
        for stage_index, stage_data in enumerate(project_stages):
            stage_name = stage_data['name']
            stage_code = stage_data['stage_code']
            stage_project_index = Proposal.get_status_index_by_code(stage_code)
            # 当前阶段之前的playbook不更新
            if stage_project_index < project.status_index:
                continue
            # 重置当前阶段
            if stage_project_index == project.status_index and reset_current_status:
                Stage.objects.filter(name=stage_name, stage_code=stage_code, content_type_id=project_type.id,
                                     object_id=project.id, member_type=member_type).all().delete()

            # 当前阶段及之后阶段根据模版更新
            stage = Stage.objects.filter(name=stage_name, stage_code=stage_code,
                                         content_type_id=project_type.id,
                                         object_id=project.id, member_type=member_type).first()
            if not stage:
                # 阶段
                stage = Stage.objects.create(name=stage_name, stage_code=stage_code, index=stage_index,
                                             content_object=project, member_type=member_type)

            origin_check_item_ids = set()
            new_check_item_ids = set()
            # 只保留已完成任务
            for check_group in stage.check_groups.all():
                completed_tasks = check_group.check_items.filter(completed_at__isnull=False)
                origin_check_item_ids = origin_check_item_ids | set(completed_tasks.values_list('id', flat=True))
                if not completed_tasks.exists():
                    check_group.delete()
                else:
                    check_group.check_items.filter(completed_at__isnull=True).delete()

            # 分组列表
            check_groups = stage_data['check_groups']
            for group_index, group_data in enumerate(check_groups):
                check_group = ChecklistItem.objects.filter(description=group_data['description'], stage=stage).first()
                check_group_created = False
                if not check_group:
                    check_group = ChecklistItem.objects.create(description=group_data['description'], index=group_index,
                                                               stage=stage)
                    check_group_created = True

                # 检查项列表
                check_items = group_data['check_items']
                for check_item_index, check_item_data in enumerate(check_items):

                    description = check_item_data['description']
                    notice = check_item_data.get('notice', None)
                    period = check_item_data.get('period', 'once')
                    expected_date_base = check_item_data.get('expected_date_base', None)
                    expected_date_base_timedelta_days = check_item_data.get('expected_date_base_timedelta_days',
                                                                            None)
                    expected_weekday = check_item_data.get('expected_weekday', None)
                    if check_group_created:
                        check_item = CheckItem.objects.create(
                            check_group=check_group,
                            description=description,
                            type=check_item_data['type'],
                            notice=notice,
                            period=period,
                            expected_date_base=expected_date_base,
                            expected_date_base_timedelta_days=expected_date_base_timedelta_days,
                            expected_weekday=expected_weekday,
                            index=check_item_index)
                        # 检查项的links
                        check_item_links = check_item_data['links']
                        for link_index, link_data in enumerate(check_item_links):
                            LinkItem.objects.create(name=link_data['name'], url=link_data['url'],
                                                    index=link_index, content_object=check_item)
                        new_check_item_ids.add(check_item.id)
                    else:
                        check_items = CheckItem.objects.filter(check_group=check_group,
                                                               description=check_item_data['description'])
                        if check_items.exists():
                            check_items.update(type=check_item_data['type'],
                                               notice=notice,
                                               period=period,
                                               expected_date_base=expected_date_base,
                                               expected_date_base_timedelta_days=expected_date_base_timedelta_days,
                                               expected_weekday=expected_weekday,
                                               index=check_item_index)
                            for check_item in check_items:
                                # 检查项的links
                                check_item_links = check_item_data['links']
                                for link_index, link_data in enumerate(check_item_links):
                                    LinkItem.objects.create(name=link_data['name'], url=link_data['url'],
                                                            index=link_index, content_object=check_item)
                if not check_group_created:
                    check_group.rebuild_completed_at()
            # 删除的任务都改为单次 避免sprint 每周任务重置
            delete_check_item_ids = origin_check_item_ids - new_check_item_ids
            CheckItem.objects.filter(id__in=delete_check_item_ids).update(period='once')
