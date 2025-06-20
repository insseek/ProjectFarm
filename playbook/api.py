from copy import deepcopy
import logging

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from django.core.cache import cache
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from gearfarm.utils.farm_response import api_success, api_bad_request, api_request_params_required, api_error, \
    api_permissions_required
from farmbase.utils import get_protocol_host, get_active_users_by_function_perm
from farmbase.permissions_utils import func_perm_required, has_function_perms
from logs.models import Log
from playbook.models import ChecklistItem, InfoItem, Stage, LinkItem, CheckItem, Template, TemplateStage, \
    TemplateCheckGroup, TemplateCheckItem, TemplateLinkItem, TemplateRevisionHistory
from playbook.serializers import StageSerializer, TemplateSerializer, TemplateCheckGroupSerializer, \
    TemplateStageSerializer, TemplateCheckItemSerializer, TemplateCheckGroupEditSerializer, \
    TemplateRevisionHistorySerializer, TemplateListSerializer, CheckItemDateSerializer
from playbook.utils import build_playbook_template_form_origin_data, build_empty_playbook_template, \
    update_ongoing_project_proposal_playbook, reset_playbook_cache_data
from proposals.models import Proposal
from projects.models import Project, Stage
# from farmbase.signals.signals import project_playbook_check_item_task
from notifications.tasks import send_project_status_update_reminder
from notifications.utils import create_notification_to_users, create_notification
from playbook.tasks import update_ongoing_project_proposal_existing_playbook


class PlaybookTemplateList(APIView):
    def get(self, request):
        templates = Template.objects.filter(is_active=True)
        params = request.GET
        status = params.get('status', None)
        template_type = params.get('template_type', None)
        member_type = params.get('member_type', None)
        if status == 'published':
            templates = templates.exclude(status='draft')
        elif status:
            templates = templates.filter(status=status)
        if template_type:
            templates = templates.filter(template_type=template_type)
        if member_type:
            templates = templates.filter(member_type=member_type)
        templates = templates.order_by('-version')
        data = TemplateListSerializer(templates, many=True).data
        return api_success(data=data)

    def post(self, request):
        request_data = request.data
        template_type = request_data.get('template_type', None)
        member_type = request_data.get('member_type', None)

        type_choices = [k for k, v in Template.TYPE_CHOICES]
        if not (template_type and template_type in type_choices):
            return api_bad_request("template_type，可选值：{}".format(type_choices))

        if template_type == "proposal":
            if member_type != 'product_manager':
                return api_bad_request("member_type必填，可选值：{}".format('product_manager'))
        if template_type == "project":
            member_types = ["product_manager", "manager"]
            if member_type not in member_types:
                return api_bad_request("参数member_type必填，可选值：{}".format(member_types))
        version = Template.get_new_version(template_type, member_type, 'draft')
        template_data = {"template_type": template_type, "member_type": member_type, "version": version,
                         "status": 'draft', "creator": request.user, "last_operator": request.user}
        online_template = Template.get_online_template(template_type, member_type)
        if online_template:
            template_data['remarks'] = "从线上版本v{}导入初始数据".format(online_template.version)
            template_data['origin'] = online_template
            stages_data = TemplateSerializer(online_template).data['stages']
            playbook_template = build_playbook_template_form_origin_data(template_data, stages_data)
        else:
            playbook_template = build_empty_playbook_template(template_data)
        data = TemplateListSerializer(playbook_template).data
        return api_success(data=data)


@api_view(['GET'])
def proposal_online_version(request):
    member_type = request.GET.get('member_type', 'product_manager')
    template = get_object_or_404(Template, template_type='proposal', status='online', member_type=member_type)
    data = TemplateSerializer(template).data
    return api_success(data=data)


@api_view(['GET'])
def project_online_version(request):
    member_type = request.GET.get('member_type', '')
    if not member_type:
        return api_bad_request("member_type in ['manager','product_manager']")
    template = get_object_or_404(Template, template_type='project', status='online', member_type=member_type)
    data = TemplateSerializer(template).data
    return api_success(data=data)


class PlaybookTemplateDetail(APIView):
    def get(self, request, template_id):
        template = get_object_or_404(Template, id=template_id)
        data = TemplateSerializer(template).data
        return api_success(data=data)

    def delete(self, request, template_id):
        template = get_object_or_404(Template, id=template_id)
        origin = deepcopy(template)
        if template.status != 'draft':
            return api_bad_request(message="只有草稿可以删除，已发布版本不能删除")
        template.is_active = False
        template.save()
        # template.delete()
        Log.build_update_object_log(request.user, origin, template)
        return api_success()


@api_view(['POST'])
def publish_playbook_template(request, template_id):
    playbook_template = get_object_or_404(Template, pk=template_id)
    origin = deepcopy(playbook_template)
    if playbook_template.status != 'draft':
        return api_bad_request(message="Playbook草稿已发布 不能重新发布")
    if not playbook_template.is_active:
        return api_bad_request(message="Playbook草稿已被删除")

    required_perm = ''
    if playbook_template.template_type == 'proposal':
        if playbook_template.member_type == 'product_manager':
            required_perm = 'manage_proposal_pm_playbook_template'
    elif playbook_template.template_type == 'project':
        if playbook_template.member_type == 'manager':
            required_perm = 'manage_project_manager_playbook_template'
        elif playbook_template.member_type == 'product_manager':
            required_perm = 'manage_project_pm_playbook_template'
    if required_perm:
        if not has_function_perms(request.user, required_perm):
            return api_permissions_required()

    version = Template.get_new_version(playbook_template.template_type, playbook_template.member_type, 'online')
    Template.objects.filter(template_type=playbook_template.template_type, status="online",
                            member_type=playbook_template.member_type).update(status="history")
    playbook_template.version = version
    playbook_template.status = 'online'
    playbook_template.publisher = request.user
    playbook_template.published_at = timezone.now()
    if request.data.get('remarks', ''):
        playbook_template.remarks = request.data['remarks']
    playbook_template.save()
    Log.build_update_object_log(request.user, origin, playbook_template, comment="发布Playbook草稿")
    revision_history = TemplateRevisionHistory.build_playbook_template_revision_history(playbook_template)
    reset_playbook_cache_data(playbook_template)
    if settings.DEVELOPMENT:
        update_ongoing_project_proposal_existing_playbook(model_name=playbook_template.template_type,
                                                          member_type=playbook_template.member_type)
    else:
        update_ongoing_project_proposal_existing_playbook.delay(model_name=playbook_template.template_type,
                                                                member_type=playbook_template.member_type)
    # 消息推送
    need_alter_users = None
    member_type = playbook_template.member_type
    protocol_host = get_protocol_host(request)
    if revision_history:
        need_alter_users = []
        if playbook_template.template_type == 'proposal':
            notification_message = "需求Playbook已经更新，是否立即查看？"
            notification_url = protocol_host + '/playbook/templates/version_records?playbook_template_id={}&member_type={}'.format(
                playbook_template.id, member_type)
            if member_type == 'product_manager':
                need_alter_users = get_active_users_by_function_perm("view_proposal_pm_playbook_template")
        else:
            notification_message = "项目Playbook已经更新，是否立即查看？"
            notification_url = protocol_host + '/playbook/templates/version_records?playbook_template_id={}&member_type={}'.format(
                playbook_template.id, member_type)
            if member_type == 'manager':
                need_alter_users = get_active_users_by_function_perm("view_project_manager_playbook_template")
            elif member_type == 'product_manager':
                need_alter_users = get_active_users_by_function_perm("view_project_pm_playbook_template")

    if need_alter_users:
        need_alter_users = need_alter_users.exclude(username=request.user.username)
        create_notification_to_users(need_alter_users, notification_message, url=notification_url, is_important=True,
                                     need_alert=True)
    return api_success()


class TemplateCheckGroupList(APIView):
    def get(self, request, stage_id):
        stage = get_object_or_404(TemplateStage, id=stage_id)

        check_groups = stage.check_groups.order_by('index')
        data = TemplateCheckGroupSerializer(check_groups, many=True).data
        return api_success(data=data)

    def post(self, request, stage_id):
        stage = get_object_or_404(TemplateStage, id=stage_id)
        request_data = deepcopy(request.data)
        previous_check_group_id = request_data.pop('previous_check_group', None)
        next_siblings = []
        request_data['index'] = get_playbook_template_stage_check_group_max_index(template_stage=stage) + 1
        if previous_check_group_id:
            previous_group = get_object_or_404(TemplateCheckGroup, pk=previous_check_group_id)
            if previous_group.template_stage_id == stage_id:
                next_siblings = list(get_playbook_template_check_group_next_siblings(previous_group))
                request_data['index'] = previous_group.index + 1
        request_data['template_stage'] = stage.id
        request_data['playbook_template'] = stage.playbook_template.id
        serializer = TemplateCheckGroupSerializer(data=request_data)
        if serializer.is_valid():
            check_group = serializer.save()
            if next_siblings:
                for sibling in next_siblings:
                    sibling.index = sibling.index + 1
                    sibling.save()
            Log.build_create_object_log(request.user, check_group, stage.playbook_template)
            return api_success(data=serializer.data)
        return api_bad_request(message=str(serializer.errors))


class TemplateCheckGroupDetail(APIView):
    def get(self, request, check_group_id):
        check_group = get_object_or_404(TemplateCheckGroup, id=check_group_id)
        data = TemplateCheckGroupSerializer(check_group).data
        return api_success(data=data)

    def post(self, request, check_group_id):
        check_group = get_object_or_404(TemplateCheckGroup, id=check_group_id)
        serializer = TemplateCheckGroupEditSerializer(check_group, data=request.data)
        if serializer.is_valid():
            check_group = serializer.save()
            Log.build_create_object_log(request.user, check_group, check_group.template_stage.playbook_template)
            return api_success(data=serializer.data)
        return api_bad_request(message=str(serializer.errors))

    def delete(self, request, check_group_id):
        check_group = get_object_or_404(TemplateCheckGroup, id=check_group_id)
        # if check_group.check_items.exists():
        #     return api_bad_request(message='该分类下还有任务，不能删除')
        origin = deepcopy(check_group)
        move_up_playbook_template_check_group_next_siblings(origin)
        check_group.delete()
        Log.build_delete_object_log(request.user, origin, origin.template_stage.playbook_template)
        return api_success(message="删除成功")


class TemplateCheckItemList(APIView):
    def get(self, request, check_group_id):
        check_group = get_object_or_404(TemplateCheckGroup, id=check_group_id)
        check_items = check_group.check_items.order_by('index')
        data = TemplateCheckItemSerializer(check_items, many=True).data
        return api_success(data=data)

    def post(self, request, check_group_id):
        check_group = get_object_or_404(TemplateCheckGroup, id=check_group_id)
        request_data = deepcopy(request.data)
        previous_check_item_id = request_data.pop('previous_check_item', None)
        next_siblings = []
        request_data['index'] = get_playbook_template_check_group_check_item_max_index(check_group=check_group) + 1
        if previous_check_item_id:
            previous_item = get_object_or_404(TemplateCheckItem, pk=previous_check_item_id)
            if previous_item.template_check_group_id == check_group_id:
                next_siblings = list(get_playbook_template_check_item_next_siblings(previous_item))
                request_data['index'] = previous_item.index + 1
        request_data['template_check_group'] = check_group.id
        request_data['playbook_template'] = check_group.template_stage.playbook_template.id
        serializer = TemplateCheckItemSerializer(data=request_data)
        if serializer.is_valid():
            check_item = serializer.save()
            if next_siblings:
                for sibling in next_siblings:
                    sibling.index = sibling.index + 1
                    sibling.save()
            # 检查项的链接
            check_item_links = request_data.get('links', [])
            if check_item_links:
                for link_index, link_data in enumerate(check_item_links):
                    TemplateLinkItem.objects.create(name=link_data['name'], url=link_data['url'],
                                                    index=link_index, template_check_item=check_item)

            playbook_template = check_item.template_check_group.template_stage.playbook_template
            Log.build_create_object_log(request.user, check_item, playbook_template)
            return api_success(data=serializer.data)
        return api_bad_request(message=str(serializer.errors))


class TemplateCheckItemDetail(APIView):
    def get(self, request, check_item_id):
        check_item = get_object_or_404(TemplateCheckItem, id=check_item_id)
        data = TemplateCheckItemSerializer(check_item).data
        return api_success(data=data)

    def post(self, request, check_item_id):
        check_item = get_object_or_404(TemplateCheckItem, pk=check_item_id)
        playbook_template = check_item.template_check_group.template_stage.playbook_template
        origin = deepcopy(check_item)
        origin_check_group = deepcopy(check_item.template_check_group)
        request_data = deepcopy(request.data)
        template_check_group_id = request_data.get("template_check_group")
        if not template_check_group_id:
            request_data['template_check_group'] = check_item.template_check_group.id
            new_check_group = check_item.template_check_group
        else:
            new_check_group = get_object_or_404(TemplateCheckGroup, pk=template_check_group_id)
            if new_check_group.template_stage_id != origin_check_group.template_stage_id:
                return api_bad_request(message="任务组与原任务任务组不在同一个模板阶段内，不能修改")
        request_data['index'] = origin.index
        move_up_list = []
        # 分类变了
        if new_check_group.id != origin_check_group.id:
            request_data['index'] = get_playbook_template_check_group_check_item_max_index(new_check_group) + 1
            move_up_list = list(get_playbook_template_check_item_next_siblings(origin))

        serializer = TemplateCheckItemSerializer(check_item, data=request_data)
        if serializer.is_valid():
            check_item = serializer.save()
            for task in move_up_list:
                task.index = task.index - 1
                task.save()
            check_item.links.all().delete()
            # 检查项的链接
            check_item_links = request_data.get('links', [])
            if check_item_links:
                for link_index, link_data in enumerate(check_item_links):
                    TemplateLinkItem.objects.create(name=link_data['name'], url=link_data['url'],
                                                    index=link_index, template_check_item=check_item)
            Log.build_update_object_log(request.user, check_item, playbook_template)
            return api_success(data=serializer.data)
        return api_bad_request(message=str(serializer.errors))

    def delete(self, request, check_item_id):
        check_item = get_object_or_404(TemplateCheckItem, pk=check_item_id)
        playbook_template = deepcopy(check_item.template_check_group.template_stage.playbook_template)
        origin = deepcopy(check_item)
        move_up_playbook_template_check_item_next_siblings(origin)
        check_item.delete()
        Log.build_delete_object_log(request.user, origin, playbook_template)
        return api_success(message="删除成功")


class TemplateCheckItemLinks(APIView):
    def get(self, request, check_item_id):
        check_item = get_object_or_404(TemplateCheckItem, id=check_item_id)
        data = [{"url": link.url, "name": link.name} for link in check_item.links.order_by('index')]
        return api_success(data=data)

    def post(self, request, check_item_id):
        check_item = get_object_or_404(TemplateCheckItem, pk=check_item_id)
        check_item.links.all().delete()
        # 检查项的链接
        check_item_links = request.data.get('links', [])
        if check_item_links:
            for link_index, link_data in enumerate(check_item_links):
                TemplateLinkItem.objects.create(name=link_data['name'], url=link_data['url'],
                                                index=link_index, template_check_item=check_item)
        data = [{"url": link.url, "name": link.name} for link in check_item.links.order_by('index')]
        return api_success(data=data)


@api_view(['POST'])
def drag_playbook_template_stage_check_group(request):
    origin_id = request.data.get('origin', None)
    target_id = request.data.get('target', None)

    if not all([origin_id, target_id]):
        return api_request_params_required(params=['origin', 'target'])

    origin_catalogue = TemplateCheckGroup.objects.filter(pk=origin_id)
    target_catalogue = TemplateCheckGroup.objects.filter(pk=target_id)
    if not origin_catalogue.exists():
        return api_bad_request(message="拖拽对象不存在")

    if not target_catalogue.exists():
        return api_bad_request(message="目标对象不存在")

    origin_catalogue = origin_catalogue.first()
    target_catalogue = target_catalogue.first()
    origin = deepcopy(origin_catalogue)

    if origin_catalogue.template_stage_id != target_catalogue.template_stage_id:
        return api_bad_request(message="拖拽任务组不属于同一个阶段")

    template_stage = origin_catalogue.template_stage
    playbook_template = template_stage.playbook_template
    # 目标对象的位置 比拖拽对象小      拖拽对象占距目标对象的位置   目标对象(包含)与拖拽对象之间的元素都下移一位 index+1
    target_index = target_catalogue.index
    origin_index = origin_catalogue.index
    if target_index < origin_index:
        middle_siblings = template_stage.check_groups.filter(index__gte=target_index,
                                                             index__lt=origin_index)
        for sibling in middle_siblings:
            sibling.index = sibling.index + 1
            sibling.save()
        origin_catalogue.index = target_index
        origin_catalogue.save()

    # 目标对象的位置 比拖拽对象大      拖拽对象占距目标对象的位置   目标对象(包含)与拖拽对象之间的元素都上移一位 index-1
    if target_index > origin_index:
        middle_siblings = template_stage.check_groups.filter(index__gt=origin_index,
                                                             index__lte=target_index)
        for sibling in middle_siblings:
            sibling.index = sibling.index - 1
            sibling.save()
        origin_catalogue.index = target_index
        origin_catalogue.save()
    Log.build_update_object_log(request.user, origin, origin_catalogue, playbook_template)
    return api_success()


@api_view(['POST'])
def drag_playbook_template_stage_check_group_check_item(request):
    origin_id = request.data.get('origin', None)
    target_id = request.data.get('target', None)

    if not all([origin_id, target_id]):
        return api_request_params_required(params=['origin', 'target'])

    origin_topic = TemplateCheckItem.objects.filter(pk=origin_id)
    target_topic = TemplateCheckItem.objects.filter(pk=target_id)
    if not origin_topic.exists():
        return api_bad_request(message="拖拽对象不存在")

    if not target_topic.exists():
        return api_bad_request(message="目标对象不存在")

    origin_topic = origin_topic.first()
    target_topic = target_topic.first()
    origin = deepcopy(origin_topic)

    if origin_topic.template_check_group_id != target_topic.template_check_group_id:
        return api_bad_request(message="拖拽对象、目标对象不属于同一个分类")
    template_check_group = origin_topic.template_check_group
    playbook_template = template_check_group.template_stage.playbook_template

    # 目标对象的位置 比拖拽对象小      拖拽对象占距目标对象的位置   目标对象(包含)与拖拽对象之间的元素都下移一位 index+1

    target_index = target_topic.index
    origin_index = origin_topic.index
    if target_index < origin_index:
        middle_siblings = template_check_group.check_items.filter(index__gte=target_index,
                                                                  index__lt=origin_index)
        for sibling in middle_siblings:
            sibling.index = sibling.index + 1
            sibling.save()
        origin_topic.index = target_index
        origin_topic.save()

    # 目标对象的位置 比拖拽对象大      拖拽对象占距目标对象的位置   目标对象(包含)与拖拽对象之间的元素都上移一位 index-1
    if target_index > origin_index:
        middle_siblings = template_check_group.check_items.filter(index__gt=origin_index,
                                                                  index__lte=target_index)
        for sibling in middle_siblings:
            sibling.index = sibling.index - 1
            sibling.save()
        origin_topic.index = target_index
        origin_topic.save()
    Log.build_update_object_log(request.user, origin, origin_topic, playbook_template)
    return api_success()


@api_view(['GET'])
def playbook_templates_revision_histories(request):
    revision_histories = TemplateRevisionHistory.objects.order_by('playbook_template__template_type',
                                                                  '-playbook_template__version')
    data = TemplateRevisionHistorySerializer(revision_histories, many=True).data
    return api_success(data=data)


@api_view(['GET'])
def proposal_playbook_templates_revision_histories(request):
    member_type = request.GET.get('member_type', 'product_manager')
    revision_histories = TemplateRevisionHistory.objects.filter(playbook_template__template_type='proposal',
                                                                playbook_template__member_type=member_type).order_by(
        '-playbook_template__version')
    data = TemplateRevisionHistorySerializer(revision_histories, many=True).data
    return api_success(data=data)


@api_view(['GET'])
def project_playbook_templates_revision_histories(request):
    member_type = request.GET.get('member_type', 'manager')
    revision_histories = TemplateRevisionHistory.objects.filter(playbook_template__template_type='project',
                                                                playbook_template__member_type=member_type).order_by(
        '-playbook_template__version')
    data = TemplateRevisionHistorySerializer(revision_histories, many=True).data
    return api_success(data=data)


@api_view(['GET'])
def playbook_template_revision_history(request, template_id):
    revision_histories = TemplateRevisionHistory.objects.filter(playbook_template_id=template_id)
    if not revision_histories.exists():
        return api_bad_request(message="不存在")

    revision_history = revision_histories.first()
    data = TemplateRevisionHistorySerializer(revision_history).data
    return api_success(data=data)


def get_playbook_template_check_group_check_item_max_index(check_group):
    max_index = -1
    topics = check_group.check_items.all().order_by('-index')
    if topics.exists():
        max_index = topics.first().index
    return max_index


def get_playbook_template_stage_check_group_max_index(template_stage):
    max_index = -1
    if template_stage:
        check_groups = template_stage.check_groups.all().order_by('-index')
        if check_groups.exists():
            max_index = check_groups.first().index
    return max_index


def get_current_playbook_template_check_item_or_check_group_next_siblings(current_item):
    current_index = current_item.index
    if hasattr(current_item, 'template_check_group'):
        previous_siblings = current_item.template_check_group.check_items.filter(
            index__gte=current_index).exclude(
            pk=current_item.id)
    else:
        project_playbook_template = playbook_template_check_item.playbook_template_chart
        previous_siblings = project_playbook_template.check_item_check_groups.filter(index__gte=current_index).exclude(
            pk=playbook_template_check_item.id)
    playbook_template_check_items = sorted(previous_siblings, key=lambda check_item: check_item.index, reverse=False)
    return playbook_template_check_items


#
def get_playbook_template_check_item_next_siblings(check_item):
    current_index = check_item.index
    previous_siblings = check_item.template_check_group.check_items.filter(
        index__gte=current_index).exclude(
        pk=check_item.id)
    previous_siblings = sorted(previous_siblings, key=lambda item: item.index, reverse=False)
    return previous_siblings


#
def get_playbook_template_check_group_next_siblings(check_group):
    current_index = check_group.index
    stage = check_group.template_stage
    previous_siblings = stage.check_groups.filter(index__gte=current_index).exclude(pk=check_group.id)
    previous_siblings = sorted(previous_siblings, key=lambda item: item.index, reverse=False)
    return previous_siblings


def get_current_playbook_template_check_item_or_check_group_next_sibling(playbook_template_check_item):
    playbook_template_check_items = get_current_playbook_template_check_item_or_check_group_next_siblings(
        playbook_template_check_item)
    if playbook_template_check_items:
        return playbook_template_check_items[0]
    return None


def get_current_playbook_template_check_item_or_check_group_previous_siblings(current_item):
    current_index = current_item.index
    if hasattr(current_item, 'check_group') and current_item.template_check_group:
        previous_siblings = current_item.template_check_group.check_items.filter(
            index__lte=current_index).exclude(
            pk=current_item.id)
    else:
        project_playbook_template = current_item.playbook_template_chart
        previous_siblings = project_playbook_template.check_item_check_groups.filter(index__lte=current_index).exclude(
            pk=current_item.id)
    playbook_template_check_items = sorted(previous_siblings, key=lambda check_item: check_item.index, reverse=True)
    return playbook_template_check_items


def get_current_playbook_template_check_item_or_check_group_previous_sibling(playbook_template_check_item):
    playbook_template_check_items = get_current_playbook_template_check_item_or_check_group_previous_siblings(
        playbook_template_check_item)
    if playbook_template_check_items:
        return playbook_template_check_items[0]
    return None


def move_up_playbook_template_check_group_next_siblings(check_group):
    next_siblings = get_playbook_template_check_group_next_siblings(check_group)
    for check_item in next_siblings:
        check_item.index = check_item.index - 1
        check_item.save()


def move_up_playbook_template_check_item_next_siblings(check_item):
    next_siblings = get_playbook_template_check_item_next_siblings(check_item)
    for check_item in next_siblings:
        check_item.index = check_item.index - 1
        check_item.save()


@api_view(['POST'])
def skip_stage(request, id):
    stage = get_object_or_404(Stage, id=id)
    stage_project_index = stage.status_index
    # 当前阶段之后的阶段不能跳过
    if stage_project_index > stage.content_object.status_index:
        return api_bad_request('当前阶段之后的阶段不能跳过')

    check_groups = stage.check_groups.filter(completed_at__isnull=True)
    if check_groups.exists():
        for check_group in check_groups:
            origin_check_group = deepcopy(check_group)
            if check_group.check_items.filter(completed_at__isnull=True).exists():
                check_group.check_items.filter(completed_at__isnull=True).update(skipped=True,
                                                                                 completed_at=timezone.now())
            if check_group.check_items.filter(checked=True).exists():
                check_group.checked = True
            else:
                check_group.skipped = True
            check_group.completed_at = timezone.now()
            check_group.save()
            Log.build_update_object_log(request.user, origin_check_group, check_group,
                                        related_object=stage.content_object)
    return api_success()


@api_view(['POST'])
def handle_check_group(request, obj_id, action_type):
    check_group = get_object_or_404(ChecklistItem, id=obj_id)
    stage = check_group.stage
    content_object = stage.content_object
    if stage.is_next_stage:
        return api_bad_request("项目不在当前阶段，不能进行操作")
    # if stage.status_index and stage.status_index > stage.content_object.status_index:
    #     return Response({'result': False, 'message': '项目不在当前阶段，不能进行操作'})
    if check_group.check_items.filter(completed_at__isnull=True).exists():
        return Response({'result': False, 'message': '当前分组中存在未处理检查项，不能进行操作'})
    if (check_group.skipped or check_group.checked) and action_type != 'reset':
        return Response({'result': False, 'message': '当前分组已处理，不能进行{}操作'.format(type)})
    origin = deepcopy(check_group)
    if action_type == 'finish':
        check_group.checked = True
        check_group.completed_at = timezone.now()
        check_group.save()
    elif action_type == 'skip':
        check_group.skipped = True
        check_group.completed_at = timezone.now()
        check_group.save()
    elif action_type == 'reset':
        if check_group.check_items.exists():
            return Response({'result': False, 'message': '当前分组存在子项，不能直接修改其完成状态'})
        elif not check_group.completed_at:
            return Response({'result': False, 'message': '当前分组已处于未处理状态，无需重置'})
        else:
            check_group = check_group.reset_init_data()
    else:
        return Response({'result': False, 'message': 'type参数无效'})
    Log.build_update_object_log(request.user, origin, check_group, related_object=content_object)
    return Response({'result': True})


@api_view(['POST'])
def handle_check_item(request, obj_id, action_type):
    check_item = get_object_or_404(CheckItem, id=obj_id)
    stage = check_item.check_group.stage
    content_object = stage.content_object
    # if stage.is_next_stage:
    #     return api_bad_request("项目不在当前阶段，不能进行操作")
    # if stage.status_index and stage.status_index > stage.content_object.status_index:
    #     return Response({'result': False, 'message': '项目不在当前阶段，不能进行{}操作'.format(type)})
    if (check_item.skipped or check_item.checked) and action_type != 'reset':
        return Response({'result': False, 'message': '当前检查项已处理，不能进行{}操作'.format(type)})
    origin = deepcopy(check_item)
    if action_type == 'finish':
        check_item.checked = True
        check_item.completed_at = timezone.now()
        check_item.save()
    elif action_type == 'skip':
        check_item.skipped = True
        check_item.completed_at = timezone.now()
        check_item.save()
    elif action_type == 'reset':
        if not check_item.completed_at:
            return Response({'result': False, 'message': '当前分组已处于未处理状态，无需重置'})
        else:
            check_item = check_item.reset_init_data()
    else:
        return Response({'result': False, 'message': 'type参数无效'})
    check_group = check_item.check_group
    check_group.rebuild_completed_at()
    Log.build_update_object_log(request.user, origin, check_item, related_object=content_object)
    return Response({'result': True})


class CheckItemDate(APIView):
    def get(self, request, id):
        check_item = get_object_or_404(CheckItem, id=id)
        data = CheckItemDateSerializer(check_item).data
        return api_success(data=data)

    def post(self, request, id):
        check_item = get_object_or_404(CheckItem, id=id)
        if check_item.completed_at:
            return api_bad_request(message="任务已完成 不能需改预计完成时间")
        origin = deepcopy(check_item)
        serializer = CheckItemDateSerializer(check_item, data=request.data)
        if serializer.is_valid():
            check_item = serializer.save()
            if check_item.period == 'weekly':
                if check_item.expected_weekday != origin.expected_weekday:
                    check_item.build_expected_date(to_save=True)
            content_object = check_item.check_group.stage.content_object
            Log.build_update_object_log(request.user, origin, check_item, content_object)
            return api_success(data=serializer.data)
        return api_bad_request(message=str(serializer.errors))


@api_view(['GET'])
def project_playbook_stages(request, id):
    project = get_object_or_404(Project, id=id)
    user_id = request.user.id
    member_type = request.GET.get('member_type', 'manager')
    if member_type == 'product_manager':
        member_ids = [project.manager_id, project.mentor_id, project.product_manager_id]
        if not has_function_perms(request.user, 'view_project_pm_playbook') and user_id not in member_ids:
            return api_permissions_required()
    if member_type == 'manager':
        member_ids = [project.manager_id, project.mentor_id]
        if not has_function_perms(request.user, 'view_project_manager_playbook') and user_id not in member_ids:
            return api_permissions_required()
    stages = project.playbook_stages.filter(member_type=member_type).order_by('index')
    stages_data = StageSerializer(stages, many=True).data
    count = 0
    for stage in project.playbook_stages.filter(member_type=member_type).all():
        if stage.is_previous_stage or stage.is_current_stage:
            stage_count = stage.check_groups.filter(completed_at__isnull=True).count()
            count = count + stage_count
    need_handle_check_group_count = count

    playbook_data = {"project_status": project.stage_display,
                     "need_handle_check_group_count": need_handle_check_group_count}
    playbook_data['stages'] = stages_data
    return api_success(data=playbook_data)


@api_view(['GET'])
def proposal_playbook_stages(request, id):
    project = get_object_or_404(Proposal, id=id)
    member_type = request.GET.get('member_type', 'product_manager')
    if not has_function_perms(request.user, 'manage_proposal_pm_playbook') and request.user.id != project.pm_id:
        return api_permissions_required()
    stages = project.playbook_stages.filter(member_type=member_type).order_by('index')
    stages_data = StageSerializer(stages, many=True).data
    count = 0
    project_status_index = project.status_index
    for stage in project.playbook_stages.all():
        stage_status_index = stage.status_index
        if stage_status_index is not None and stage.status_index <= project_status_index:
            stage_count = stage.check_groups.filter(completed_at__isnull=True).count()
            count = count + stage_count
    need_handle_check_group_count = count
    playbook_data = {"project_status": project.status, "project_status_index": project.status_index,
                     "need_handle_check_group_count": need_handle_check_group_count}

    playbook_data['stages'] = stages_data

    return api_success(data=playbook_data)


@api_view(['GET'])
def data_migrate(request):
    return api_success()
