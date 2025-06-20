import logging
import re
from copy import deepcopy
from datetime import timedelta, datetime

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db import transaction
from django.db.models import Count
from django.db.models import Sum, IntegerField, When, Case, Q
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from clients.models import Lead, LeadOrganization, LeadIndividual, RequirementInfo, ClientInfo
from clients.serializers import LeadSourceSerializer, ClientInfoSerializer
from clients.api import build_lead_source_data, build_client_info_company
from comments.models import Comment

from gearfarm.utils.farm_response import api_success, api_bad_request, build_pagination_response
from gearfarm.utils.decorators import request_params_required, request_data_fields_required
from gearfarm.utils import farm_response
from farmbase.utils import get_protocol_host, get_active_users_by_function_perm
from farmbase.permissions_utils import has_function_perm, has_any_function_perms, func_perm_required
from farmbase.serializers import UserSimpleSerializer, UserFilterSerializer
from farmbase.tasks import crawl_quip_proposals_folders, update_quip_proposal_folder, create_quip_proposal_folder, \
    rebuild_bound_quip_proposals_folders
from farmbase.utils import get_user_by_name, any_true
from files.utils import handle_obj_files
from gearfarm.utils.const import LEAD_STATUS, PROPOSAL_STATUS_FLOW
from logs.models import Log
from notifications.tasks import send_task_auto_update_reminder
from notifications.utils import create_notification_group, create_notification, create_notification_to_users
from playbook.utils import initialize_proposal_playbook
from playbook.tasks import update_proposal_playbook
from proposals.models import Proposal, HandoverReceipt
from proposals.serializers import ProposalSerializer, ProposalDetailSerializer, ProposalsPageSerializer, \
    BusinessOpportunitySerializer, ProposalSimpleSerializer, HandoverReceiptSerializer, HandoverReceiptDetailSerializer, \
    ProposalEditSerializer, ProposalMembersSerializer
from reports.serializers import ReportPageSerializer, ProposalReportListSerializer, ReportTagSerializer
from webphone.models import CallRecord
from webphone.serializers import CallRecordSerializer
from webphone.tasks import download_record_file_to_local_server
from tasks.auto_task_utils import create_proposal_need_report_auto_task

PROPOSAL_STATUS_DICT = Proposal.PROPOSAL_STATUS_DICT


class ProposalList(APIView):
    def get(self, request, format=None):
        proposals = Proposal.objects.all()
        proposal_status = request.GET.get('status', None)
        if proposal_status:
            if proposal_status not in PROPOSAL_STATUS_DICT.keys():
                return Response({"result": False, 'message': "所查询的状态不存在"})
            proposals = proposals.filter(status=PROPOSAL_STATUS_DICT[proposal_status]['status']).order_by('created_at')
        return build_pagination_response(request, proposals, ProposalDetailSerializer)

    def post(self, request, lead_id=None, format=None):
        request_data = deepcopy(request.data)
        # quip_folder的处理开始
        quip_folder_type = request_data.get('quip_folder_type', None)
        quip_folder_id = request_data.get('quip_folder_id', None)
        if quip_folder_type in ['auto', 'no_need']:
            request_data.pop('quip_folder_id', None)
        elif quip_folder_type == 'select':
            if not quip_folder_id:
                return api_bad_request('Quip文件夹必选')
        else:
            return api_bad_request('Quip文件夹类型必选、可选值为auto、no_need、select')

        if quip_folder_id:
            quip_proposals_folders = cache.get('quip_proposals_folders', {})
            if quip_folder_id not in quip_proposals_folders:
                return api_bad_request('所选择的Quip文件夹不存在')
            bound_proposal = Proposal.objects.filter(quip_folder_id=quip_folder_id).first()
            if bound_proposal:
                return api_bad_request("所择Quip文件夹已绑定需求'【{}】{}'".format(bound_proposal.id, bound_proposal.name))
        # quip_folder的处理结束

        request_data['bd'] = request.user.id
        request_data['submitter'] = request.user.id
        lead_id = lead_id or request_data.get('lead', None)
        lead = None
        origin_lead_source = None
        if lead_id:
            lead = get_object_or_404(Lead, pk=lead_id)
            client_info_data = request_data.get('client_info', None)
            if not client_info_data:
                return api_bad_request("客户信息必填")
            if lead.lead_source:
                origin_lead_source = deepcopy(lead.lead_source)
            if Proposal.objects.filter(lead_id=lead_id).exists():
                return Response({"result": False, "message": "该线索已经存在需求"}, status=status.HTTP_400_BAD_REQUEST)
            if lead.status != 'contact':
                return Response({"result": False, "message": "该线索处于{}状态，不能创建需求".format(lead.get_status_display())},
                                status=status.HTTP_400_BAD_REQUEST)
            can_be_converted = lead.can_be_converted_to_proposal
            if not can_be_converted:
                message = "需要满足以下条件之一才能转需求：1. 一次会面打卡、2. 两次电话打卡、3. 已发布线索报告"
                return api_bad_request(message=message)
            request_data['lead'] = lead.id
            if lead.salesman and lead.salesman.is_active:
                request_data['bd'] = lead.salesman.id

        # 事物中创建线索来源
        with transaction.atomic():
            # 创建事务保存点
            save_id = transaction.savepoint()
            try:
                # 线索来源数据处理方法
                lead_source_data = request_data.get('lead_source', None)
                if not lead_source_data:
                    return api_bad_request('来源数据为必填参数')
                # 根据企业/组织/机构名创建企业对象
                lead_source_data = build_lead_source_data(request, lead_source_data)
                request_data['lead_source'] = lead_source_data

                if not lead_source_data:
                    return Response({"result": False, "message": "需求来源数据为必填参数"}, status=status.HTTP_400_BAD_REQUEST)
                if lead and lead.lead_source:
                    lead_source_serializer = LeadSourceSerializer(lead.lead_source, data=lead_source_data)
                else:
                    lead_source_serializer = LeadSourceSerializer(data=lead_source_data)
                if lead_source_serializer.is_valid():
                    lead_source = lead_source_serializer.save()
                    request_data['lead_source'] = lead_source.id
                else:
                    transaction.savepoint_rollback(save_id)
                    return api_bad_request(lead_source_serializer.errors)
            except Exception as e:
                logger = logging.getLogger()
                logger.error(e)
                transaction.savepoint_rollback(save_id)
                raise

            transaction.savepoint_commit(save_id)

        client_info = None
        # 事物中创建客户信息
        with transaction.atomic():
            # 创建事务保存点
            client_info_save_id = transaction.savepoint()
            try:
                # 线索来源数据处理方法
                client_info_data = request_data.get('client_info', None)
                if client_info_data:
                    client_info_data = build_client_info_company(request, client_info_data)
                    serializer = ClientInfoSerializer(data=client_info_data)
                    if not serializer.is_valid():
                        transaction.savepoint_rollback(client_info_save_id)
                        return api_bad_request(serializer.errors)
                    client_info = serializer.save()
            except Exception as e:
                logger = logging.getLogger()
                logger.error(e)
                transaction.savepoint_rollback(client_info_save_id)
                raise
            transaction.savepoint_commit(client_info_save_id)

        serializer = ProposalSerializer(data=request_data)
        if serializer.is_valid():
            proposal = None
            with transaction.atomic():
                save_id_proposal = transaction.savepoint()
                try:
                    proposal = serializer.save()
                    if lead_id:
                        lead.status = LEAD_STATUS['proposal'][0]
                        lead.proposal_created_at = timezone.now()
                        lead.save()
                        if RequirementInfo.objects.filter(lead_id=lead.id).exists():
                            requirement = RequirementInfo.objects.get(lead_id=lead.id)
                            proposal.requirement = requirement
                            proposal.save()

                    handle_obj_files(proposal, request)
                    build_proposal_tags(proposal, request)

                    Log.build_create_object_log(request.user, proposal)
                    if origin_lead_source:
                        Log.build_update_object_log(request.user, origin_lead_source, proposal.lead.lead_source,
                                                    related_object=proposal.lead)

                    initialize_proposal_playbook(proposal)

                    notification_url = get_protocol_host(request) + '/proposals/waiting/'
                    notification_content = '新需求【{} {}】需要认领'.format(proposal.id, proposal.name)
                    create_notification_group(settings.GROUP_NAME_DICT['learning_pm'], notification_content,
                                              notification_url)
                    create_notification_group(settings.GROUP_NAME_DICT['pm'], notification_content, notification_url)
                except Exception as e:
                    transaction.savepoint_rollback(save_id_proposal)
                    logger = logging.getLogger()
                    logger.error(e)
                    return farm_response.api_error(message=str(e))

                if client_info:
                    client_info.proposal = proposal
                    if lead:
                        client_info.lead = lead
                        # 需求创建成功后 客户信息更新到线索
                        lead.company = client_info.company
                        lead.company_name = client_info.company_name
                        lead.address = client_info.address
                        lead.contact_name = client_info.contact_name
                        lead.contact_job = client_info.contact_job
                        lead.phone_number = client_info.phone_number
                        if proposal.rebate in ['0', '1']:
                            lead.has_rebate = True
                            lead.rebate_info = proposal.rebate_info
                        lead.save()
                    client_info.save()

                transaction.savepoint_commit(save_id_proposal)

            # quip_folder的处理开始
            if proposal.quip_folder_id:
                if not settings.DEVELOPMENT:
                    update_quip_proposal_folder.delay(proposal.id)
                else:
                    update_quip_proposal_folder(proposal.id)
            elif quip_folder_type == 'auto':
                if not settings.DEVELOPMENT:
                    create_quip_proposal_folder.delay(proposal.id)
                else:
                    create_quip_proposal_folder(proposal.id)
            # quip_folder的处理结束
            data = ProposalDetailSerializer(proposal, many=False).data
            return api_success(data=data)
        return farm_response.api_bad_request(message=serializer.errors)


# def handle_proposal_organization_individual_name(request, request_data):
#     organization_name = request_data.get('organization')
#     individual_name = request_data.get('individual')
#     if organization_name:
#         organization, created = LeadOrganization.objects.get_or_create(name=organization_name)
#         if created:
#             organization.creator = request.user
#             organization.save()
#         request_data['organization'] = organization.id
#     if individual_name:
#         individual, created = LeadIndividual.objects.get_or_create(name=individual_name)
#         if created:
#             individual.creator = request.user
#             individual.save()
#         request_data['individual'] = individual.id
#
#     return request_data


# 所属行业 应用平台 产品分类
def build_proposal_tags(report, request):
    from reports.models import Industry, ApplicationPlatform
    industries = request.data.get('industries', [])
    application_platforms = request.data.get('application_platforms', [])
    # product_types = request.data.get('product_types', [])
    report.industries.clear()
    report.application_platforms.clear()
    # report.product_types.clear()
    if industries:
        industries = Industry.objects.filter(pk__in=industries)
        report.industries.add(*industries)
    if application_platforms:
        application_platforms = ApplicationPlatform.objects.filter(pk__in=application_platforms)
        report.application_platforms.add(*application_platforms)
    # if product_types:
    #     product_types = ProductType.objects.filter(pk__in=product_types)
    #     report.product_types.add(*product_types)


class ProposalDetail(APIView):
    def get(self, request, id, format=None):
        proposal = get_object_or_404(Proposal, pk=id)
        serializer = ProposalDetailSerializer(proposal)
        return Response({"result": True, 'data': serializer.data})

    @transaction.atomic
    def post(self, request, id, format=None):
        proposal = get_object_or_404(Proposal, pk=id)
        origin = deepcopy(proposal)
        origin_lead_source = None
        if proposal.lead_source:
            origin_lead_source = deepcopy(proposal.lead_source)

        request_data = deepcopy(request.data)

        # quip_folder的处理开始
        quip_folder_type = request_data.get('quip_folder_type', None)
        quip_folder_id = request_data.get('quip_folder_id', None)
        if quip_folder_type in ['auto', 'no_need']:
            request_data.pop('quip_folder_id', None)
        elif quip_folder_type == 'select':
            if not quip_folder_id:
                return api_bad_request('Quip文件夹必选')
        else:
            return api_bad_request('Quip文件夹类型必选、可选值为auto、no_need、select')

        if quip_folder_id:
            quip_proposals_folders = cache.get('quip_proposals_folders', {})
            if quip_folder_id not in quip_proposals_folders:
                return api_bad_request('所选择的Quip文件夹不存在')
            bound_proposal = Proposal.objects.exclude(pk=proposal.id).filter(quip_folder_id=quip_folder_id).exists()
            if bound_proposal:
                return api_bad_request("所择Quip文件夹已绑定需求'【{}】{}'".format(bound_proposal.id, bound_proposal.name))

        savepoint = transaction.savepoint()
        # 线索来源数据处理方法
        lead_source_data = request_data.get('lead_source', None)
        if not lead_source_data:
            return api_bad_request('来源数据为必填参数')
        # 根据企业/组织/机构名创建企业对象
        lead_source_data = build_lead_source_data(request, lead_source_data)
        request_data['lead_source'] = lead_source_data

        if not lead_source_data:
            return Response({"result": False, "message": "需求来源数据为必填参数"}, status=status.HTTP_400_BAD_REQUEST)
        if proposal.lead_source:
            lead_source_serializer = LeadSourceSerializer(proposal.lead_source, data=lead_source_data)
        else:
            lead_source_serializer = LeadSourceSerializer(data=lead_source_data)
        if lead_source_serializer.is_valid():
            lead_source = lead_source_serializer.save()
            request_data['lead_source'] = lead_source.id
        else:
            transaction.savepoint_rollback(savepoint)
            return Response({"result": False, "message": lead_source_serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)

        client_info = ClientInfo.objects.filter(proposal_id=proposal.id).first()
        origin_client_info = deepcopy(client_info) if client_info else None
        # 事物中创建客户信息
        with transaction.atomic():
            # 创建事务保存点
            client_info_save_id = transaction.savepoint()
            try:
                # 线索来源数据处理方法
                client_info_data = request_data.get('client_info', None)
                if client_info_data:
                    client_info_data = build_client_info_company(request, client_info_data)
                    client_info_data['proposal'] = proposal.id
                    client_info_data['lead'] = proposal.lead.id if getattr(proposal, 'lead', None) else None
                    serializer = ClientInfoSerializer(client_info,
                                                      data=client_info_data) if client_info else ClientInfoSerializer(
                        data=client_info_data)
                    if not serializer.is_valid():
                        transaction.savepoint_rollback(client_info_save_id)
                        return api_bad_request(serializer.errors)
                    client_info = serializer.save()

                    if origin_client_info:
                        Log.build_update_object_log(request.user, origin_client_info, client_info,
                                                    related_object=proposal)
            except Exception as e:
                logger = logging.getLogger()
                logger.error(e)
                transaction.savepoint_rollback(client_info_save_id)
                raise
            transaction.savepoint_commit(client_info_save_id)

        serializer = ProposalEditSerializer(proposal, data=request_data)
        if serializer.is_valid():
            try:
                proposal = serializer.save()
                handle_obj_files(proposal, request)
                build_proposal_tags(proposal, request)

                # quip_folder的处理开始
                if proposal.quip_folder_id:
                    if settings.PRODUCTION:
                        update_quip_proposal_folder.delay(proposal.id)
                    else:
                        update_quip_proposal_folder(proposal.id)
                elif quip_folder_type == 'auto':
                    if settings.PRODUCTION:
                        create_quip_proposal_folder.delay(proposal.id)
                    else:
                        create_quip_proposal_folder(proposal.id)
                # quip_folder的处理结束

                Log.build_update_object_log(request.user, origin, proposal)
                if origin_lead_source:
                    Log.build_update_object_log(request.user, origin_lead_source, proposal.lead_source,
                                                related_object=proposal)
                    if proposal.lead and proposal.lead_source_id and proposal.lead.lead_source_id == proposal.lead_source_id:
                        Log.build_update_object_log(request.user, origin_lead_source, proposal.lead_source,
                                                    related_object=proposal.lead)
            except Exception as e:
                transaction.savepoint_rollback(savepoint)
                logger = logging.getLogger()
                logger.error(e)
                return farm_response.api_error(str(e))
            data = ProposalDetailSerializer(proposal).data
            return api_success(data)

        transaction.savepoint_rollback(savepoint)
        return Response({"result": False, "message": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class MyProposalList(APIView):
    def get(self, request, format=None):
        proposals = Proposal.objects.all().filter(pm=request.user)
        serializer = ProposalSerializer(proposals, many=True)
        return Response(serializer.data)


@api_view(['GET'])
def mobile_proposal_list(request, is_mine):
    proposals = Proposal.objects.order_by('-created_at')
    if is_mine:
        proposals = proposals.filter((Q(pm=request.user) | Q(bd=request.user)))
    proposal_status = request.GET.get('proposal_status', None)
    search_value = request.GET.get('search_value', None)
    page = request.GET.get('page', None)
    page_size = request.GET.get('page_size', None)
    if proposal_status == 'ongoing':
        if not has_any_function_perms(request.user, ['view_all_proposals', 'view_ongoing_proposals']):
            return Response({"result": False, "message": "你没有权限查看需求列表"})
        proposals = proposals.filter(status__lt=PROPOSAL_STATUS_DICT['deal']['status'])
    elif proposal_status == 'closed':
        if has_function_perm(request.user, 'view_all_proposals'):
            proposals = proposals.filter(status__gte=PROPOSAL_STATUS_DICT['deal']['status'])
        elif has_function_perm(request.user, 'view_proposals_finished_in_90_days'):
            user_proposals = proposals.filter(pm=request.user)
            proposals_finished_in_90_days = proposals.filter(closed_at__gte=timezone.now() - timedelta(days=90))
            proposals = proposals_finished_in_90_days | user_proposals
        else:
            return Response({"result": False, "message": "你没有权限查看需求列表"})
    else:
        if not has_function_perm(request.user, 'view_all_proposals'):
            return Response({"result": False, "message": "你没有权限查看需求列表"})

    if search_value:
        proposals = proposals.filter(Q(pm__username__icontains=search_value) | \
                                     (Q(name__isnull=False) & Q(name__icontains=search_value)) | (
                                         (Q(name__isnull=True) & Q(description__icontains=search_value))))

    return build_pagination_response(request, proposals, ProposalsPageSerializer)


def get_datatable_data(request_parameters, model_queryset, model_serializer, recordsTotal, recordsFiltered):
    datatable_column_map = {}
    for key, value in request_parameters.items():
        if key.startswith("columns[") and key.endswith("][name]"):
            column_num = re.search(r'[(\d+)]', key).group(0)
            datatable_column_map[column_num] = value
    # 获取多列排序组合
    order_column_list = []
    order_dir_list = []

    for key, value in request_parameters.items():
        if key.startswith("order[") and key.endswith("[column]"):
            order_column_list.append(value)
        if key.startswith("order[") and key.endswith("[dir]"):
            order_dir_list.append(value)
    order_by_zip = zip(order_column_list, order_dir_list)
    # 判断desc asc获取排序列表
    order_by_list = []
    for column, dir in order_by_zip:
        order_by = datatable_column_map.get(column)
        if dir == 'desc':
            order_by = '-' + order_by
        order_by_list.append(order_by)

    # 获得页参数
    if not {'draw', 'length', 'start'}.issubset(request_parameters.keys()):
        return {"result": False, "message": "缺失分页参数"}
    draw = request_parameters.get('draw')
    length = request_parameters.get('length')
    start = request_parameters.get('start')

    # 判断 排序列表中是否存在对未完成任务数量进行排序
    if 'undone_task_num' in order_by_list or '-undone_task_num' in order_by_list:
        model_queryset = model_queryset.annotate(undone_task_num=Sum(
            Case(When(tasks__is_done=False, then=1), default=0, output_field=IntegerField())))
    # 排序
    if order_by_list:
        model_queryset = model_queryset.order_by(*order_by_list)
    # 数据
    model_queryset_page = model_queryset[int(start):(int(start) + int(length))]
    data = model_serializer(model_queryset_page, many=True).data
    return {"result": True, "message": '数据获取成功', 'draw:': int(draw), 'recordsTotal': recordsTotal,
            'recordsFiltered': recordsFiltered, 'data': data}


@api_view(['GET'])
def proposal_filter_data(request):
    if not has_any_function_perms(request.user, ['view_all_proposals', 'view_ongoing_proposals']):
        undone_proposals = []
    else:
        undone_proposals = Proposal.ongoing_proposals()

    if has_function_perm(request.user, 'view_all_proposals'):
        done_proposals = Proposal.closed_proposals()
    elif has_function_perm(request.user, 'view_proposals_finished_in_90_days'):
        done_proposals = Proposal.closed_proposals().select_related('pm', 'bd')
        user_proposals = done_proposals.filter(Q(pm_id=request.user.id) | Q(bd_id=request.user.id))
        proposals_finished_in_90_days = done_proposals.filter(closed_at__gte=timezone.now() - timedelta(days=90))
        done_proposals = proposals_finished_in_90_days | user_proposals
    else:
        done_proposals = []

    ongoing = get_proposals_filter_data(undone_proposals, status='ongoing')
    closed = get_proposals_filter_data(done_proposals, status='closed')
    return api_success(data={'ongoing': ongoing, 'closed': closed})


def get_proposals_filter_data(proposals, status=None):
    if proposals:
        pm_id_list = [pm for pm in set(proposals.values_list('pm_id', flat=True)) if pm]
        bd_id_list = [bd for bd in set(proposals.values_list('bd_id', flat=True)) if bd]
        pms = User.objects.filter(id__in=pm_id_list).order_by('-is_active', 'date_joined')
        bds = User.objects.filter(id__in=bd_id_list).order_by('-is_active', 'date_joined')
        pms_data = UserFilterSerializer(pms, many=True).data
        bds_data = UserFilterSerializer(bds, many=True).data
    else:
        pms_data = []
        bds_data = []
    if status == 'closed':
        status_data = [item for item in PROPOSAL_STATUS_FLOW if item['codename'] in ['deal', 'no_deal']]
    elif status == 'ongoing':
        status_data = [item for item in PROPOSAL_STATUS_FLOW if item['codename'] not in ['deal', 'no_deal']]
    else:
        status_data = [item for item in PROPOSAL_STATUS_FLOW]
    data = {'pms': pms_data, 'bds': bds_data, 'status': status_data}
    return data


@api_view(['GET'])
def ongoing_proposals(request):
    proposals = Proposal.objects.none()
    if has_any_function_perms(request.user, ['view_all_proposals', 'view_ongoing_proposals']):
        proposals = Proposal.ongoing_proposals().select_related('pm', 'bd')
    result_response = get_proposal_table_data_result_response(request, proposals, proposal_status='ongoing')
    return result_response


@api_view(['GET'])
def closed_proposals(request):
    proposals = Proposal.objects.none()
    if has_function_perm(request.user, 'view_all_proposals'):
        proposals = Proposal.closed_proposals().select_related('pm', 'bd')
    elif has_function_perm(request.user, 'view_proposals_finished_in_90_days'):
        proposals = Proposal.closed_proposals().select_related('pm', 'bd')
        user_proposals = proposals.filter(Q(pm_id=request.user.id) | Q(bd_id=request.user.id))
        proposals_finished_in_90_days = proposals.filter(closed_at__gte=timezone.now() - timedelta(days=90))
        proposals = proposals_finished_in_90_days | user_proposals
    result_response = get_proposal_table_data_result_response(request, proposals, proposal_status='closed')
    return result_response


@api_view(['GET'])
def my_ongoing_proposals(request):
    request_user_id = request.user.id
    proposals = Proposal.ongoing_proposals().filter(Q(pm_id=request_user_id) | Q(bd_id=request_user_id)).select_related(
        'pm', 'bd')
    result_response = get_proposal_table_data_result_response(request, proposals, proposal_status='ongoing')
    return result_response


@api_view(['GET'])
def my_closed_proposals(request):
    request_user_id = request.user.id
    proposals = Proposal.closed_proposals().filter(Q(pm_id=request_user_id) | Q(bd_id=request_user_id)).select_related(
        'pm', 'bd')
    result_response = get_proposal_table_data_result_response(request, proposals, proposal_status='closed')
    return result_response


def get_proposal_table_data_result_response(request, proposals, proposal_status=None):
    params = request.GET
    pm_list = re.sub(r'[;；,，]', ' ', params.get('pms', '')).split()
    bd_list = re.sub(r'[;；,，]', ' ', params.get('bds', '')).split()
    status_list = re.sub(r'[;；,，]', ' ', params.get('status', '')).split()
    search_value = request.GET.get('search_value', None)
    if pm_list:
        proposals = proposals.filter(pm_id__in=pm_list)
    if bd_list:
        proposals = proposals.filter(bd_id__in=bd_list)
    if status_list:
        proposals = proposals.filter(status__in=status_list)
    # 对关键字模糊检索
    if search_value:
        # id的查询
        if str.isdigit(search_value) and proposals.filter(pk=search_value).exists():
            proposals = proposals.filter(pk=search_value)
        else:
            proposals = proposals.filter(
                Q(pm__username__icontains=search_value) | Q(bd__username__icontains=search_value) |
                (Q(name__isnull=False) & Q(name__icontains=search_value)) | (
                    (Q(name__isnull=True) & Q(description__icontains=search_value))))
    order_by = params.get('order_by', '')
    order_dir = params.get('order_dir', '')
    if not order_by:
        order_by = 'closed_at' if proposal_status == 'closed' else 'created_at'
        order_dir = order_dir or 'desc'
    if order_dir == 'desc':
        order_by = '-' + order_by
    # 判断 排序列表中是否存在对未完成任务数量进行排序
    if 'undone_tasks' in order_by:
        proposals = sorted(proposals, key=lambda x: len(x.undone_tasks()), reverse=order_dir == 'desc')
        # proposals = proposals.annotate(undone_task_num=Sum(
        #     Case(When(tasks__is_done=False, then=1), default=0, output_field=IntegerField())))
        # order_by = order_by.replace('undone_tasks', 'undone_task_num')
    else:
        proposals = proposals.order_by(order_by)
    return build_pagination_response(request, proposals, ProposalsPageSerializer)


@api_view(['GET'])
def proposal_reports(request, proposal_id):
    proposal = get_object_or_404(Proposal, pk=proposal_id)
    reports = proposal.reports.order_by('-created_at')
    if request.GET.get('is_public', None) in ['True', True, 'true', 1, '1']:
        reports = proposal.reports.filter(is_public=True).order_by('-published_at')
    if request.GET.get('is_public', None) in ['False', False, 'false', 0, '0']:
        reports = proposal.reports.filter(is_public=False).order_by('-created_at')
    count = reports.count()
    serializer = ProposalReportListSerializer(reports, many=True)
    return Response({"result": True, 'count': count, 'data': serializer.data})


@api_view(['GET'])
def proposal_latest_report_tags(request, proposal_id):
    proposal = get_object_or_404(Proposal, pk=proposal_id)
    last_reports = proposal.reports.filter(is_public=True).order_by('-published_at')
    if last_reports.exists():
        serializer = ReportTagSerializer(last_reports.first())
        return Response({"result": True, 'data': serializer.data})
    return Response({"result": True, 'data': None, "message": "需求不存在报告"})


@api_view(['GET'])
def proposal_latest_report(request, proposal_id):
    proposal = get_object_or_404(Proposal, pk=proposal_id)
    last_report = proposal.reports.filter(is_public=True).order_by('-published_at').first()
    if last_report:
        serializer = ReportPageSerializer(last_report)
        return api_success(serializer.data)
    return api_bad_request("需求不存在报告")


@api_view(['POST'])
@request_data_fields_required('reliability')
def proposal_reliability(request, id):
    proposal = get_object_or_404(Proposal, id=id)
    origin = deepcopy(proposal)
    proposal.reliability = request.data['reliability']
    proposal.save()
    if proposal.reliability == 'major':
        request_data = deepcopy(request.data)
        request_data['biz_opp_created_at'] = origin.biz_opp_created_at if origin.biz_opp_created_at else timezone.now()
        serializer = BusinessOpportunitySerializer(proposal, data=request_data)
        if serializer.is_valid():
            proposal = serializer.save()
        else:
            return api_bad_request(serializer.errors)
        if origin.biz_opp_created_at:
            Log.build_update_object_log(request.user, origin, proposal, related_object=proposal, comment='修改商机信息')
        else:
            Log.build_update_object_log(request.user, origin, proposal, related_object=proposal, comment='创建商机信息')
    Log.build_update_object_log(request.user, origin, proposal)
    data = ProposalSerializer(proposal).data
    return Response({"result": True, 'data': data})


class ProposalMemberList(APIView):
    def get(self, request, proposal_id, format=None):
        project = get_object_or_404(Proposal, pk=proposal_id)
        serializer = ProposalMembersSerializer(project)
        return api_success(data=serializer.data)

    def post(self, request, proposal_id, format=None):
        project = get_object_or_404(Proposal, pk=proposal_id)
        origin = deepcopy(project)
        serializer = ProposalMembersSerializer(project, data=request.data)
        if serializer.is_valid():
            project = serializer.save()
            Log.build_update_object_log(operator=request.user, original=origin, updated=project)
            return api_success(data=serializer.data)
        return api_bad_request(message=serializer.errors)


@api_view(['POST'])
def reassign(request, id):
    proposal = get_object_or_404(Proposal, pk=id)
    new_pm_id = request.data['new_pm_id']
    new_pm = get_object_or_404(User, id=new_pm_id)
    if new_pm.id == proposal.pm_id:
        return api_success()

    origin = deepcopy(proposal)
    proposal.pm = new_pm
    proposal.save()
    Log.build_update_object_log(request.user, origin, proposal)
    # 需求重新指定产品经理，通知原产品经理、新产品经理
    notification_url = get_protocol_host(request) + '/proposals/detail/?proposalId={}'.format(proposal.id)
    if origin.pm_id and origin.pm_id != request.user.id and origin.pm.is_active:
        content = '{}把你的需求【{} {}】分配给了{}'.format(request.user.username, proposal.id, proposal.name, proposal.pm.username)
        create_notification(origin.pm, content)
    if proposal.pm_id != request.user.id:
        content = '{}把需求【{} {}】分配给了你'.format(request.user.username, proposal.id, proposal.name)
        create_notification(proposal.pm, content, notification_url)

    data = ProposalSerializer(proposal).data
    return api_success(data=data)


@api_view(['POST'])
@func_perm_required('proposals.be_proposal_product_manager')
def assign(request, id):
    proposal = get_object_or_404(Proposal, id=id)
    origin = deepcopy(proposal)
    if not proposal.status == PROPOSAL_STATUS_DICT['pending']['status']:
        return Response({'result': False, "message": "该需求已经被认领"})

    proposal.pm = request.user
    proposal.assigned_at = timezone.now()
    proposal.status = PROPOSAL_STATUS_DICT['contact']['status']
    proposal.save()

    if proposal.bd_id and request.user.id != proposal.bd_id:
        notification_url = get_protocol_host(request) + '/proposals/detail/?proposalId={}'.format(proposal.id)
        notification_content = '{} 认领了你的需求【{} {}】'.format(request.user.username, proposal.id, proposal.name)
        create_notification(proposal.bd, notification_content, notification_url)

    Log.build_update_object_log(request.user, origin, proposal)
    data = ProposalSerializer(proposal).data
    return api_success(data=data)


@api_view(['POST'])
def proposal_name(request, id):
    proposal = get_object_or_404(Proposal, id=id)
    origin = deepcopy(proposal)
    proposal.name = request.data['name']
    proposal.save()
    Log.build_update_object_log(request.user, origin, proposal)
    data = ProposalSerializer(proposal).data
    return Response({'result': True, 'data': data})


@api_view(['POST'])
def contact(request, id):
    proposal = get_object_or_404(Proposal, id=id)
    origin = deepcopy(proposal)
    if proposal.status != PROPOSAL_STATUS_DICT['contact']['status']:
        return Response({'result': False, 'message': '该需求不处在等待沟通状态，当前状态为{},不能进行联系打卡操作'.format(
            proposal.get_status_display())})
    proposal.contact_at = timezone.now()
    proposal.status = PROPOSAL_STATUS_DICT['ongoing']['status']
    proposal.save()
    Log.build_update_object_log(request.user, origin, proposal)
    data = ProposalSerializer(proposal).data
    return Response({'result': True, 'message': '', 'data': data})


@api_view(['POST'])
def report_request(request, id):
    proposal = get_object_or_404(Proposal, id=id)
    proposal_pm = proposal.pm
    if not proposal_pm:
        return api_bad_request('当前需求没有产品经理')
    expected_at = timezone.now() + timedelta(days=1)
    comment = request.data.get('comment')
    if request.data.get('expected_at'):
        try:
            expected_at = datetime.strptime(request.data.get('expected_at'), '%Y-%m-%d')
        except Exception as e:
            return Response({'result': False, 'message': str(e)})
    if proposal_pm:
        # 给PM创建TODO
        create_proposal_need_report_auto_task(proposal, expected_at)
        send_task_auto_update_reminder.delay('proposal', proposal.id)
        # 创建评论
        content = "{}需要一份反馈报告，期望完成时间:{}".format(request.user.username, expected_at.strftime('%Y-%m-%d'))
        content = content + (' 备注:{}'.format(comment) if comment else '')
        Comment.objects.create(author=request.user, content=content, content_object=proposal)
    return Response({'result': True, 'message': ''})


@api_view(['POST'])
def nodeal(request, id):
    proposal = get_object_or_404(Proposal, id=id)
    if proposal.status >= PROPOSAL_STATUS_DICT['deal']['status']:
        return Response({'result': False, 'message': '该需求当前状态为{}，不能进行关闭操作'.format(
            proposal.get_status_display())})
    origin = deepcopy(proposal)
    closed_reason_remarks = request.data.get('closed_reason_remarks', None)
    closed_reason_text = request.data.get('closed_reason_text', None)
    proposal.closed_reason_text = closed_reason_text
    proposal.closed_reason_remarks = closed_reason_remarks
    proposal.closed_at = timezone.now()
    proposal.status = PROPOSAL_STATUS_DICT['no_deal']['status']
    proposal.save()
    for report in proposal.reports.all():
        report.expire_now()
    if proposal.lead:
        lead = proposal.lead
        lead.status = LEAD_STATUS['no_deal'][0]
        lead.proposal_closed_at = timezone.now()
        lead.save()
        for report in lead.reports.all():
            report.expire_now()

    comment = '关闭理由：' + (closed_reason_text or '') + '; ' + (closed_reason_remarks or '')
    Log.build_update_object_log(request.user, origin, proposal, comment=comment)
    data = ProposalSerializer(proposal).data
    return Response({'result': True, 'message': '', 'data': data})


@api_view(['POST'])
def open_proposal(request, id):
    proposal = get_object_or_404(Proposal, id=id)
    if request.user.id not in [proposal.bd_id, proposal.pm_id] and not request.user.is_superuser:
        return Response({'result': False, 'message': '你没有权限恢复当前需求到进行中, 请联系需求的产品经理、BD或管理员'},
                        status=status.HTTP_403_FORBIDDEN)
    if proposal.status != PROPOSAL_STATUS_DICT['no_deal']['status']:
        return Response({'result': False, 'message': '该需求当前状态为{}，不能恢复为进行中'.format(
            proposal.get_status_display())})
    origin = deepcopy(proposal)
    proposal.closed_reason_text = None
    proposal.closed_at = None
    proposal.closed_reason_remarks = None
    proposal.status = PROPOSAL_STATUS_DICT['ongoing']['status']
    if proposal.biz_opp_created_at:
        proposal.budget = None
        proposal.decision_time = None
        proposal.decision_makers = None
        proposal.biz_opp_created_at = None
    if HandoverReceipt.objects.filter(proposal_id=proposal.id).exists():
        HandoverReceipt.objects.filter(proposal_id=proposal.id).delete()
    proposal.save()
    update_proposal_playbook(proposal, reset_current_status=True)
    if proposal.lead and proposal.lead.status == LEAD_STATUS['no_deal'][0]:
        proposal.lead.status = LEAD_STATUS['proposal'][0]
        proposal.lead.proposal_closed_at = None
        proposal.lead.save()

    notification_users = set()
    notification_url = get_protocol_host(request) + '/proposals/detail/?proposalId={}'.format(proposal.id)
    notification_content = "{}将未成单需求【{} {}】修改为进行中状态".format(request.user.username, proposal.id, proposal.name)
    for member in [proposal.bd, proposal.pm]:
        if member and member.is_active and member.id != request.user.id:
            notification_users.add(member)
    create_notification_to_users(notification_users, notification_content, notification_url)

    Log.build_update_object_log(request.user, origin, proposal)
    data = ProposalSerializer(proposal).data
    return Response({'result': True, 'message': '', 'data': data})


def get_business_opportunity_datatables_data(request, proposals):
    recordsTotal = proposals.count()
    search_value = request.GET.get('search[value]', None)
    # 对关键字模糊检索
    if search_value:
        proposals = proposals.filter(
            Q(pm__username__icontains=search_value) | Q(bd__username__icontains=search_value) |
            (Q(name__isnull=False) & Q(name__icontains=search_value)) | (
                (Q(name__isnull=True) & Q(description__icontains=search_value))))
    recordsFiltered = proposals.count()
    result = get_datatable_data(request.GET, proposals, BusinessOpportunitySerializer, recordsTotal, recordsFiltered)
    return result


class BusinessOpportunityList(APIView):
    def get(self, request, proposal_id=None):
        if proposal_id:
            proposal = get_object_or_404(Proposal, pk=proposal_id)
            data = None
            if proposal.biz_opp_created_at:
                serializer = BusinessOpportunitySerializer(proposal)
                data = serializer.data
            return Response({"result": True, 'data': data})

        biz_opp_status = PROPOSAL_STATUS_DICT['biz_opp']['status']
        proposals = Proposal.objects.filter(status=biz_opp_status)

        params = request.GET
        search_value = params.get('search_value', None)
        order_by = params.get('order_by', 'biz_opp_created_at')
        order_dir = params.get('order_dir', 'desc')
        page = params.get('page', None)
        page_size = params.get('page_size', None)

        # 对关键字模糊检索
        if search_value:
            proposals = proposals.filter(
                Q(pm__username__icontains=search_value) | Q(bd__username__icontains=search_value) |
                (Q(name__isnull=False) & Q(name__icontains=search_value)) | (
                    (Q(name__isnull=True) & Q(description__icontains=search_value))))

        if not order_by:
            order_by = 'biz_opp_created_at'
            order_dir = 'desc'
        if order_dir == 'desc':
            order_by = '-' + order_by
        # 判断 排序列表中是否存在对未完成任务数量进行排序
        if 'undone_tasks' in order_by:
            proposals = proposals.annotate(undone_task_num=Sum(
                Case(When(tasks__is_done=False, then=1), default=0, output_field=IntegerField())))
            order_by = order_by.replace('undone_tasks', 'undone_task_num')
        proposals = proposals.order_by(order_by)
        return build_pagination_response(request, proposals, ProposalsPageSerializer)

    def post(self, request, proposal_id=None):
        proposal_id = proposal_id if proposal_id else request.data.get('proposal_id', None)
        if not proposal_id:
            return Response({"result": False, "message": "缺少参数proposal_id"})
        proposal = get_object_or_404(Proposal, pk=proposal_id)
        ongoing_status = PROPOSAL_STATUS_DICT['ongoing']['status']
        biz_opp_status = PROPOSAL_STATUS_DICT['biz_opp']['status']
        if proposal.status not in [ongoing_status, biz_opp_status]:
            return Response({'result': False, 'message': '当前状态为{},不能进行填写商机信息操作'.format(
                proposal.get_status_display())})
        origin = deepcopy(proposal)
        request_data = deepcopy(request.data)
        request_data['biz_opp_created_at'] = origin.biz_opp_created_at if origin.biz_opp_created_at else timezone.now()
        serializer = BusinessOpportunitySerializer(proposal, data=request_data)
        if serializer.is_valid():
            proposal = serializer.save()
            if proposal.status == ongoing_status:
                proposal.status = biz_opp_status
                proposal.save()

            if origin.biz_opp_created_at:
                Log.build_update_object_log(request.user, origin, proposal, related_object=proposal, comment='修改商机信息')
            else:
                Log.build_update_object_log(request.user, origin, proposal, related_object=proposal, comment='创建商机信息')

            return Response({"result": True, "data": serializer.data})
        return Response({"result": False, "message": serializer.errors})


@api_view(['GET', ])
def get_proposal_source_data(request):
    source_data = Proposal.SOURCE_CHOICES
    source_data_list = []
    for value, description in source_data:
        source = {'value': value, 'description': description}
        source_data_list.append(source)
    return Response({"result": True, "data": source_data_list})


class ProposalCallRecordList(APIView):
    def get(self, request, proposal_id):
        proposal = get_object_or_404(Proposal, pk=proposal_id)
        call_records = proposal.call_records.all()
        record_flag = request.GET.get('record_flag', 0)
        if record_flag and int(record_flag) == 1:
            call_records = call_records.filter(record_flag=1)
        call_records = call_records.order_by('-record_date', '-created_at')
        data = CallRecordSerializer(call_records, many=True).data
        return Response({"result": True, "data": data})

    def post(self, request, proposal_id):
        proposal = get_object_or_404(Proposal, pk=proposal_id)

        request.data['proposal'] = proposal.id
        request.data['submitter'] = request.user.id
        request.data['record_date'] = request.data['record_date'] if request.data.get(
            'record_date') else timezone.now().date()
        request.data['source'] = 1
        request.data['is_active'] = True

        record_file = None
        if 'file' in request.data:
            record_file = request.data.get('file')
            if not record_file.name.endswith(('.mp3', '.wav', '.m4a')):
                return Response({"result": False, "message": "只支持mp3、wav、m4a格式"})
            request.data['file_size'] = str(record_file.size)
            request.data['file_suffix'] = record_file.name.rsplit('.', 1)[1]
        if record_file and not request.data.get('filename', ''):
            request.data['filename'] = re.sub(r'[~#^/=$@%&?？]', ' ', record_file.name)

        serializer = CallRecordSerializer(data=request.data)
        if serializer.is_valid():
            call_record = serializer.save()
            download_record_file_to_local_server(call_record)
            Log.build_create_object_log(request.user, call_record, call_record.proposal)
            Log.build_create_object_log(request.user, call_record, call_record)
            return Response({"result": True, 'data': serializer.data})
        return Response({"result": False, "message": str(serializer.errors)})


class ProposalCallRecordDetail(APIView):
    def get(self, request, call_record_id):
        call_record = get_object_or_404(CallRecord, pk=call_record_id)
        serializer = CallRecordSerializer(call_record)
        return Response({"result": True, 'data': serializer.data})


@api_view(['GET', ])
def my_submitted_proposals(request):
    submitted_proposals = request.user.submitted_proposals.order_by('-created_at', 'source').all()
    data = ProposalSimpleSerializer(submitted_proposals, many=True).data

    first_day = datetime.today().replace(day=1, hour=0, minute=0, second=0)
    six_month = first_day - relativedelta(months=5)
    proposal_history = request.user.submitted_proposals.filter(created_at__gte=six_month).annotate(
        month=TruncMonth('created_at')).values('month').annotate(c=Count('id')).values('month', 'c')
    trend_months = []
    trend_counts = []
    for i in range(-1, 5):
        current = (six_month.month + i) % 12 + 1
        trend_months.append("%d月" % (current))
        c = 0
        for h in proposal_history:
            if h['month'].month == current:
                c = h['c']
                break
        trend_counts.append(c)
    statistic_data = {}

    for month, count in zip(trend_months, trend_counts):
        statistic_data[month] = count

    return Response({"result": True, 'statistic_data': statistic_data, "data": data, })


class HandoverReceiptList(APIView):
    def get(self, request, proposal_id):
        get_object_or_404(Proposal, pk=proposal_id)
        handover_receipt = get_object_or_404(HandoverReceipt, proposal_id=proposal_id)
        serializer = HandoverReceiptDetailSerializer(handover_receipt)
        return Response({"result": True, 'data': serializer.data})

    def post(self, request, proposal_id):
        proposal = get_object_or_404(Proposal, pk=proposal_id)
        pending_status = PROPOSAL_STATUS_DICT['pending']['status']
        contract_status = PROPOSAL_STATUS_DICT['contract']['status']
        if not pending_status < proposal.status < contract_status:
            return Response({'result': False, 'message': '需求当前状态为{},不能进行创建交付清单操作'.format(
                proposal.get_status_display())})
        if HandoverReceipt.objects.filter(proposal_id=proposal_id).exists():
            return Response({"result": False, "message": "需求已经创建交付清单, 不能重复创建"})
        request_data = deepcopy(request.data)

        has_referral_fee = request_data.get('has_referral_fee')
        if has_referral_fee in [True, '1', 1, 'true']:
            if 'referral_fee_rebate' not in request_data:
                return Response({"result": False, "message": "有介绍费时, 介绍费返点为必填"})
            request_data['has_referral_fee'] = True
        else:
            request_data.pop('referral_fee_rebate', None)
            request_data['has_referral_fee'] = False

        need_op_service = request_data.get('need_op_service')
        if need_op_service in [True, '1', 1, 'true']:
            if not {'op_period', 'op_service_charge', 'op_payment_mode', 'op_invoice_mode'}.issubset(
                    request_data.keys()):
                return Response({"result": False, "message": "有运维服务时, 运维周期、运维服务费、运维开票类型、运维开票方式为必填"})
            request_data['need_op_service'] = True
        else:
            request_data['need_op_service'] = False
            for op_data in {'op_period', 'op_service_charge', 'op_payment_mode', 'op_invoice_mode'}:
                request_data.pop(op_data, None)

        has_marketing_plan = request_data.get('has_marketing_plan')
        if has_marketing_plan in [True, '1', 1, 'true']:
            if 'marketing_plan_info' not in request_data.keys():
                return Response({"result": False, "message": "有市场安排时, 市场安排信息为必填"})
            request_data['has_marketing_plan'] = True
        else:
            request_data['has_marketing_plan'] = False
            request_data.pop('marketing_plan_info', None)

        request_data['proposal'] = proposal.id
        request_data['submitter'] = request.user.id
        serializer = HandoverReceiptSerializer(data=request_data)
        if serializer.is_valid():
            handover_receipt = serializer.save()
            proposal.status = contract_status
            proposal.save()
            Log.build_create_object_log(request.user, handover_receipt, proposal)
            create_notification_of_reassign_project_manager_for_proposal(request, proposal)
            return api_success(data=serializer.data)
        return api_bad_request(message=serializer.errors)

    def put(self, request, proposal_id):
        get_object_or_404(Proposal, pk=proposal_id)
        proposal = get_object_or_404(Proposal, pk=proposal_id)
        handover_receipt = get_object_or_404(HandoverReceipt, proposal_id=proposal_id)
        origin = deepcopy(handover_receipt)
        request_data = deepcopy(request.data)

        has_referral_fee = request_data.get('has_referral_fee')
        if has_referral_fee in [True, '1', 1, 'true']:
            request_data['has_referral_fee'] = True
            if 'referral_fee_rebate' not in request_data:
                return Response({"result": False, "message": "有介绍费时, 介绍费返点为必填"})
        else:
            request_data['has_referral_fee'] = False
            request_data['referral_fee_rebate'] = None

        need_op_service = request_data.get('need_op_service')
        if need_op_service in [True, '1', 1, 'true']:
            request_data['need_op_service'] = True
            if not {'op_period', 'op_service_charge', 'op_payment_mode', 'op_invoice_mode'}.issubset(
                    request_data.keys()):
                return Response({"result": False, "message": "有运维服务时, 运维周期、运维服务费、运维开票类型、运维开票方式为必填"})
        else:
            request_data['need_op_service'] = False
            for op_data in {'op_period', 'op_service_charge', 'op_payment_mode', 'op_invoice_mode'}:
                request_data[op_data] = None

        has_marketing_plan = request_data.get('has_marketing_plan')
        if has_marketing_plan in [True, '1', 1, 'true']:
            if 'marketing_plan_info' not in request_data.keys():
                return Response({"result": False, "message": "有市场安排时, 市场安排信息为必填"})
            request_data['has_marketing_plan'] = True
        else:
            request_data['has_marketing_plan'] = False
            request_data.pop('marketing_plan_info', None)

        serializer = HandoverReceiptDetailSerializer(handover_receipt, data=request_data)
        if serializer.is_valid():
            handover_receipt = serializer.save()
            Log.build_update_object_log(request.user, origin, handover_receipt, proposal)
            return Response({"result": True, 'data': serializer.data})
        return Response({"result": False, "message": serializer.errors})


def create_notification_of_reassign_project_manager_for_proposal(request, proposal):
    users = get_active_users_by_function_perm('reassign_project_manager_for_proposal')
    content = "需求【{} {}】已进入成单交接阶段，请分配一名项目经理创建项目️".format(proposal.id, proposal.name)
    url = get_protocol_host(request) + '/proposals/detail/?proposalId={}'.format(proposal.id)

    create_notification_to_users(users, content, url=url, is_important=True)


@api_view(['GET', ])
def quip_folders(request):
    folders_dict = cache.get('quip_proposals_folders', None)
    bound_quip_folders = cache.get("bound_quip_proposals_folders", set())
    ignore_quip_folders = cache.get('ignore_quip_folders', set())
    if folders_dict is None:
        folders_dict = crawl_quip_proposals_folders()
    else:
        crawl_quip_proposals_folders.delay()

    if not bound_quip_folders:
        bound_quip_folders = rebuild_bound_quip_proposals_folders()
    else:
        rebuild_bound_quip_proposals_folders.delay()
    folders = []
    for folder_key in folders_dict:
        folder_data = folders_dict[folder_key]
        title = folder_data["folder"].get('title', None)
        title = title.lower().strip() if title else title
        if title and ('archive' == title or '完成项目归档' in title or '项目完成归档' in title):
            ignore_quip_folders.add(folder_key)
            continue
        if folder_key not in bound_quip_folders:
            folders.append(deepcopy(folder_data["folder"]))
    cache.set('ignore_quip_folders', ignore_quip_folders, None)
    folder_list = sorted(folders, key=lambda x: x['created_usec'], reverse=True)
    return api_success(data=folder_list[:18])
