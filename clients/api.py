import re
import json
import logging
from itertools import chain
from copy import deepcopy
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time
import os
from pprint import pprint
from wsgiref.util import FileWrapper

from django.shortcuts import get_object_or_404

from django.db import transaction
from django.db.models import Sum, IntegerField, When, Case, Q
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import escape_uri_path
from django.utils.decorators import method_decorator
from django.conf import settings
from django.core.cache import cache
from django.core.files import File
from django.http import Http404, HttpResponse, FileResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.contrib.auth.models import User
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import api_view
from rest_framework import status
from xlwt import Workbook
import xlrd
import multiselectfield

from farmbase.user_utils import get_user_view_projects, get_user_view_proposals, get_user_view_leads
from gearfarm.utils import farm_response
from gearfarm.utils.farm_response import build_pagination_response, api_success, api_bad_request
from gearfarm.utils.decorators import request_params_required
from clients.models import Lead, LeadOrganization, LeadIndividual, RequirementInfo, TrackCodeFile, LeadTrack, \
    LeadSource, LeadQuotation, ClientInfo, LeadReportFile, Client, LeadPunchRecord
from clients.serializers import LeadSimpleSerializer, LeadSerializer, LeadListSerializer, \
    LeadIndividualSerializer, LeadOrganizationSerializer, LeadRequiredFieldsSerializer, RequirementSerializer, \
    LeadPunchRecordViewSerializer, LeadPunchRecordCreateSerializer, TrackCodeFileSerializer, LeadExportSerializer, \
    LeadSemTrackSerializer, LeadConversionRateSerializer, LeadSourceSerializer, LeadQuotationViewSerializer, \
    LeadQuotationCreateSerializer, LeadQuotationEditSerializer, ClientInfoSerializer, LeadReportFileSerializer, \
    ClientSerializer
from clients.tasks import extract_lead_track_data_from_excel
from files.utils import handle_obj_files
from gearfarm.utils.farm_response import api_bad_request, api_success, api_request_params_required, api_not_found, \
    api_suspended, api_permissions_required
from gearfarm.utils.decorators import request_data_fields_required
from notifications.utils import create_notification, create_notification_to_users
from logs.models import Log
from farmbase.utils import any_true, get_user_by_name, gen_uuid, get_md5, this_month_start, \
    get_active_users_by_function_perm, get_protocol_host
from farmbase.permissions_utils import has_function_perm, func_perm_any_required, func_perm_required
from gearfarm.utils.const import LEAD_STATUS
from farmbase.serializers import UserSimpleSerializer, UserFilterSerializer
from proposals.models import Proposal
from projects.models import Project, ProjectClient
from reports.serializers import ReportPageSerializer, ProposalReportListSerializer, ReportTagSerializer


@method_decorator(request_data_fields_required(['projects', 'username', 'phone']), name='post')
class ClientList(APIView):
    def get(self, request):
        params = request.GET
        page = params.get('page', None)
        page_size = params.get('page_size', None)
        search = params.get('search', None)

        clients = Client.objects.filter(is_active=True).order_by('-created_at')
        if search:
            clients = clients.filter(Q(username__icontains=search) | Q(phone__icontains=search))

        return build_pagination_response(request, clients, ClientSerializer)

    def post(self, request):
        phone = request.data.get('phone')
        username = request.data.get('username')
        project_ids = request.data.get('projects')
        if not all([phone, username, project_ids]):
            return api_bad_request("手机号、姓名、项目不能为空")
        if Client.objects.filter(phone=phone, is_active=True).exists():
            return api_bad_request("手机号已存在")
        projects = Project.objects.filter(pk__in=project_ids).distinct()
        if not projects.exists():
            return api_bad_request("所选项目不存在")
        client = Client.objects.create(phone=phone, username=username, creator=request.top_user)
        for p in projects:
            ProjectClient.objects.create(project=p, client=client, is_admin=True)
        data = ClientSerializer(client, many=False).data
        return api_success(data)


@method_decorator(request_data_fields_required(['projects', 'username', 'phone']), name='post')
class ClientDetail(APIView):
    def get(self, request, id):
        client = get_object_or_404(Client, pk=id)
        data = ClientSerializer(client, many=False).data
        return Response({"result": True, 'data': data})

    def post(self, request, id):
        client = get_object_or_404(Client, pk=id)
        phone = request.data.get('phone')
        username = request.data.get('username')
        project_ids = request.data.get('projects')

        if not all([phone, username, project_ids]):
            return api_bad_request("手机号、姓名、项目不能为空")
        if Client.objects.exclude(pk=client.id).filter(phone=phone, is_active=True).exists():
            return api_bad_request("手机号已存在")
        projects = Project.objects.filter(pk__in=project_ids).distinct()

        if not projects.exists():
            return api_bad_request("所选项目不存在")

        client.phone = phone
        client.username = username
        client.save()

        new_project_ids = set(projects.values_list('id', flat=True))
        origin_project_ids = set(client.projects.values_list('id', flat=True))
        delete_project_ids = origin_project_ids - new_project_ids
        client.project_clients.filter(project_id__in=delete_project_ids).delete()
        for p in projects:
            p_c, created = ProjectClient.objects.get_or_create(project=p, client=client)
            if created:
                p_c.is_admin = True
                p_c.save()
        data = ClientSerializer(client, many=False).data
        return api_success(data)

    def put(self, request, id):
        client = get_object_or_404(Client, pk=id)
        phone = request.data.get('phone', None)
        username = request.data.get('username', None)

        if Client.objects.exclude(pk=client.id).filter(phone=phone, is_active=True).exists():
            return api_bad_request("手机号已存在")

        if phone:
            client.phone = phone
        if username:
            client.username = username
        client.save()

        data = ClientSerializer(client, many=False).data
        return api_success(data)

    def delete(self, request, id):
        client = get_object_or_404(Client, pk=id)
        client.is_active = False
        client.save()
        client.project_clients.all().delete()
        return api_success()


@api_view(['POST'])
@request_data_fields_required(['username', 'phone'])
def add_project_client(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    phone = request.data.get('phone')
    username = request.data.get('username')
    if not all([phone, username]):
        return api_bad_request("手机号、姓名不能为空")
    client = Client.objects.filter(phone=phone, is_active=True).first()
    if not client:
        client = Client.objects.create(phone=phone, username=username, creator=request.top_user)
    else:
        if project.project_clients.filter(client=client).exists():
            return api_bad_request("客户已存在在项目中")

    ProjectClient.objects.get_or_create(project=project, client=client, is_admin=True)
    return api_success()


@api_view(['GET'])
@request_params_required('phone')
def client_phone_check(request):
    phone = request.GET['phone']
    if not phone:
        return api_bad_request('phone不能为空')
    client = Client.objects.filter(phone=phone, is_active=True).first()
    if client:
        data = ClientSerializer(client, many=False).data
        return api_success(data)
    return api_not_found()


@api_view(['GET'])
def salesman_leads(request, user_id):
    salesman = get_object_or_404(User, pk=user_id)
    leads = salesman.sales_leads.all()
    params = request.GET
    status_list = re.sub(r'[;；,，]', ' ', params.get('status', '')).split()
    if status_list:
        leads = leads.filter(status__in=status_list)
    data = LeadListSerializer(leads, many=True).data
    return api_success(data=data)


class LeadList(APIView):
    def get(self, request, is_mine):
        user = request.user
        leads = Lead.objects.all()

        params = request.GET
        proposal_id = params.get('proposal', '')
        lead_id = params.get('lead', '')

        if proposal_id:
            proposal = get_object_or_404(Proposal, pk=proposal_id)
            if not proposal.lead_id:
                return api_not_found()
            leads = leads.filter(id=proposal.lead_id)
        elif lead_id:
            get_object_or_404(Lead, pk=lead_id)
            leads = leads.filter(id=lead_id)
        else:
            leads = get_user_view_leads(user, is_mine)
            all_creation_time = params.get('all_creation_time', '') in [True, '1', 1, 'true']
            all_close_time = params.get('all_close_time', '') in [True, '1', 1, 'true']
            search_value = str(params.get('search_value')).strip() if params.get('search_value') else None
            if search_value:
                base_leads = leads
                if str.isdigit(search_value):
                    pk_leads = base_leads.filter(pk=search_value)
                    name_leads = base_leads.filter(
                        Q(name__icontains=search_value) | Q(phone_number__icontains=search_value))
                    leads = pk_leads if pk_leads.exists() else name_leads
                else:
                    leads = base_leads.filter(Q(name__icontains=search_value) | Q(phone_number__icontains=search_value))

            creator_list = re.sub(r'[;；,，]', ' ', params.get('creators', '')).split()
            salesman_list = re.sub(r'[;；,，]', ' ', params.get('salesmen', '')).split()
            if creator_list:
                leads = leads.filter(creator_id__in=creator_list)
            if salesman_list:
                leads = leads.filter(salesman_id__in=salesman_list)

            status_list = re.sub(r'[;；,，]', ' ', params.get('status', '')).split()
            source_list = re.sub(r'[;；,，]', ' ', params.get('sources', '')).split()
            if status_list:
                leads = leads.filter(status__in=status_list)
            if source_list:
                leads = leads.filter(lead_source__source_type__in=source_list)

            creation_start_time = None
            creation_end_time = None
            close_start_time = None
            close_end_time = None

            try:
                if not all_creation_time:
                    if params.get('creation_start_time'):
                        creation_start_time = datetime.strptime(params.get('creation_start_time'), '%Y-%m-%d')
                    if params.get('creation_end_time'):
                        creation_end_time = datetime.strptime(params.get('creation_end_time'), '%Y-%m-%d')
                if not all_close_time:
                    if params.get('close_start_time'):
                        close_start_time = datetime.strptime(params.get('close_start_time'), '%Y-%m-%d')
                    if params.get('close_end_time'):
                        close_end_time = datetime.strptime(params.get('close_end_time'), '%Y-%m-%d')
            except Exception as e:
                return Response({"result": False, "message": '参数有误:{}'.format(str(e))})

            if creation_start_time:
                leads = leads.filter(created_date__gte=creation_start_time)
            if creation_end_time:
                leads = leads.filter(created_date__lte=creation_end_time)
            if close_start_time:
                ongoing_leads = leads.filter(status__in=['contact', 'proposal'])
                closed_leads = leads.exclude(status__in=['contact', 'proposal']).filter(
                    Q(proposal_closed_at__gte=close_start_time) | Q(closed_at__gte=close_start_time))
                leads = ongoing_leads | closed_leads
            if close_end_time:
                ongoing_leads = leads.filter(status__in=['contact', 'proposal'])
                closed_leads = leads.exclude(status__in=['contact', 'proposal']).filter(
                    Q(proposal_closed_at__lte=close_end_time + timedelta(days=1)) | Q(
                        closed_at__lte=close_end_time + timedelta(days=1)))
                leads = ongoing_leads | closed_leads

            order_by = params.get('order_by', 'created_at')
            order_dir = params.get('order_dir', 'desc')
            if not order_by:
                order_by = 'created_at'
            if not order_dir:
                order_dir = 'desc'
            if order_dir == 'desc':
                order_by = '-' + order_by
            # 判断 排序列表中是否存在对未完成任务数量进行排序
            if 'undone_tasks' in order_by:
                leads = sorted(leads, key=lambda x: len(x.undone_tasks()), reverse=order_dir == 'desc')
            elif 'quotation_status' in order_by:
                leads = sorted(leads, key=lambda x: x.quotation_status or '', reverse=order_dir == 'desc')
            else:
                leads = leads.order_by(order_by)
        return build_pagination_response(request, leads, LeadListSerializer)

    @transaction.atomic
    def post(self, request, lead_id=None):
        lead = None
        origin_lead = None
        origin_lead_source = None
        if lead_id:
            lead = get_object_or_404(Lead, pk=lead_id)
            origin_lead = deepcopy(lead)
            if lead.lead_source:
                origin_lead_source = deepcopy(lead.lead_source)

        savepoint = transaction.savepoint()

        request_data = deepcopy(request.data)
        build_client_info_company(request, request_data)

        # 线索来源数据处理方法
        lead_source_data = request_data.get('lead_source', None)
        if not lead_source_data:
            return api_bad_request('来源数据为必填参数')
        # 根据企业/组织/机构名创建企业对象
        lead_source_data = build_lead_source_data(request, lead_source_data)
        request_data['lead_source'] = lead_source_data

        if lead and lead.lead_source:
            lead_source_serializer = LeadSourceSerializer(lead.lead_source, data=lead_source_data)
        else:
            lead_source_serializer = LeadSourceSerializer(data=lead_source_data)
        if lead_source_serializer.is_valid():
            lead_source = lead_source_serializer.save()
            request_data['lead_source'] = lead_source.id
        else:
            transaction.savepoint_rollback(savepoint)
            return Response({"result": False, "message": lead_source_serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)

        if not lead_id:
            request_data['creator'] = request.user.id
            request_data['status'] = 'contact'
            serializer = LeadSerializer(data=request_data)
        else:
            for field_name in Lead.NOT_EDITABLE_FIELDS:
                request_data.pop(field_name, '')
            serializer = LeadSerializer(lead, data=request_data)

        if serializer.is_valid():
            try:
                lead = serializer.save()
                handle_obj_files(lead, request)

                # 线索没有成需求时  线索编辑时更新客户信息
                proposal = getattr(lead, 'proposal', None)
                if not proposal:
                    client_info = ClientInfo.objects.filter(lead_id=lead_id).first()
                    if client_info:
                        client_info.company_name = lead.company_name
                        client_info.company = lead.company
                        client_info.address = lead.address
                        client_info.contact_name = lead.contact_name
                        client_info.contact_job = lead.contact_job
                        client_info.phone_number = lead.phone_number
                        if client_info.company_name and client_info.client_background is None:
                            client_info.client_background = '1'
                        client_info.save()

                if lead.salesman_id != request.user.id:
                    content = "{username}提交了线索【{lead_name}】，并分配你为BD️".format(username=request.user.username,
                                                                             lead_name=lead.name)
                    url = '/clients/leads/mine/' + '?lead={}'.format(lead.id)
                    if lead_id:
                        content = "{username}编辑了线索【{lead_name}】，请查看️".format(username=request.user.username,
                                                                             lead_name=lead.name)
                    create_notification(lead.salesman, content, url)
                if lead_id:
                    Log.build_update_object_log(request.user, origin_lead, lead)
                    if origin_lead_source:
                        Log.build_update_object_log(request.user, origin_lead_source, lead.lead_source,
                                                    related_object=lead)
                else:
                    Log.build_create_object_log(request.user, lead)
                return Response({"result": True, 'data': serializer.data})
            except Exception as e:
                transaction.savepoint_rollback(savepoint)
                logger = logging.getLogger()
                logger.error(e)
                return Response({"result": False, "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        transaction.savepoint_rollback(savepoint)
        return Response({"result": False, "message": serializer.errors})


@api_view(['POST'])
def lead_reassign(request, lead_id):
    lead = get_object_or_404(Lead, pk=lead_id)
    salesman_id = request.data.get('salesman')
    if not salesman_id:
        return api_bad_request("参数salesman必填")
    if not str.isdigit(str(salesman_id)):
        return api_bad_request("参数salesman为int")

    salesman = get_object_or_404(User, id=salesman_id)
    if not salesman.is_active:
        return api_bad_request("该用户已离职")
    if salesman.id != lead.salesman_id:
        origin = deepcopy(lead)
        lead.salesman = salesman
        lead.save()
        lead.undone_tasks().filter(principal_id=origin.salesman_id).update(principal_id=lead.salesman_id)
        Log.build_update_object_log(request.user, origin, lead)
        # 线索重新分配BD
        if lead.salesman_id != request.user.id:
            content = "{username}分配你为线索【{lead_name}】的BD️".format(username=request.user.username,
                                                                 lead_name=lead.name)
            url = get_protocol_host(request) + '/clients/leads/mine/' + '?lead={}'.format(lead.id)
            create_notification(lead.salesman, content, url)
    return api_success(data=None)


@api_view(['POST'])
def lead_batch_reassign(request):
    lead_ids = request.data.get('leads', [])
    leads = Lead.objects.filter(pk__in=lead_ids)
    salesman_id = request.data.get('salesman')
    if not salesman_id:
        return api_bad_request("参数salesman必填")
    if not str.isdigit(str(salesman_id)):
        return api_bad_request("参数salesman为int")

    salesman = get_object_or_404(User, id=salesman_id)
    if not salesman.is_active:
        return api_bad_request("该用户已离职")

    for lead in leads:
        if salesman.id != lead.salesman_id:
            origin = deepcopy(lead)
            lead.salesman = salesman
            lead.save()
            lead.undone_tasks().filter(principal_id=origin.salesman_id).update(principal_id=lead.salesman_id)
            Log.build_update_object_log(request.user, origin, lead)
            # 需求重新指定产品经理，通知原产品经理、新产品经理
            if lead.salesman_id != origin.salesman_id and lead.salesman_id != request.user.id:
                content = "{username}分配你为线索【{lead_name}】的BD️".format(username=request.user.username,
                                                                     lead_name=lead.name)
                url = get_protocol_host(request) + '/clients/leads/mine/' + '?lead={}'.format(lead.id)
                create_notification(lead.salesman, content, url)
    return api_success()


class LeadDetail(APIView):
    def get(self, request, lead_id):
        lead = get_object_or_404(Lead, pk=lead_id)
        data = LeadListSerializer(lead).data
        return Response({"result": True, 'data': data})


def build_client_info_company(request, request_data):
    company_name = request_data.get('company_name', None)
    if company_name:
        organization = LeadOrganization.objects.filter(name=company_name).first()
        if not organization:
            organization = LeadOrganization.objects.create(name=company_name, creator=request.user)
        request_data['company'] = organization.id
    elif 'company_name' in request_data:
        request_data['company'] = None
        request_data['company_name'] = None
    return request_data


def build_lead_source_data(request, lead_source):
    source_type = lead_source.get('source_type', None)
    source_fields_dict = LeadSource.SOURCE_FIELDS_DICT
    source_editable_fields = LeadSource.SOURCE_EDITABLE_FIELDS
    # 根据来源 清理原字段数据
    if source_type and source_type in source_fields_dict:
        new_lead_source = {}
        current_source_fields = [field['field_name'] for field in source_fields_dict.get(source_type, [])]
        for field_name in source_editable_fields:
            if field_name in current_source_fields:
                new_lead_source[field_name] = lead_source.get(field_name, None)
            else:
                new_lead_source[field_name] = None
        new_lead_source['source_type'] = source_type
        lead_source = new_lead_source

    organization_name = lead_source.get('organization_name', None)
    organization_type = lead_source.get('organization_type', None)
    organization_type = organization_type if organization_type and organization_type not in ['其它', 'other'] else None

    if source_type == 'startup_camp':
        organization_type = '创业营/商学院/训练营'

    if organization_name:
        if organization_type:
            LeadOrganization.objects.filter(name=organization_name, organization_type__isnull=True).update(
                organization_type=organization_type)

            organization = LeadOrganization.objects.filter(name=organization_name,
                                                           organization_type=organization_type).first()
            if not organization:
                organization = LeadOrganization.objects.create(name=organization_name,
                                                               organization_type=organization_type,
                                                               creator=request.user)

        else:
            organization = LeadOrganization.objects.filter(name=organization_name).first()
            if not organization:
                organization = LeadOrganization.objects.create(name=organization_name, creator=request.user)
        lead_source['organization'] = organization.id

    return lead_source


def handle_organization_individual_name(request, request_data):
    organization_name = request_data.get('organization')
    individual_name = request_data.get('individual')
    company_name = request_data.get('company_name')

    if organization_name:
        organization = LeadOrganization.objects.filter(name=organization_name).first()
        if not organization:
            organization = LeadOrganization.objects.create(name=organization_name, creator=request.user)
        request_data['organization'] = organization.id
    if individual_name:
        individual, created = LeadIndividual.objects.get_or_create(name=individual_name)
        if created:
            individual.creator = request.user
            individual.save()
        request_data['individual'] = individual.id

    if company_name:
        if not all([organization_name, company_name == organization_name]):
            organization = LeadOrganization.objects.filter(name=company_name).first()
            if not organization:
                organization = LeadOrganization.objects.create(name=company_name, creator=request.user)
        request_data['company'] = organization.id
    elif 'company_name' in request_data:
        request_data['company'] = None
        request_data['company_name'] = None

    return request_data


@api_view(['GET'])
def leads_users(request):
    leads = Lead.objects.all()
    creator_id_list = [creator for creator in set(leads.values_list('creator_id', flat=True)) if creator]
    salesmen_id_list = [salesman for salesman in set(leads.values_list('salesman_id', flat=True)) if salesman]
    creators = User.objects.filter(id__in=creator_id_list)
    salesmen = User.objects.filter(id__in=salesmen_id_list)
    status_data = [{'codename': codename, 'name': name} for codename, name in Lead.STATUS]
    creators_data = UserSimpleSerializer(creators, many=True).data
    salesmen_data = UserSimpleSerializer(salesmen, many=True).data
    return Response(
        {"result": True, 'data': {'creators': creators_data, 'salesmen': salesmen_data, 'status': status_data}})


@api_view(['GET'])
def leads_filter_data(request):
    leads = Lead.objects.all()
    user = request.user
    limited = request.GET.get('limited')
    if limited not in ['False', 'false', '0', 0, False]:
        # 全部线索权限 限定
        cache_key = 'user_{user_id}_special_permissions'.format(user_id=user.id)
        user_special_permissions = cache.get(cache_key, {})
        if 'view_all_leads' in user_special_permissions:
            special_permission_data = user_special_permissions['view_all_leads']
            params = special_permission_data.get('params')
            if params:
                creator_username_list = params.get('creators', [])
                salesmen_username_list = params.get('salesmen', [])

                if user.groups.filter(name=settings.GROUP_NAME_DICT['sem']).exists():
                    my_leads = leads.filter(
                        Q(creator_id=user.id) | Q(salesman_id=user.id) | Q(lead_source__source_type='sem') | Q(
                            lead_source__source_type='website'))
                else:
                    my_leads = leads.filter(Q(creator_id=user.id) | Q(salesman_id=user.id))
                if creator_username_list:
                    leads = leads.filter(creator_id__in=creator_username_list)
                if salesmen_username_list:
                    leads = leads.filter(salesman_id__in=salesmen_username_list)
                leads = (leads | my_leads).distinct()

    creator_id_list = [creator for creator in set(leads.values_list('creator_id', flat=True)) if creator]
    salesmen_id_list = [salesman for salesman in set(leads.values_list('salesman_id', flat=True)) if salesman]
    if limited in ['False', 'false', '0', 0, False]:
        bd_id_list = User.objects.filter(groups__name=settings.GROUP_NAME_DICT['bd'], is_active=True).all().values_list(
            'id', flat=True)
        salesmen_id_list = set(salesmen_id_list) | set(bd_id_list)

    creators = User.objects.filter(id__in=creator_id_list).order_by('-is_active', 'date_joined')
    salesmen = User.objects.filter(id__in=salesmen_id_list).order_by('-is_active', 'date_joined')
    creators_data = UserFilterSerializer(creators, many=True).data
    salesmen_data = UserFilterSerializer(salesmen, many=True).data
    status_data = [{'codename': codename, 'name': name} for codename, name in Lead.STATUS]
    source_data = [{'codename': codename, 'name': name} for codename, name in LeadSource.LEAD_SOURCES]
    result_data = {'status': status_data, 'sources': source_data, 'creators': creators_data, 'salesmen': salesmen_data}
    return api_success(result_data)


@api_view(['GET'])
def leads_sources(request):
    individuals = LeadIndividual.objects.all()
    organizations = LeadOrganization.objects.all()
    sources = [{'codename': codename, 'name': name} for codename, name in LeadSource.LEAD_SOURCES]
    individual_data = LeadIndividualSerializer(individuals, many=True).data
    organization_data = LeadOrganizationSerializer(organizations, many=True).data
    data = {'individuals': individual_data, 'organizations': organization_data, 'sources': sources}
    return api_success(data=data)


@api_view(['GET'])
def client_organizations(request):
    organizations = LeadOrganization.objects.all()
    organization_data = LeadOrganizationSerializer(organizations, many=True).data
    return api_success(data=organization_data)


@api_view(['GET'])
@request_params_required('phone_number')
def leads_phone_check(request):
    phone_number = request.GET['phone_number']
    if not phone_number:
        return api_bad_request('phone_number不能为空')
    leads = Lead.objects.filter(phone_number=phone_number).order_by('-created_at')
    if leads.exists():
        data = LeadSimpleSerializer(leads.first()).data
        return api_success(data=data)
    return api_not_found()


@api_view(['POST'])
def perfect_fields(request, lead_id):
    lead = get_object_or_404(Lead, pk=lead_id)
    request_data = deepcopy(request.data)
    company_name = request_data.get('company_name')
    if company_name:
        organization = LeadOrganization.objects.filter(name=company_name).first()
        if not organization:
            organization = LeadOrganization.objects.create(name=company_name, creator=request.user)
        request_data['company'] = organization.id
    elif 'company_name' in request_data:
        request_data['company'] = None
        request_data['company_name'] = None

    origin = deepcopy(lead)
    serializer = LeadRequiredFieldsSerializer(lead, data=request_data)
    if serializer.is_valid():
        lead = serializer.save()
        content = "{}编辑了线索【{}】️".format(request.user.username, lead.name)
        url = '/clients/leads/mine/'
        if lead.salesman.id != request.user.id:
            create_notification(lead.salesman, content, url)
        if lead.creator.id != request.user.id:
            create_notification(lead.creator, content, url)
        Log.build_update_object_log(request.user, origin, lead)
        data = LeadListSerializer(lead).data
        return Response({"result": True, 'data': data})
    return Response({"result": False, "message": serializer.errors})


@api_view(['GET'])
def check_required_fields(request, lead_id):
    lead = get_object_or_404(Lead, pk=lead_id)
    if lead.status != 'contact':
        message = "该线索处于{}状态，不能创建需求".format(lead.get_status_display())
        check_result = False
    else:
        check_result = lead.can_be_converted_to_proposal
        message = ''
        if not check_result:
            message = "需要满足以下条件之一才能转需求：1. 一次会面打卡、2. 两次电话打卡、3. 已发布线索报告"
    return api_success(data={"can_be_converted": check_result, "message": message})


@api_view(['POST'])
@func_perm_required('close_lead')
def close_lead(request, lead_id):
    lead = get_object_or_404(Lead, pk=lead_id)
    if lead.status != LEAD_STATUS['contact'][0]:
        return Response({'result': False, 'message': '该线索当前状态为{}，不能标记为无效'.format(
            lead.get_status_display())})
    origin = deepcopy(lead)
    invalid_reason = request.data.get('invalid_reason', '')
    invalid_remarks = request.data.get('invalid_remarks', '')
    lead.invalid_reason = invalid_reason
    lead.invalid_remarks = invalid_remarks
    lead.status = LEAD_STATUS['invalid'][0]
    lead.closed_at = datetime.now()
    lead.closed_by = request.user
    lead.save()
    for report in lead.reports.all():
        report.expire_now()
    Log.build_update_object_log(request.user, origin, lead, comment=invalid_reason + '；' + invalid_remarks)
    data = LeadSimpleSerializer(lead).data
    return Response({"result": True, 'data': data})


@api_view(['POST'])
@func_perm_any_required(['close_lead', 'close_lead_review_required'])
def apply_close_lead(request, lead_id):
    lead = get_object_or_404(Lead, pk=lead_id)
    if lead.status != LEAD_STATUS['contact'][0]:
        return Response({'result': False, 'message': '该线索当前状态为{}，不能申请关闭无效'.format(
            lead.get_status_display())})
    origin = deepcopy(lead)
    invalid_reason = request.data.get('invalid_reason', '')
    invalid_remarks = request.data.get('invalid_remarks', '')
    lead.invalid_reason = invalid_reason
    lead.invalid_remarks = invalid_remarks
    lead.status = LEAD_STATUS['apply_close'][0]
    lead.apply_closed_at = datetime.now()
    lead.apply_closed_by = request.user
    lead.save()

    notification_content = '{}申请关闭线索【{} {}】请尽快审核'.format(request.user, lead.id, lead.name)
    notification_url = get_protocol_host(request) + '/clients/leads/' + '?lead={}'.format(lead.id)
    notification_users = get_active_users_by_function_perm('close_lead_review')
    for user in notification_users:
        cache_key = 'user_{user_id}_special_permissions'.format(user_id=user.id)
        user_special_permissions = cache.get(cache_key, {})
        close_lead_review_data = user_special_permissions.get('close_lead_review', {})
        review_users = close_lead_review_data.get('users', [])
        if review_users:
            if request.user.username in review_users:
                create_notification(user, notification_content, notification_url, is_important=True)
        else:
            create_notification(user, notification_content, notification_url, is_important=True)

    Log.build_update_object_log(request.user, origin, lead, comment=invalid_reason + '；' + invalid_remarks)
    data = LeadSimpleSerializer(lead).data
    return Response({"result": True, 'data': data})


@api_view(['POST'])
@func_perm_required('close_lead_review')
def confirm_close_lead(request, lead_id):
    lead = get_object_or_404(Lead, pk=lead_id)
    if lead.status != LEAD_STATUS['apply_close'][0]:
        return Response({'result': False, 'message': '该线索当前状态为{}，不能确认关闭'.format(
            lead.get_status_display())})

    user = request.user
    cache_key = 'user_{user_id}_special_permissions'.format(user_id=user.id)
    user_special_permissions = cache.get(cache_key, {})
    close_lead_review_data = user_special_permissions.get('close_lead_review', {})
    review_users = close_lead_review_data.get('users', [])
    if review_users:
        lead_users = []
        if lead.salesman:
            lead_users.append(lead.salesman.username)
        if lead.apply_closed_by:
            lead_users.append(lead.apply_closed_by.username)
        if not set(lead_users) & set(review_users):
            return farm_response.api_permissions_required('你没有权限关闭该线索')

    origin = deepcopy(lead)
    lead.status = LEAD_STATUS['invalid'][0]
    lead.closed_at = datetime.now()
    lead.closed_by = request.user
    lead.save()
    for report in lead.reports.all():
        report.expire_now()
    Log.build_update_object_log(request.user, origin, lead, comment='确认关闭')
    data = LeadSimpleSerializer(lead).data
    return Response({"result": True, 'data': data})


@api_view(['POST'])
def open_lead(request, lead_id):
    lead = get_object_or_404(Lead, pk=lead_id)
    if lead.status not in [LEAD_STATUS['invalid'][0], LEAD_STATUS['apply_close'][0]]:
        return Response({'result': False, 'message': '该线索当前状态为{}，不能重新打开到前期沟通'.format(
            lead.get_status_display())})
    origin = deepcopy(lead)
    lead.invalid_remarks = None
    lead.invalid_reason = None
    lead.closed_at = None
    lead.apply_closed_at = None
    lead.status = LEAD_STATUS['contact'][0]
    lead.save()
    Log.build_update_object_log(request.user, origin, lead, comment='重新开启线索')
    data = LeadListSerializer(lead).data
    return Response({"result": True, 'data': data})


class LeadRequirement(APIView):
    def get(self, request, lead_id):
        get_object_or_404(Lead, pk=lead_id)
        requirement = get_object_or_404(RequirementInfo, lead_id=lead_id)
        serializer = RequirementSerializer(requirement)
        return Response({"result": True, 'data': serializer.data})

    def post(self, request, lead_id):
        lead = get_object_or_404(Lead, pk=lead_id)
        request_data = deepcopy(request.data)
        request_data['lead'] = lead_id
        requirements = RequirementInfo.objects.filter(lead_id=lead_id)

        origin = None
        if requirements.exists():
            requirement = requirements.first()
            origin = deepcopy(requirement)
            serializer = RequirementSerializer(requirement, data=request_data)
        else:
            request_data['submitter'] = request.user.id
            serializer = RequirementSerializer(data=request_data)

        if serializer.is_valid():
            requirement = serializer.save()

            handle_obj_files(requirement, request)

            if origin:
                related_object = lead.proposal if Proposal.objects.filter(lead_id=lead_id).exists() else lead
                Log.build_update_object_log(request.user, origin, requirement, related_object=related_object)
            else:
                related_object = lead.proposal if Proposal.objects.filter(lead_id=lead_id).exists() else lead
                Log.build_create_object_log(request.user, requirement, related_object=related_object)
            return Response({"result": True, 'data': serializer.data})
        return Response({"result": False, "message": serializer.errors})


class LeadReportFileList(APIView):
    def get(self, request, lead_id):
        lead = get_object_or_404(Lead, pk=lead_id)
        report_files = lead.report_files.filter(is_active=True).order_by('published_at')
        serializer = LeadReportFileSerializer(report_files, many=True)
        return api_success(data=serializer.data)

    def post(self, request, lead_id):
        lead = get_object_or_404(Lead, pk=lead_id)
        request_data = deepcopy(request.data)
        request_data['lead'] = lead_id
        request_data['creator'] = request.user.id
        request_data['author'] = request.user.username
        request_data['is_active'] = True
        request_data['is_public'] = True
        serializer = LeadReportFileSerializer(data=request_data)
        if serializer.is_valid():
            report_file = serializer.save()
            file = request.data.get('file')
            report_file.title = file.name.rsplit(".", 1)[0]
            report_file.save()
            Log.build_create_object_log(request.user, report_file, related_object=lead)
            return api_success(data=serializer.data)
        return api_bad_request(message=serializer.errors)


class LeadReportFileDetail(APIView):
    def delete(self, request, report_file_id):
        report_file = get_object_or_404(LeadReportFile, pk=report_file_id)
        origin = deepcopy(report_file)
        report_file.is_active = False
        report_file.save()

        Log.build_update_object_log(request.user, origin, report_file, related_object=report_file.lead)
        return api_success()


class LeadPunchRecordList(APIView):
    def get(self, request, lead_id):
        lead = get_object_or_404(Lead, pk=lead_id)
        params = request.GET
        punch_records = lead.punch_records.all()
        order_by = params.get('order_by', 'created_at')
        order_dir = params.get('order_dir', 'asc')
        if not order_by:
            order_by = 'created_at'
        if not order_dir:
            order_dir = 'asc'
        if order_dir == 'desc':
            order_by = '-' + order_by
        punch_records = punch_records.order_by(order_by)
        serializer = LeadPunchRecordViewSerializer(punch_records, many=True)
        return api_success(data=serializer.data)

    def post(self, request, lead_id):
        lead = get_object_or_404(Lead, pk=lead_id)
        request_data = deepcopy(request.data)
        request_data['lead'] = lead_id
        request_data['creator'] = request.user.id
        serializer = LeadPunchRecordCreateSerializer(data=request_data)
        if serializer.is_valid():
            punch_record = serializer.save()
            Log.build_create_object_log(request.user, punch_record, related_object=lead)
            return api_success(data=serializer.data)
        return api_bad_request(message=serializer.errors)


@api_view(['GET'])
def lead_latest_punch_record(request, lead_id):
    lead = get_object_or_404(Lead, pk=lead_id)
    punch_records = lead.punch_records.order_by('-created_at')
    if punch_records.exists():
        serializer = LeadPunchRecordViewSerializer(punch_records.first())
        return api_success(data=serializer.data)
    return api_not_found()


# Create your tests here.
class LeadQuotationList(APIView):
    def get(self, request, lead_id):
        lead = get_object_or_404(Lead, pk=lead_id)
        params = request.GET
        order_by = params.get('order_by') or 'created_at'
        order_dir = params.get('order_dir') or 'desc'
        if order_dir == 'desc':
            order_by = '-' + order_by
        quotations = lead.quotations.order_by(order_by)
        serializer = LeadQuotationViewSerializer(quotations, many=True)
        return api_success(data=serializer.data)

    def post(self, request, lead_id):
        lead = get_object_or_404(Lead, pk=lead_id)
        request_data = deepcopy(request.data)
        request_data['lead'] = lead_id
        request_data['creator'] = request.user.id
        serializer = LeadQuotationCreateSerializer(data=request_data)
        if serializer.is_valid():
            quotation = serializer.save()
            handle_obj_files(quotation, request)
            quotation.edited_at = timezone.now()
            quotation.edited_date = timezone.now().date()
            quotation.editor = request.user
            quotation.save()
            create_notification_of_lead_quotation(request, quotation)
            Log.build_create_object_log(request.user, quotation, related_object=lead)
            serializer = LeadQuotationViewSerializer(quotation)
            return api_success(data=serializer.data)
        return api_bad_request(message=serializer.errors)


def create_notification_of_lead_quotation(request, quotation, is_edit=False):
    lead = quotation.lead
    notification_users = get_active_users_by_function_perm('provide_lead_quotation')
    notification_users = [user for user in notification_users if user.username != '唐海鹏']
    content = "线索【{} {}】等待报价，提交人：{}".format(lead.id, lead.name, request.user.username)
    if is_edit:
        content = "线索【{} {}】重新提交了报价需求内容，提交人：{}".format(lead.id, lead.name, request.user.username)
    url = get_protocol_host(
        request) + '/clients/leads/detail/' + '?lead_id={lead_id}&quotation_id={quotation_id}'.format(lead_id=lead.id,
                                                                                                      quotation_id=quotation.id)
    create_notification_to_users(notification_users, content, url=url, is_important=True)


@api_view(['GET'])
def lead_latest_quotation(request, lead_id):
    lead = get_object_or_404(Lead, pk=lead_id)
    quotations = lead.quotations.order_by('-edited_at')
    if quotations.exists():
        serializer = LeadQuotationViewSerializer(quotations.first())
        return api_success(data=serializer.data)
    return api_not_found()


# Create your tests here.
class LeadQuotationDetail(APIView):
    def get(self, request, id):
        quotation = get_object_or_404(LeadQuotation, pk=id)
        serializer = LeadQuotationViewSerializer(quotation, many=False)
        return api_success(data=serializer.data)

    def post(self, request, id):
        quotation = get_object_or_404(LeadQuotation, id=id)
        if quotation.status == 'quoted':
            return api_bad_request(message="当前状态为{}".format(quotation.get_status_display()))
        origin = deepcopy(quotation)
        request_data = deepcopy(request.data)

        serializer = LeadQuotationEditSerializer(quotation, data=request_data)
        if serializer.is_valid():
            quotation = serializer.save()

            handle_obj_files(quotation, request)

            quotation.edited_at = timezone.now()
            quotation.edited_date = timezone.now().date()
            quotation.editor = request.user
            if quotation.status == 'rejected':
                quotation.status = 'waiting'
            quotation.save()
            create_notification_of_lead_quotation(request, quotation, is_edit=True)
            Log.build_update_object_log(request.user, origin, quotation, related_object=quotation.lead)
            serializer = LeadQuotationViewSerializer(quotation)
            return api_success(data=serializer.data)
        return api_bad_request(message=serializer.errors)


@api_view(['POST'])
@func_perm_required('provide_lead_quotation')
def lead_quotation_quote(request, id):
    quotation = get_object_or_404(LeadQuotation, id=id)
    if quotation.status == 'rejected':
        return api_bad_request(message="当前状态为{}".format(quotation.get_status_display()))
    lead = quotation.lead
    origin = deepcopy(quotation)
    quotation_list = request.data.get('quotation_list')
    if not quotation_list:
        return api_request_params_required('quotation_list')
    # quotation.quotation_content = json.dumps(quotation_list, ensure_ascii=False)
    quotation.quotation_list = json.dumps(quotation_list, ensure_ascii=False)

    quotation.quoter = request.user
    quotation.status = 'quoted'
    quotation.quoted_at = timezone.now()
    quotation.save()
    content = "线索【{} {}】提交了线索报价，报价人：{}".format(lead.id, lead.name, request.user.username)
    url = get_protocol_host(request) + '/clients/leads/mine/' + '?lead={}'.format(lead.id)
    create_notification(quotation.lead.salesman, content, url=url, is_important=True)

    Log.build_update_object_log(request.user, origin, quotation, related_object=quotation.lead)
    serializer = LeadQuotationViewSerializer(quotation)
    return api_success(data=serializer.data)


@api_view(['POST'])
@func_perm_required('provide_lead_quotation')
def lead_quotation_reject(request, id):
    quotation = get_object_or_404(LeadQuotation, id=id)
    if quotation.status != 'waiting':
        return api_bad_request(message="当前状态为{}".format(quotation.get_status_display()))
    origin = deepcopy(quotation)
    rejected_reason = request.data.get('rejected_reason')
    if not rejected_reason:
        return api_request_params_required('rejected_reason')

    quotation.rejecter = request.user
    quotation.status = 'rejected'
    quotation.rejected_at = timezone.now()
    quotation.rejected_reason = rejected_reason
    quotation.save()
    content = "线索【{}】报价被驳回，驳回人：{}".format(quotation.lead.name, request.user.username)
    url = get_protocol_host(request) + '/clients/leads/mine/?lead={}'.format(quotation.lead.id)
    create_notification(quotation.lead.salesman, content, url=url, is_important=True)
    Log.build_update_object_log(request.user, origin, quotation, related_object=quotation.lead)
    serializer = LeadQuotationViewSerializer(quotation)
    return api_success(data=serializer.data)


@api_view(['GET'])
def leads_quotations_filter_data(request):
    status_data = [{'codename': codename, 'name': name} for codename, name in LeadQuotation.STATUS_CHOICES]
    quotations = LeadQuotation.objects.all()
    editor_id_list = [editor for editor in set(quotations.values_list('editor_id', flat=True)) if editor]
    editors = User.objects.filter(id__in=editor_id_list).order_by('-is_active', 'date_joined')
    editors_data = UserFilterSerializer(editors, many=True).data
    result_data = {'editors': editors_data, 'status': status_data}
    return api_success(data=result_data)


@api_view(['GET'])
def all_leads_quotations(request):
    if not has_function_perm(request.user, 'view_all_leads_quotations'):
        return api_permissions_required('view_all_leads_quotations')
    quotations = LeadQuotation.objects.all()

    params = request.GET
    creation_start_time = None
    creation_end_time = None
    try:
        if params.get('edit_start_date'):
            creation_start_time = datetime.strptime(params.get('edit_start_date'), '%Y-%m-%d')
        if params.get('edit_end_date'):
            creation_end_time = datetime.strptime(params.get('edit_end_date'), '%Y-%m-%d')
    except Exception as e:
        return api_bad_request(message='参数有误:{}'.format(str(e)))
    search_value = params.get('search_value')
    creator_list = re.sub(r'[;；,，]', ' ', params.get('editors', '')).split()
    status_list = re.sub(r'[;；,，]', ' ', params.get('status', '')).split()

    if creation_start_time:
        quotations = quotations.filter(edited_date__gte=creation_start_time)
    if creation_end_time:
        quotations = quotations.filter(edited_date__lte=creation_end_time)
    if creator_list:
        quotations = quotations.filter(editor_id__in=creator_list)
    if status_list:
        quotations = quotations.filter(status__in=status_list)
    if search_value:
        quotations = quotations.filter(lead__name__icontains=search_value)

    order_by = params.get('order_by') or 'edited_at'
    order_dir = params.get('order_dir') or 'desc'
    if order_dir == 'desc':
        order_by = '-' + order_by

    quotations = quotations.order_by(order_by)
    lead_id_sets = set()
    result_quotations = []
    for quotation in quotations:
        lead_id = quotation.lead_id
        if lead_id not in lead_id_sets:
            result_quotations.append(quotation)
            lead_id_sets.add(lead_id)
    return build_pagination_response(request, result_quotations, LeadQuotationViewSerializer)


@api_view(['GET'])
def my_leads_quotations(request):
    # STATUS_CHOICES = (
    #     ('waiting', '等待报价'),
    #     ('rejected', '已驳回'),
    #     ('quoted', '已经报价')
    # )
    quotations = LeadQuotation.objects.filter(lead__salesman_id=request.user.id)
    params = request.GET
    quotation_status = params.get('status', '')
    if quotation_status:
        if quotation_status not in ['waiting', 'rejected', 'quoted']:
            return api_bad_request("status not in ['waiting', 'rejected', 'quoted'] ")
        quotations = quotations.filter(status=quotation_status)

    quotations.order_by('-edited_at')
    lead_id_sets = set()
    result_quotations = []
    for quotation in quotations:
        lead = quotation.lead
        lead_id = quotation.lead_id
        if quotation_status:
            if lead.quotation_status == quotation_status:
                if lead_id not in lead_id_sets:
                    result_quotations.append(quotation)
                    lead_id_sets.add(lead_id)
        else:
            if lead_id not in lead_id_sets:
                result_quotations.append(quotation)
                lead_id_sets.add(lead_id)
    return build_pagination_response(request, result_quotations, LeadQuotationViewSerializer)


@api_view(['GET'])
def lead_reports(request, lead_id):
    lead = get_object_or_404(Lead, pk=lead_id)
    reports = lead.reports.order_by('-created_at')
    is_public = request.GET.get('is_public', None) in ['True', True, 'true', 1, '1']
    is_draft = request.GET.get('is_public', None) in ['False', False, 'false', 0, '0']
    report_data = []
    if is_public:
        reports = lead.reports.filter(is_public=True)
        report_data = ProposalReportListSerializer(reports, many=True).data
        report_files_data = LeadReportFileSerializer(lead.report_files.filter(is_active=True), many=True).data
        report_data.extend(report_files_data)
        report_data = sorted(report_data, key=lambda x: x['published_at'], reverse=True)
    elif is_draft:
        reports = lead.reports.filter(is_public=False).order_by('-created_at')
        report_data = ProposalReportListSerializer(reports, many=True).data
    else:
        report_data = ProposalReportListSerializer(reports, many=True).data
    return api_success(data=report_data)


@api_view(['GET'])
def lead_latest_report(request, lead_id):
    lead = get_object_or_404(Lead, pk=lead_id)
    last_report = lead.reports.filter(is_public=True).order_by('-published_at').first()
    if last_report:
        serializer = ReportPageSerializer(last_report)
        return api_success(serializer.data)
    return api_bad_request("不存在报告")


@api_view(['GET'])
def lead_latest_report_tags(request, lead_id):
    lead = get_object_or_404(Lead, pk=lead_id)
    last_reports = lead.reports.filter(is_public=True).order_by('-published_at')
    if last_reports.exists():
        serializer = ReportTagSerializer(last_reports.first())
        return Response({"result": True, 'data': serializer.data})
    return Response({"result": True, 'data': None, "message": "线索不存在报告"})


def get_and_save_sem_track_template():
    work_book = Workbook()  # 创建一个工作簿
    sheet_one = work_book.add_sheet("SEM跟踪表")  # 创建一个工作表
    export_fields = [
        {'field_name': 'channel', 'verbose_name': '渠道', 'col_width': 8},
        {'field_name': 'media', 'verbose_name': '媒体', 'col_width': 8},
        {'field_name': 'account', 'verbose_name': '账户', 'col_width': 10},
        {'field_name': 'plan', 'verbose_name': '计划', 'col_width': 16},
        {'field_name': 'unit', 'verbose_name': '单元', 'col_width': 16},
        {'field_name': 'keywords', 'verbose_name': '关键词', 'col_width': 16},
        {'field_name': 'device', 'verbose_name': '设备', 'col_width': 8},
        {'field_name': 'url', 'verbose_name': 'URL', 'col_width': 40},
    ]
    example_data = ['SEM', '百度', 'bj-齿轮', 'App开发-PC', '北京App开发', 'App开发软件', 'PC',
                    'https://chilunyc.com/landing/app/']

    for index_num, field in enumerate(export_fields):
        sheet_one.write(0, index_num, field['verbose_name'])

    for field_num, field in enumerate(example_data):
        sheet_one.write(1, field_num, field)

    for i in range(len(export_fields)):
        sheet_one.col(i).width = 256 * export_fields[i]['col_width']

    file_path = settings.MEDIA_ROOT + 'leads/sem_track_template.xls'

    dir_path = os.path.dirname(file_path)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    work_book.save(file_path)  # 保存
    return file_path


@api_view(['GET'])
def download_sem_track_template(request):
    if not TrackCodeFile.objects.filter(is_template=True).exists():
        file_path = get_and_save_sem_track_template()
        filename = 'sem_track_template.xls'
        template_data = {"filename": filename, "entry_path": file_path, 'output_path': file_path, "is_template": True}
        serializer = TrackCodeFileSerializer(data=template_data)
        if not serializer.is_valid():
            return Response({"result": False, "message": serializer.errors})
        serializer.save()

    track_file = TrackCodeFile.objects.get(is_template=True)
    file_path = track_file.output_path
    if not file_path or not os.path.exists(file_path):
        file_path = get_and_save_sem_track_template()
        track_file.entry_path = file_path
        track_file.output_path = file_path
        track_file.save()
    filename = 'sem_track_template.xls'
    wrapper = FileWrapper(open(file_path, 'rb'))
    response = FileResponse(wrapper, content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = "attachment; filename*=utf-8''{}".format(escape_uri_path(filename))
    return response


def new_lead_track_code():
    return gen_uuid(8)


@api_view(['POST'])
def sem_track_file_upload(request):
    entry_path = settings.MEDIA_ROOT + 'leads/{}_sem_track_entry.xls'.format(time.time())
    dir_path = os.path.dirname(entry_path)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    with open(entry_path, 'wb') as file:
        file.write(request.data.get('file').read())
    wb = xlrd.open_workbook(filename=entry_path)  # 打开文件
    sheet1 = wb.sheet_by_index(0)  # 通过索引获取表格

    lead_track_code_md5_dict = cache.get('lead_track_code_md5_dict', {})
    track_code_set = set(lead_track_code_md5_dict.values())

    result_data = []
    # excel文件中对应的字段
    field_names = ('channel', 'media', 'account', 'plan', 'unit', 'keywords', 'device', 'url')
    for rx in range(1, sheet1.nrows):
        origin_data = sheet1.row_values(rx)[:8]
        track_data = [str(int(filed_value) if isinstance(filed_value, float) else filed_value).strip() for filed_value
                      in origin_data]
        url = track_data[7]
        md5_hash = get_md5(''.join(track_data[:7]))

        if md5_hash in lead_track_code_md5_dict:
            track_code = lead_track_code_md5_dict[md5_hash]
        else:
            while True:
                track_code = new_lead_track_code()
                if track_code not in track_code_set:
                    break
            lead_track_code_md5_dict[md5_hash] = track_code
            track_code_set.add(track_code)

        if '?' not in url:
            track_url = '{url}?track_code={track_code}'.format(url=url, track_code=track_code)
        else:
            track_url = '{url}&track_code={track_code}'.format(url=url, track_code=track_code)
        track_data.append(track_url)
        track_data.append(track_code)
        track_data.append(md5_hash)
        result_data.append(deepcopy(track_data))
    work_book = Workbook()  # 创建一个工作簿
    sheet_one = work_book.add_sheet("SEM跟踪表")  # 创建一个工作表
    export_fields = [
        {'field_name': 'channel', 'verbose_name': '渠道', 'col_width': 8},
        {'field_name': 'media', 'verbose_name': '媒体', 'col_width': 8},
        {'field_name': 'account', 'verbose_name': '账户', 'col_width': 10},
        {'field_name': 'plan', 'verbose_name': '计划', 'col_width': 16},
        {'field_name': 'unit', 'verbose_name': '单元', 'col_width': 16},
        {'field_name': 'keywords', 'verbose_name': '关键词', 'col_width': 16},
        {'field_name': 'device', 'verbose_name': '设备', 'col_width': 8},
        {'field_name': 'url', 'verbose_name': 'URL', 'col_width': 40},

        {'field_name': 'track_url', 'verbose_name': '生成URL', 'col_width': 50},

        {'field_name': 'track_code', 'verbose_name': '跟踪码', 'col_width': 10},
        {'field_name': 'track_code', 'verbose_name': 'Hash Code', 'col_width': 10},
    ]

    for index_num, field in enumerate(export_fields):
        sheet_one.write(0, index_num, field['verbose_name'])

    for i in range(len(result_data)):
        for field_num, field in enumerate(result_data[i]):
            sheet_one.write(i + 1, field_num, field)

    for i in range(len(export_fields)):
        sheet_one.col(i).width = 256 * export_fields[i]['col_width']

    output_path = settings.MEDIA_ROOT + 'leads/{}_sem_track_output.xls'.format(time.time())

    dir_path = os.path.dirname(output_path)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

    work_book.save(output_path)  # 保存
    request_data = {'entry_path': entry_path, 'output_path': output_path, 'filename': request.data.get('file').name}
    track_file = TrackCodeFile.objects.create(**request_data)
    cache.set('lead_track_code_md5_dict', lead_track_code_md5_dict, None)
    extract_lead_track_data_from_excel.delay(track_file.id)
    serializer = TrackCodeFileSerializer(track_file)
    return Response({"result": True, "data": serializer.data})


@api_view(['GET'])
def sem_track_file_download(request, track_id):
    track_file = get_object_or_404(TrackCodeFile, pk=track_id)
    file_path = track_file.output_path

    wrapper = FileWrapper(open(file_path, 'rb'))

    filename = "SEM跟踪码URL导出文件-{}.xls".format(datetime.now().strftime('%y_%m_%d_%H_%M'))
    response = FileResponse(wrapper, content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = "attachment; filename*=utf-8''{}".format(escape_uri_path(filename))
    return response


@api_view(['GET'])
def sem_leads_filter_data(request):
    leads = Lead.objects.filter(lead_source__source_type='sem')
    creator_id_list = [creator for creator in set(leads.values_list('creator_id', flat=True)) if creator]
    creators = User.objects.filter(id__in=creator_id_list).order_by('-is_active', 'date_joined')
    creators_data = UserFilterSerializer(creators, many=True).data
    result_data = {'creators': creators_data}
    return api_success(data=result_data)


@api_view(['GET'])
def sem_leads_download(request):
    params = request.GET
    leads = Lead.objects.filter(lead_source__source_type='sem')
    creation_start_time = None
    creation_end_time = None
    try:
        if params.get('creation_start_time'):
            creation_start_time = datetime.strptime(params.get('creation_start_time'), '%Y-%m-%d')
        if params.get('creation_end_time'):
            creation_end_time = datetime.strptime(params.get('creation_end_time'), '%Y-%m-%d')
    except Exception as e:
        return Response({"result": False, "message": '参数有误:{}'.format(str(e))})

    if creation_start_time:
        leads = leads.filter(created_date__gte=creation_start_time)
    if creation_end_time:
        leads = leads.filter(created_date__lte=creation_end_time)

    creator_list = re.sub(r'[;；,，]', ' ', params.get('creators', '')).split()
    if creator_list:
        leads = leads.filter(creator_id__in=creator_list)

    leads = leads.distinct().order_by('-created_at')

    leads_data = LeadSemTrackSerializer(leads, many=True).data
    w = Workbook()  # 创建一个工作簿
    ws = w.add_sheet("SEM线索跟踪表")  # 创建一个工作表

    lead_export_fields = [
        {'field_name': 'created_date', 'verbose_name': '提交日期', 'col_width': 12},
        {'field_name': 'created_time', 'verbose_name': '提交时间', 'col_width': 8},
        {'field_name': 'creator_username', 'verbose_name': '提交人', 'col_width': 8},
        {'field_name': 'address', 'verbose_name': '客户所在地', 'col_width': 8},

        {'field_name': 'channel', 'verbose_name': '渠道', 'col_width': 8},
        {'field_name': 'media', 'verbose_name': '媒体', 'col_width': 8},
        {'field_name': 'account', 'verbose_name': '账户', 'col_width': 10},
        {'field_name': 'plan', 'verbose_name': '计划', 'col_width': 16},
        {'field_name': 'unit', 'verbose_name': '单元', 'col_width': 16},
        {'field_name': 'keywords', 'verbose_name': '关键词', 'col_width': 16},
        {'field_name': 'device', 'verbose_name': '设备', 'col_width': 8},
        {'field_name': 'url', 'verbose_name': 'URL', 'col_width': 40},

        {'field_name': 'name', 'verbose_name': '线索名称', 'col_width': 18},
        {'field_name': 'closed_within_a_day', 'verbose_name': 'T+1关闭', 'col_width': 16},
        {'field_name': 'closed_within_a_week', 'verbose_name': 'T+7关闭', 'col_width': 16},

        {'field_name': 'closed_at', 'verbose_name': '关闭时间', 'col_width': 20},
        {'field_name': 'closed_reason', 'verbose_name': '关闭理由', 'col_width': 30},
        {'field_name': 'undone_tasks', 'verbose_name': '当前任务', 'col_width': 30},
        {'field_name': 'salesman_username', 'verbose_name': 'BD', 'col_width': 8},
    ]

    lead_source_export_fields = [
        {'field_name': 'sem_track_code', 'verbose_name': '跟踪码', 'col_width': 10},
        {'field_name': 'sem_type_display', 'verbose_name': 'SEM线索来源', 'col_width': 16},
        {'field_name': 'leave_info_type_display', 'verbose_name': '留资方式', 'col_width': 12},
        {'field_name': 'leave_info_date', 'verbose_name': '留资日期', 'col_width': 12},
        {'field_name': 'leave_info_time', 'verbose_name': '留资时间', 'col_width': 8},
        {'field_name': 'sem_project_category', 'verbose_name': 'SEM产品分类', 'col_width': 16},
        {'field_name': 'sem_search_term', 'verbose_name': 'SEM搜索词', 'col_width': 16},
        {'field_name': 'source_address', 'verbose_name': '来源地区', 'col_width': 16},
    ]

    export_fields = lead_export_fields + lead_source_export_fields

    for index_num, field in enumerate(export_fields):
        ws.write(0, index_num, field['verbose_name'])

    for index_num, lead_data in enumerate(leads_data):
        new_lead_data = deepcopy(lead_data)
        lead_track = new_lead_data.pop('lead_track', {})
        new_lead_data.update(lead_track)

        lead_source_data = deepcopy(lead_data['lead_source'])
        new_lead_source_data = {}
        for filed in lead_source_export_fields:
            field_name = filed['field_name']
            field_value = lead_source_data.get(field_name, '')
            new_lead_source_data[field_name] = field_value if field_value else ''

        new_lead_data.update(new_lead_source_data)
        for field_num, field in enumerate(export_fields):
            field_value = new_lead_data.get(field['field_name'], '')
            ws.write(index_num + 1, field_num, field_value)

    for i in range(len(export_fields)):
        ws.col(i).width = 256 * export_fields[i]['col_width']

    path = settings.MEDIA_ROOT + 'sem_track_leads.xls'
    w.save(path)  # 保存
    wrapper = FileWrapper(open(path, 'rb'))
    filename = "SEM线索跟踪数据表-{}.xls".format(datetime.now().strftime('%y_%m_%d_%H_%M'))
    response = FileResponse(wrapper, content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = "attachment; filename*=utf-8''{}".format(escape_uri_path(filename))
    return response


def get_conversion_rate_statistic(creation_start_time, creation_end_time, leads=None):
    if not leads:
        leads = Lead.objects.all()

    if creation_start_time:
        leads = leads.filter(created_date__gte=creation_start_time)
    if creation_end_time:
        leads = leads.filter(created_date__lte=creation_end_time)

    result_data_dict = {
        "total_statistic": {
            'lead_count': 0,
            'lead_status_group': {
                'ongoing_count': 0,
                'invalid_count': 0,
                'converted_count': 0,
            },
            'proposal_count': 0,
            'proposal_status_group': {
                'ongoing_count': 0,
                'invalid_count': 0,
                'converted_count': 0,
            },
            'project_count': 0
        },
        "source_group_statistic": {}
    }

    for position, (source, source_display) in enumerate(LeadSource.LEAD_SOURCES):
        result_data_dict["source_group_statistic"][source] = {"source": source, "source_display": source_display,
                                                              "position": position,
                                                              'lead_count': 0, 'proposal_count': 0, 'project_count': 0}

    leads_data = LeadConversionRateSerializer(leads, many=True).data

    total_statistic = result_data_dict['total_statistic']
    source_group_statistic = result_data_dict['source_group_statistic']
    total_lead_status_group = total_statistic['lead_status_group']
    total_proposal_status_group = total_statistic['proposal_status_group']

    for lead_data in leads_data:
        lead_source = lead_data['lead_source']
        if not lead_source:
            continue

        source = lead_source['source_type']
        source_display = lead_source['source_type_display']
        if source and source not in result_data_dict['source_group_statistic']:
            continue
            # source_group_statistic[source] = {"source": source, "source_display": source_display,
            #                                   'lead_count': 0, 'proposal_count': 0, 'project_count': 0}

        current_group_data = source_group_statistic[source]

        total_statistic['lead_count'] = total_statistic['lead_count'] + 1
        current_group_data['lead_count'] = current_group_data['lead_count'] + 1

        lead_status = lead_data['status']
        # 转化为需求的线索
        if lead_status in ['proposal', 'no_deal', 'deal']:
            total_statistic['proposal_count'] = total_statistic['proposal_count'] + 1
            current_group_data['proposal_count'] = current_group_data['proposal_count'] + 1

            # 转化为需求的线索
            total_lead_status_group['converted_count'] = total_lead_status_group['converted_count'] + 1

            # 转化为项目的需求
            if lead_status == 'deal':
                total_statistic['project_count'] = total_statistic['project_count'] + 1
                current_group_data['project_count'] = current_group_data['project_count'] + 1
                total_proposal_status_group['converted_count'] = total_proposal_status_group['converted_count'] + 1
            # 进行中的需求
            elif lead_status == 'proposal':
                total_proposal_status_group['ongoing_count'] = total_proposal_status_group['ongoing_count'] + 1
            # 无效关闭的需求
            else:
                total_proposal_status_group['invalid_count'] = total_proposal_status_group['invalid_count'] + 1

        # 进行中的线索
        elif lead_status == 'contact':
            total_lead_status_group['ongoing_count'] = total_lead_status_group['ongoing_count'] + 1

        # 无效关闭的线索
        elif lead_status == 'invalid':
            total_lead_status_group['invalid_count'] = total_lead_status_group['invalid_count'] + 1

    total_statistic['lead_proposal_rate'] = '{:.1f}%'.format(
        total_statistic['proposal_count'] / total_statistic['lead_count'] * 100) if total_statistic[
        'lead_count'] else '0.0%'
    total_statistic['proposal_project_rate'] = '{:.1f}%'.format(
        total_statistic['project_count'] / total_statistic['proposal_count'] * 100) if total_statistic[
        'proposal_count'] else '0.0%'
    total_statistic['lead_project_rate'] = '{:.1f}%'.format(
        total_statistic['project_count'] / total_statistic['lead_count'] * 100) if total_statistic[
        'lead_count'] else '0.0%'

    total_lead_status_group['ongoing_rate'] = '{:.1f}%'.format(
        total_lead_status_group['ongoing_count'] / total_statistic['lead_count'] * 100) if total_statistic[
        'lead_count'] else '0.0%'
    total_lead_status_group['invalid_rate'] = '{:.1f}%'.format(
        total_lead_status_group['invalid_count'] / total_statistic['lead_count'] * 100) if total_statistic[
        'lead_count'] else '0.0%'
    total_lead_status_group['converted_rate'] = '{:.1f}%'.format(
        total_lead_status_group['converted_count'] / total_statistic['lead_count'] * 100) if total_statistic[
        'lead_count'] else '0.0%'

    total_proposal_status_group['ongoing_to_lead_rate'] = '{:.1f}%'.format(
        total_proposal_status_group['ongoing_count'] / total_statistic['lead_count'] * 100) if total_statistic[
        'lead_count'] else '0.0%'
    total_proposal_status_group['invalid_to_lead_rate'] = '{:.1f}%'.format(
        total_proposal_status_group['invalid_count'] / total_statistic['lead_count'] * 100) if total_statistic[
        'lead_count'] else '0.0%'
    total_proposal_status_group['converted_to_lead_rate'] = '{:.1f}%'.format(
        total_proposal_status_group['converted_count'] / total_statistic['lead_count'] * 100) if total_statistic[
        'lead_count'] else '0.0%'

    total_proposal_status_group['ongoing_rate'] = '{:.1f}%'.format(
        total_proposal_status_group['ongoing_count'] / total_statistic['proposal_count'] * 100) if total_statistic[
        'proposal_count'] else '0.0%'
    total_proposal_status_group['invalid_rate'] = '{:.1f}%'.format(
        total_proposal_status_group['invalid_count'] / total_statistic['proposal_count'] * 100) if total_statistic[
        'proposal_count'] else '0.0%'
    total_proposal_status_group['converted_rate'] = '{:.1f}%'.format(
        total_proposal_status_group['converted_count'] / total_statistic['proposal_count'] * 100) if \
        total_statistic[
            'proposal_count'] else '0.0%'

    for source in source_group_statistic:
        current_group_data = source_group_statistic[source]
        current_group_data['lead_proposal_rate'] = '{:.1f}%'.format(
            current_group_data['proposal_count'] / current_group_data['lead_count'] * 100) if current_group_data[
            'lead_count'] else '0.0%'
        current_group_data['proposal_project_rate'] = '{:.1f}%'.format(
            current_group_data['project_count'] / current_group_data['proposal_count'] * 100) if current_group_data[
            'proposal_count'] else '0.0%'
        current_group_data['lead_project_rate'] = '{:.1f}%'.format(
            current_group_data['project_count'] / current_group_data['lead_count'] * 100) if current_group_data[
            'lead_count'] else '0.0%'

    sorted_source_groups = sorted(source_group_statistic.values(), key=lambda x: x['position'])
    result_data = {'total_statistic': total_statistic, 'source_group_statistic': sorted_source_groups}
    return result_data


@api_view(['GET'])
def leads_conversion_rate(request):
    leads = Lead.objects.all()
    params = request.GET
    creation_start_time = None
    creation_end_time = None

    try:
        if params.get('creation_start_time'):
            creation_start_time = datetime.strptime(params.get('creation_start_time'), '%Y-%m-%d')
        if params.get('creation_end_time'):
            creation_end_time = datetime.strptime(params.get('creation_end_time'), '%Y-%m-%d')
    except Exception as e:
        return Response({"result": False, "message": '参数有误:{}'.format(str(e))})

    statistic_data = get_conversion_rate_statistic(creation_start_time, creation_end_time, leads)
    result_data = {'start_date': creation_start_time.strftime(settings.DATE_FORMAT) if creation_start_time else '',
                   'end_date': creation_end_time.strftime(settings.DATE_FORMAT) if creation_end_time else '',
                   'statistic_data': statistic_data}

    return Response({"result": True, "data": result_data})


@api_view(['GET'])
def leads_conversion_rate_monthly(request):
    leads = Lead.objects.all()
    today = datetime.today().date()

    result_data = []
    for timedelta_month_num in range(0, 12):
        current_month = today - relativedelta(months=timedelta_month_num)
        start_time = datetime(current_month.year, current_month.month, 1)
        if timedelta_month_num == 0:
            end_time = today
        else:
            next_month = current_month + relativedelta(months=1)
            end_time = datetime(next_month.year, next_month.month, 1) - timedelta(days=1)
        statistic_data = get_conversion_rate_statistic(start_time, end_time, leads)
        month_data = {'start_date': start_time.strftime(settings.DATE_FORMAT), 'month': start_time.strftime('%Y-%m'),
                      'end_date': end_time.strftime(settings.DATE_FORMAT), 'statistic_data': statistic_data}
        result_data.append(month_data)
    return Response({"result": True, "data": result_data})


@api_view(['GET'])
def data_migrate(request):
    return Response({"result": True, "data": None})


def lead_sem_website_source_data_migrate():
    website_leads = Lead.objects.filter(lead_source__source_type='website')
    for lead in website_leads:
        lead_created_at = lead.created_at
        lead_created_at_date_str = lead_created_at.strftime('%Y.%m.%d')
        if lead_created_at_date_str < '2019.11.15':
            lead.lead_source.source_type = 'sem'
            lead.lead_source.sem_type = 'baidu'
            lead.lead_source.save()
        elif '2020.02.02' > lead_created_at_date_str >= '2019.11.15':
            if lead.lead_source.leave_info_type != 'form_submit':
                lead.lead_source.source_type = 'sem'
                lead.lead_source.sem_type = 'baidu'
                lead.lead_source.save()
    lead_sources = LeadSource.objects.filter(source_type__in=['startup_camp', 'org_referral'])

    for lead_source in lead_sources:
        if lead_source.source_type == 'startup_camp':
            if lead_source.organization and not lead_source.organization.organization_type:
                lead_source.organization.organization_type = '创业营/商学院/训练营'
                lead_source.organization.save()
        elif lead_source.source_type == 'org_referral':
            if lead_source.organization and lead_source.organization_type and not lead_source.organization.organization_type:
                lead_source.organization.organization_type = lead_source.organization_type
                lead_source.organization.save()


# 线索数据迁移
def lead_source_data_migrate():
    leads = Lead.objects.all()
    for lead in leads:
        if not lead.lead_source:
            lead_source = LeadSource.objects.create()
            lead.lead_source = lead_source
            lead.save()
        lead_source = lead.lead_source
        # 搜索引擎
        if lead.source == 'search_engine':
            if lead.search_engine_type == "mini_program":
                lead_source.source_type = 'content_marketing'
                lead_source.content_marketing_type = "wx_mp"
            elif lead.search_engine_type in ['sougou', 'shenma', '360', 'baidu', 'phone', 'toutiao']:
                lead_source.source_type = 'sem'
                lead_source.sem_type = lead.search_engine_type
            elif lead.search_engine_type == "website":
                lead_source.source_type = 'website'
            else:
                lead_source.source_type = 'sem'
                lead_source.sem_type = 'other'
            lead_source.sem_track_code = lead.track_code
            lead_source.leave_info_at = lead.leave_info_at
            lead_source.leave_info_type = lead.leave_info_type
        elif lead.source == 'strategy_cooperation':
            lead_source.source_type = 'org_referral'
            lead_source.organization = lead.organization
        elif lead.source == 'rebate_cooperation':
            lead_source.source_type = 'org_referral'
            lead_source.organization = lead.organization
            if lead.individual:
                lead_source.contact_name = lead.individual.name
        elif lead.source == 'client_referral':
            lead_source.source_type = 'client_referral'
            lead_source.organization = lead.organization
            if lead.individual:
                lead_source.contact_name = lead.individual.name
        elif lead.source == 'activity':
            lead_source.source_type = 'activity'
            lead_source.activity_type = lead.activity_type
            lead_source.activity_name = lead.activity_name
        elif lead.source == 'other':
            lead_source.source_type = 'social_network'

        if lead.source_remark:
            lead_source.source_remark = lead.source_remark

        lead_source.save()
        if getattr(lead, 'proposal', None):
            lead.proposal.lead_source = lead_source
            lead.proposal.save()


def proposal_source_data_migrate():
    leads = Proposal.objects.filter(lead_id__isnull=True)
    for lead in leads:
        if not lead.lead_source:
            lead_source = LeadSource.objects.create()
            lead.lead_source = lead_source
            lead.save()
        lead_source = lead.lead_source
        # 搜索引擎
        if lead.source == 'search_engine':
            if lead.search_engine_type == "mini_program":
                lead_source.source_type = 'content_marketing'
                lead_source.content_marketing_type = "wx_mp"
            elif lead.search_engine_type in ['sougou', 'shenma', '360', 'baidu', 'phone', 'toutiao']:
                lead_source.source_type = 'sem'
                lead_source.sem_type = lead.search_engine_type
            elif lead.search_engine_type == "website":
                lead_source.source_type = 'website'
            else:
                lead_source.source_type = 'website'
            # lead_source.sem_track_code = lead.track_code
            # lead_source.leave_info_at = lead.leave_info_at
            # lead_source.leave_info_type = lead.leave_info_type
        elif lead.source == 'strategy_cooperation':
            lead_source.source_type = 'org_referral'
            lead_source.organization = lead.organization
        elif lead.source == 'rebate_cooperation':
            lead_source.source_type = 'org_referral'
            lead_source.organization = lead.organization
            if lead.individual:
                lead_source.contact_name = lead.individual.name
        elif lead.source == 'client_referral':
            lead_source.source_type = 'client_referral'
            lead_source.organization = lead.organization
            if lead.individual:
                lead_source.contact_name = lead.individual.name
        elif lead.source == 'client_repurchase':
            lead_source.source_type = 'client_project_iteration'
            lead_source.organization = lead.organization
            if lead.individual:
                lead_source.contact_name = lead.individual.name
        elif lead.source == 'activity':
            lead_source.source_type = 'activity'
            lead_source.activity_type = lead.activity_type
            lead_source.activity_name = lead.activity_name
        elif lead.source == 'oneself':
            lead_source.source_type = 'social_network'
        elif lead.source == 'other':
            if lead.source_remark and "原朋友" in lead.source_remark:
                lead_source.source_type = 'social_network'
        if lead.source_remark:
            lead_source.source_remark = lead.source_remark
        lead_source.save()


def migrate_lead_source_data_from_excel():
    leads = Lead.objects.all()
    source_type_display_dict = dict(
        [(source_type_display, source_type) for source_type, source_type_display in LeadSource.SOURCES])
    activity_type_display_dict = dict(
        [(source_type_display, source_type) for source_type, source_type_display in LeadSource.ACTIVITY_TYPES])
    sem_type_display_dict = dict(
        [(source_type_display, source_type) for source_type, source_type_display in LeadSource.SEM_CHOICES])

    entry_path = 'clients/migrate_lead_source_data.xlsx'
    wb = xlrd.open_workbook(filename=entry_path)  # 打开文件
    sheet1 = wb.sheet_by_index(0)  # 通过索引获取表格
    result_data = []
    # excel文件中对应的字段
    field_names = (
        'lead_id', 'origin_source_display', 'source_type_display', 'activity_type_display', 'sem_type_display',
        'organization_type')
    for rx in range(1, sheet1.nrows):
        lead_source_data = sheet1.row_values(rx)[:6]
        lead_source_data[0] = str(int(lead_source_data[0]))
        lead_source_dict = dict(zip(field_names, lead_source_data))
        if lead_source_dict['source_type_display']:
            lead_source_dict["source_type"] = source_type_display_dict[lead_source_dict['source_type_display']]
        if lead_source_dict['activity_type_display']:
            lead_source_dict["activity_type"] = activity_type_display_dict[lead_source_dict['activity_type_display']]
        if lead_source_dict['sem_type_display']:
            lead_source_dict["sem_type"] = sem_type_display_dict[lead_source_dict['sem_type_display']]

        lead = leads.filter(pk=int(lead_source_dict['lead_id']))
        if lead.exists():
            lead = lead.first()
            if not lead.lead_source:
                lead_source = LeadSource.objects.create()
                lead.lead_source = lead_source
                lead.save()
            lead_source = lead.lead_source
            if lead_source_dict.get('source_type'):
                lead_source.source_type = lead_source_dict['source_type']
            if lead_source_dict.get('activity_type'):
                lead_source.activity_type = lead_source_dict['activity_type']
            if lead_source_dict.get('sem_type'):
                lead_source.sem_type = lead_source_dict['sem_type']
            if lead_source_dict['organization_type']:
                lead_source.organization_type = lead_source_dict['organization_type']
            lead_source.save()
        result_data.append(lead_source_dict)


@api_view(['GET'])
def one_time_authentication_key(request, client_id):
    client = get_object_or_404(Client, pk=client_id)
    if not client.is_active:
        return api_suspended()
    authentication_key = 'client-{}{}'.format(client.id, gen_uuid(8))
    key_data = {'authentication_key': authentication_key, 'created_at': timezone.now(), 'expired_seconds': 3600,
                'client': {'id': client.id, 'phone': client.phone, 'username': client.username}}
    cache.set(authentication_key, key_data, 3600)
    return Response({"result": True, "data": key_data})


@api_view(['GET'])
def my_ongoing_leads(request):
    ongoing_leads = Lead.ongoing_leads().filter(salesman_id=request.user.id).order_by('-created_at')
    data = LeadSimpleSerializer(ongoing_leads, many=True).data
    return api_success(data)


@api_view(['GET'])
def recent_punch_leads(request):
    start_day = timezone.now() - timedelta(days=30)
    leads = request.user.sales_leads.filter(punch_records__created_at__gte=start_day).distinct().order_by(
        '-created_at')
    data = LeadSimpleSerializer(leads, many=True).data
    return api_success(data)


@api_view(['GET'])
def lead_recent_punch_records(request, lead_id):
    lead = get_object_or_404(Lead, pk=lead_id)
    start_day = timezone.now() - timedelta(days=30)
    punch_records = lead.punch_records.filter(created_at__gte=start_day).order_by('-created_at')
    serializer = LeadPunchRecordViewSerializer(punch_records, many=True)
    return api_success(data=serializer.data)


@api_view(['GET'])
def my_recent_punch_records(request):
    params = request.GET
    leads_list = re.sub(r'[;；,，]', ' ', params.get('leads', '')).split()

    start_day = timezone.now() - timedelta(days=30)
    punch_records = LeadPunchRecord.objects.filter(created_at__gte=start_day).filter(
        lead__salesman_id=request.user.id).order_by('-created_at')
    if leads_list:
        punch_records = punch_records.filter(lead_id__in=leads_list)

    serializer = LeadPunchRecordViewSerializer(punch_records, many=True)
    return api_success(data=serializer.data)
