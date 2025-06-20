from copy import deepcopy
import re
import logging
import json
from datetime import timedelta
from itertools import chain

from django.db.models import Sum, IntegerField, When, Case, Q
from django.shortcuts import get_object_or_404, reverse
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from comments.models import Comment
from farmbase.serializers import UserSimpleSerializer, UserFilterSerializer
from farmbase.utils import get_protocol_host
from farmbase.user_utils import get_user_view_projects, get_user_view_proposals
from files.utils import handle_obj_files
from gearfarm.utils import farm_response
from gearfarm.utils.farm_response import api_success, api_bad_request
from gearfarm.utils.decorators import request_data_fields_required
from farmbase.permissions_utils import has_function_perm
from notifications.utils import create_notification
from logs.models import Log
from workorder.models import CommonWorkOrder, WorkOrderOperationLog
from workorder.serializers import CommonWorkOrderCreateSerializer, CommonWorkOrderDetailSerializer, \
    WorkOrderOperationLogSerializer, CommonWorkOrderDateSerializer, StyleWorkOrderCreateSerializer, \
    GlobalWorkOrderCreateSerializer, ChangesWorkOrderCreateSerializer, BugWorkOrderCreateSerializer, \
    StyleWorkOrderDoneSerializer, GlobalWorkOrderDoneSerializer, ChangesWorkOrderDoneSerializer, \
    CommonWorkOrderDoneSerializer, CommonWorkOrderListSerializer

logger = logging.getLogger()


@api_view(['GET'])
def work_order_sources(request):
    user_id = request.user.id
    '''
    其他
    项目（按照 我进行中的项目，其他人进行中的项目，已关闭的项目排序）
    需求（按照 我进行中的需求，其他人进行中的需求排序）
    '''
    projects = get_user_view_projects(request.user)
    proposals = get_user_view_proposals(request.user, main_status='ongoing')

    projects_data = []
    for p in projects:
        projects_data.append(
            {'id': p.id, 'name': p.name,
             'content_object': {'app_label': 'projects', 'model': 'project', 'object_id': p.id}})

    proposals_data = []
    for p in proposals:
        proposals_data.append(
            {'id': p.id, 'name': p.name,
             'content_object': {'app_label': 'proposals', 'model': 'proposal', 'object_id': p.id}})

    # ongoing_leads = Lead.pending_leads()
    # my_ongoing_leads = ongoing_leads.filter(salesman_id=user_id)
    # other_ongoing_leads = ongoing_leads.difference(my_ongoing_leads)
    # leads_data = []
    # for p in chain(my_ongoing_leads, other_ongoing_leads):
    #     leads_data.append(
    #         {'id': p.id, 'name': p.name,
    #          'content_object': {'app_label': 'clients', 'model': 'lead', 'object_id': p.id}})
    data = {
        "projects": projects_data,
        "proposals": proposals_data,
        # "leads": leads_data,
    }
    return api_success(data)


@api_view(['GET'])
def work_orders_statistics(request):
    params = request.GET
    work_orders = CommonWorkOrderList.get_queryset(request)

    main_status = params.get('main_status', None)
    principal_count = CommonWorkOrder.user_principal_work_orders(request.user, queryset=work_orders).exclude(
        status=4).count()
    submitter_count = CommonWorkOrder.user_submit_work_orders(request.user, queryset=work_orders).exclude(
        status=4).count()

    if main_status == 'ongoing':
        data = {'my_assigned': principal_count, 'my_submitted': submitter_count}
    else:
        ongoing_count = CommonWorkOrder.ongoing_work_orders(queryset=work_orders).count()
        closed_count = CommonWorkOrder.closed_work_orders(queryset=work_orders).count()
        data = {'my_assigned': principal_count, 'my_submitted': submitter_count, 'ongoing': ongoing_count,
                'closed': closed_count}
    return Response(data)


# 筛选项
@api_view(['GET'])
def common_work_orders_users(request):
    my_assigned_work_orders = CommonWorkOrder.user_principal_work_orders(request.user)
    my_created_work_orders = CommonWorkOrder.user_submit_work_orders(request.user)
    ongoing_work_orders = CommonWorkOrder.ongoing_work_orders()
    closed_work_orders = CommonWorkOrder.closed_work_orders()
    ongoing = get_work_orders_filter_data(ongoing_work_orders)
    closed = get_work_orders_filter_data(closed_work_orders)
    my_assigned = get_work_orders_filter_data(my_assigned_work_orders)
    my_created = get_work_orders_filter_data(my_created_work_orders)

    return farm_response.api_success(
        data={'my_assigned': my_assigned, 'my_created': my_created, 'ongoing': ongoing, 'closed': closed})


class CommonWorkOrderList(APIView):
    @staticmethod
    def get_queryset(request):
        params = request.GET
        main_status = params.get('main_status', None)
        current_user_id = request.user.id
        queryset = CommonWorkOrder.objects.all()
        if has_function_perm(request.user, 'view_all_work_orders'):
            pass
        elif has_function_perm(request.user, 'view_my_work_orders'):
            ids = set()
            for obj in queryset:
                for user in obj.participants:
                    if user and user.id == current_user_id:
                        ids.add(obj.id)
                        break
                if obj.content_object:
                    for user in obj.content_object.participants:
                        if user and user.id == current_user_id:
                            ids.add(obj.id)
                            break
            queryset = queryset.filter(id__in=ids)
        else:
            queryset = CommonWorkOrder.objects.none()
            return queryset

        if main_status == 'ongoing':
            queryset = CommonWorkOrder.ongoing_work_orders(queryset)
        elif main_status == 'closed':
            queryset = CommonWorkOrder.closed_work_orders(queryset)

        submitters_str = request.GET.get('submitters', '')
        principals_str = request.GET.get('principals', '')

        filtered_submitter_list = re.sub(r'[;；,，]', ' ', submitters_str).split()
        filtered_principal_list = re.sub(r'[;；,，]', ' ', principals_str).split()
        if filtered_submitter_list:
            queryset = queryset.filter(submitter_id__in=filtered_submitter_list)
        if filtered_principal_list:
            queryset = queryset.filter(principal_id__in=filtered_principal_list)
        work_order_status = params.get('status', '')

        if work_order_status:
            status_list = re.sub(r'[;；,，]', ' ', work_order_status).split()
            queryset = queryset.filter(status__in=status_list)
        work_order_type = params.get('work_order_type', '')
        if work_order_type:
            if work_order_type == 'tpm':
                queryset = queryset.filter(
                    work_order_type__in=['tpm_deployment', 'tpm_bug', 'tpm_evaluation', 'tpm_other'])
            elif work_order_type == 'design':
                queryset = queryset.filter(
                    work_order_type__in=['ui_style', 'ui_global', 'ui_changes', 'ui_walkthrough'])
            else:
                work_order_types = re.sub(r'[;；,，]', ' ', work_order_type).split()
                queryset = queryset.filter(work_order_type__in=work_order_types)
        return queryset

    def get(self, request):
        params = request.GET
        work_orders = self.get_queryset(request)
        order_by = params.get('order_by', '')
        order_dir = params.get('order_dir', '')
        submitters_str = request.GET.get('submitters', '')
        principals_str = request.GET.get('principals', '')
        main_status = params.get('main_status', None)

        if not order_by:
            # 未关闭的
            if main_status == 'ongoing':
                order_by = 'expiration_date'
            elif main_status == 'closed':
                order_by = '-closed_at'
            # 自己提交的  或 自己是负责人的
            elif submitters_str == str(request.user.id) or principals_str == str(request.user.id):
                order_by = 'status', '-closed_at', 'expiration_date'
            else:
                order_by = '-created_at'
        else:
            if order_dir == 'desc':
                order_by = '-' + order_by
        if not isinstance(order_by, str):
            work_orders = work_orders.order_by(*order_by)
        else:
            work_orders = work_orders.order_by(order_by)
        return farm_response.build_pagination_response(request, work_orders, CommonWorkOrderListSerializer)

    def post(self, request):
        request_data = deepcopy(request.data)
        work_type = request_data['work_order_type']
        request_data['submitter'] = request.user.id

        if 'content_object' in request_data and request_data['content_object']:
            content_object_data = request_data.pop('content_object')
            if not isinstance(content_object_data, dict):
                return api_bad_request("content_object参数格式错误")
            if not set(content_object_data.keys()).issuperset({'app_label', 'model', 'object_id'}):
                return api_bad_request("content_object参数格式:{'app_label', 'model', 'object_id'}")
            content_type = ContentType.objects.filter(app_label=content_object_data['app_label'],
                                                      model=content_object_data['model'])
            if not content_type.exists():
                return farm_response.api_not_found("model不存在")
            content_type = content_type.first()
            request_data['content_type'] = content_type.id
            request_data['object_id'] = content_object_data['object_id']

        serializers = get_serializer(work_type)
        serializer = serializers(data=request_data)
        if serializer.is_valid():
            work_order = serializer.save()
            handle_obj_files(work_order, request)
            if work_order.principal_id and work_order.principal_id != request.user.id:
                content = "你有一个【{}】的工单等待处理，优先级️【{}】".format(work_order.content_object_name,
                                                            work_order.get_priority_display())
                url = '/work_orders/detail/?id={}'.format(work_order.id)
                create_notification(work_order.principal, content, url, priority="important")
            build_work_order_operation_log(request, work_order, 'create', origin=None)
            detail_serializer = CommonWorkOrderDetailSerializer(work_order)
            return Response({"result": True, 'data': detail_serializer.data})
        return Response({'result': False, 'message': str(serializer.errors)})


def get_serializer(work_type):
    serializer_dict = {
        'ui_style': StyleWorkOrderCreateSerializer,
        'ui_global': GlobalWorkOrderCreateSerializer,
        'ui_changes': ChangesWorkOrderCreateSerializer,
        'tpm_bug': BugWorkOrderCreateSerializer
    }
    if work_type in serializer_dict:
        return serializer_dict[work_type]
    else:
        return CommonWorkOrderCreateSerializer


def get_done_serializer(work_type):
    serializer_dict = {
        'ui_style': StyleWorkOrderDoneSerializer,
        'ui_global': GlobalWorkOrderDoneSerializer,
        'ui_changes': ChangesWorkOrderDoneSerializer,
    }
    if work_type in serializer_dict:
        return serializer_dict[work_type]
    else:
        return CommonWorkOrderDoneSerializer


class CommonWorkOrderDetail(APIView):
    def get(self, request, id):
        work_order = get_object_or_404(CommonWorkOrder, id=id)
        work_order_data = CommonWorkOrderDetailSerializer(work_order).data
        return Response({"result": True, "data": work_order_data})

    def post(self, request, id):
        work_order = get_object_or_404(CommonWorkOrder, id=id)
        origin = deepcopy(work_order)
        request_data = deepcopy(request.data)
        if 'content_object' in request_data and request_data['content_object']:
            content_object_data = request_data.pop('content_object')
            if not isinstance(content_object_data, dict):
                return api_bad_request("content_object参数格式错误")
            if not set(content_object_data.keys()).issuperset({'app_label', 'model', 'object_id'}):
                return api_bad_request("content_object参数格式:{'app_label', 'model', 'object_id'}")

            content_type = ContentType.objects.filter(app_label=content_object_data['app_label'],
                                                      model=content_object_data['model'])
            if not content_type.exists():
                return farm_response.api_not_found("model不存在")
            content_type = content_type.first()
            request_data['content_type'] = content_type.id
            request_data['object_id'] = content_object_data['object_id']
        work_order_type = request_data.get('work_order_type', work_order.work_order_type)
        serializers = get_serializer(work_type=work_order_type)
        serializer = serializers(work_order, data=request_data)

        if work_order.submitter.id != request.user.id and not request.user.is_superuser:
            return api_bad_request('仅有工单的创建人可以编辑工单')
        if work_order.status >= 3:
            return api_bad_request(message='该工单不处在处理中，当前状态为{},不能进行编辑操作'.format(work_order.get_status_display()))
        if serializer.is_valid():
            work_order = serializer.save()
            handle_obj_files(work_order, request)
            if work_order.principal_id and (origin.principal_id != work_order.principal_id):
                content = "你有一个【{}】的工单等待处理，优先级️【{}】".format(work_order.content_object_name,
                                                            work_order.get_priority_display())
            else:
                content = "{}编辑了【{}】的工单".format(request.user.username, work_order.content_object_name)
            url = get_protocol_host(request) + '/work_orders/detail/?id={}'.format(work_order.id)
            create_notification(work_order.principal, content, url, priority="important")

            WorkOrderOperationLog.build_log(work_order, request.user, log_type='edit')
            Log.build_update_object_log(request.user, origin, work_order, related_object=work_order)
            serializer = CommonWorkOrderDetailSerializer(work_order)
            return Response({"result": True, "data": serializer.data})
        return Response({'result': False, 'message': str(serializer.errors)})


def get_work_order_result_status(origin_status, action):
    actions = CommonWorkOrder.STATUS_ACTIONS_CHOICES[origin_status]
    if action not in actions:
        return False, "当前状态不能进行该操作"
    result_status = CommonWorkOrder.ACTIONS_TO_STATUS[action]
    return True, result_status


@api_view(['POST'])
def change_common_work_order_status(request, work_order_id):
    request_data = deepcopy(request.data)
    work_order = get_object_or_404(CommonWorkOrder, pk=work_order_id)
    '''
    1、仅有工单的创建人可以编辑工单，关闭工单，重启工单
    2、仅有负责人可以确认工单，修改预计完成时间，指派他人，完成工单
    3、超管可以进行所有操作
    '''
    # 判断是否可以进行操作
    if not work_order.principal_id:
        return farm_response.api_bad_request('请先分配负责人')

    action_type = request.data.get('action')
    if action_type in ['begin', 'done']:
        can_do = work_order.principal.id == request.user.id or request.user.is_superuser
        if not can_do:
            return api_bad_request('仅有负责人可以操作')
    elif action_type == ['close', 'reopen']:
        can_do = request.user.id == work_order.submitter_id or request.user.is_superuser
        if not can_do:
            return farm_response.api_bad_request("只有提交人可以操作")

    origin = deepcopy(work_order)
    # 获取result_status
    result, data = get_work_order_result_status(origin.status, action_type)
    if not result:
        return farm_response.api_bad_request(message=data)
    result_status = data

    change_work_order_status(request, work_order, result_status, action_type)

    # 操作记录
    build_work_order_operation_log(request, work_order, action_type, origin=origin)

    # 消息通知
    notification_content, notification_users = get_work_order_status_change_notification_data(work_order, action_type)
    if notification_content:
        notification_url = get_protocol_host(request) + '/work_orders/detail/?id={}'.format(work_order.id)
        for notification_user in notification_users:
            if notification_user and request.user.id != notification_user.id:
                create_notification(notification_user, notification_content, notification_url)
    return api_success()


def build_work_order_operation_log(request, work_order, log_type, origin=None):
    remarks = request.data.get('remarks', '')
    files = request.data.get('files', None)
    origin = origin or deepcopy(work_order)
    log = WorkOrderOperationLog.build_log(work_order, request.user, log_type=log_type,
                                          expected_at=work_order.expected_at,
                                          origin_assignee=origin.principal, new_assignee=work_order.principal)
    if remarks or files:
        comment_obj = Comment.objects.create(author=request.user, content=remarks, content_object=log)
        handle_obj_files(comment_obj, request)
    if log_type == 'create':
        Log.build_create_object_log(request.user, work_order, related_object=work_order)
        if work_order.content_object:
            Log.build_create_object_log(request.user, work_order, related_object=work_order.content_object)
    else:
        Log.build_update_object_log(request.user, origin, work_order, comment=remarks)


def get_work_order_status_change_notification_data(work_order, action_type):
    notification_content = ''
    notification_users = []
    if action_type == 'begin':
        notification_content = "【{}】的工单【{}】已经开始处理️，预计完成时间【{}】".format(work_order.content_object_name,
                                                                      work_order,
                                                                      work_order.expected_at)
        notification_users.append(work_order.submitter)
    elif action_type == 'done':
        notification_content = "【{}】的工单【{}】已经处理完成️".format(work_order.content_object_name, work_order)
        notification_users.append(work_order.submitter)
    elif action_type == 'close':
        notification_content = "【{}】的工单【{}】已经被关闭️".format(work_order.content_object_name, work_order)
        notification_users.append(work_order.principal)
    elif action_type == 'reopen':
        notification_content = "【{}】的工单【{}】需要重新处理️".format(work_order.content_object_name, work_order)
        notification_users.append(work_order.principal)
    return notification_content, notification_users


def change_work_order_status(request, work_order, result_status, action_type):
    '''
    点击完成后，负责人变成提交人
    点击关闭后，负责人变成完成人(如有， 没有完成人的负责人不变)
    点击重启后，负责人变成完成人(如有， 没有完成人的负责人不变)
    '''
    request_data = request.data
    if action_type == 'begin':
        request_data['start_at'] = timezone.now()
        # request_data['start_by'] = request.user.id
        request_data['status'] = result_status
        work_order.start_by = None
        serializer = CommonWorkOrderDateSerializer(work_order, data=request_data)
        serializer.is_valid(raise_exception=True)
        work_order = serializer.save()
        work_order.start_by = request.user
    elif action_type == 'done':
        if work_order.submitter_id:
            request_data['principal'] = work_order.submitter_id
        request_data['done_by'] = request.user.id
        request_data['done_at'] = timezone.now()
        request_data['status'] = result_status
        serializers = get_done_serializer(work_order.work_order_type)
        serializer = serializers(work_order, data=request_data, partial=True)
        serializer.is_valid(raise_exception=True)
        work_order = serializer.save()

    elif action_type == 'close':
        work_order.closed_at = timezone.now()
        work_order.closed_by = request.user
        if work_order.done_by:
            work_order.principal = work_order.done_by
    elif action_type == 'reopen':
        principal_id = request.data.get('principal', '')
        if principal_id:
            principal = get_object_or_404(User, id=principal_id)
            work_order.principal = principal
        elif work_order.done_by:
            work_order.principal = deepcopy(work_order.done_by)
        work_order.closed_by = None
        work_order.closed_at = None
        work_order.done_at = None
        work_order.done_by = None
        work_order.start_at = None
    work_order.status = result_status
    work_order.save()


@api_view(['POST'])
def common_reassign(request, id):
    user = request.user
    work_order = get_object_or_404(CommonWorkOrder, pk=id)
    # 状态未完成 且 负责人可以进行该操作
    can_do = work_order.status < 3 and (work_order.principal_id in [None, user.id] or user.is_superuser)
    if can_do:
        principal_id = request.data['principal']
        principal = get_object_or_404(User, id=principal_id)
        origin = deepcopy(work_order)
        work_order.principal = principal
        work_order.save()
        Log.build_update_object_log(request.user, origin, work_order)
        if work_order.principal_id and (origin.principal_id != work_order.principal_id):
            content = "你有一个【{}】的工单等待处理，优先级️【{}】".format(work_order.content_object_name,
                                                        work_order.get_priority_display())
            url = get_protocol_host(request) + '/work_orders/detail/?id={}'.format(work_order.id)
            create_notification(work_order.principal, content, url, priority="important")

            build_work_order_operation_log(request, work_order, 'assign', origin=origin)

        return api_success()
    return api_bad_request('工单状态未完成 且 负责人可以进行该操作')


@api_view(['POST'])
@request_data_fields_required('expected_at')
def modify_work_order_expected_at(request, work_order_id):
    user = request.user
    work_order = get_object_or_404(CommonWorkOrder, pk=work_order_id)
    can_do = work_order.status < 3 and (work_order.principal_id in [None, user.id] or user.is_superuser)

    if can_do:
        origin = deepcopy(work_order)
        expected_at = request.data.get('expected_at', '')
        work_order.expected_at = expected_at
        work_order.save()
        content = "{}将【{}】的工单【{}】的预计完成时间修改为【{}】".format(request.user.username, work_order.content_object_name,
                                                        work_order, work_order.expected_at)
        url = get_protocol_host(request) + '/work_orders/detail/?id={}'.format(work_order_id)
        create_notification(work_order.submitter, content, url)

        build_work_order_operation_log(request, work_order, 'modify', origin=origin)

        return api_success()
    return api_bad_request('工单状态未完成 且 负责人可以进行该操作')


@api_view(['GET'])
def operation_logs(request, work_order_id):
    instance = get_object_or_404(CommonWorkOrder, pk=work_order_id)
    logs = instance.operation_logs.order_by('created_at')
    data = WorkOrderOperationLogSerializer(logs, many=True).data
    return Response(data)


@api_view(['POST'])
def comments(request, work_order_id):
    instance = get_object_or_404(CommonWorkOrder, pk=work_order_id)
    content = request.data.get('content', None)
    content_text = request.data.get('content_text', None)
    parent_id = request.data.get('parent', None)
    parent = None
    if parent_id:
        parent = Comment.objects.filter(pk=parent_id).first()
        if not parent:
            return farm_response.api_not_found("父级不存在")
        elif getattr(parent.content_object, 'work_order') != instance:
            return farm_response.api_bad_request("父级评论不属于同一个对象")
        elif parent.parent:
            return farm_response.api_bad_request("不支持二级以上评论")
    comment = WorkOrderOperationLog.build_comment_log(instance, request.user, content, content_text=content_text,
                                                      parent=parent)
    handle_obj_files(comment, request)
    return farm_response.api_success()


@api_view(['POST'])
def common_work_order_priority(request, id):
    work_order = get_object_or_404(CommonWorkOrder, id=id)
    origin = deepcopy(work_order)
    work_order.priority = request.data['priority']
    work_order.save()
    Log.build_update_object_log(request.user, origin, work_order)
    return Response({"result": True, 'data': None})


def get_work_orders_filter_data(work_orders):
    submitter_id_list = [user_id for user_id in set(work_orders.values_list('submitter_id', flat=True)) if user_id]
    principal_id_list = [user_id for user_id in set(work_orders.values_list('principal_id', flat=True)) if user_id]
    submitters = User.objects.filter(id__in=submitter_id_list).order_by('-is_active', 'date_joined')
    principals = User.objects.filter(id__in=principal_id_list).order_by('-is_active', 'date_joined')
    submitter_list = UserFilterSerializer(submitters, many=True).data
    principal_list = UserFilterSerializer(principals, many=True).data
    return {'submitters': submitter_list, 'principals': principal_list}
