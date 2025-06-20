from copy import deepcopy
import logging
import uuid
import re
import json
from datetime import datetime, timedelta
import threading
from itertools import chain
from base64 import b64decode
from wsgiref.util import FileWrapper

from django.http import FileResponse
from django.utils.encoding import escape_uri_path
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.conf import settings
from django.contrib.auth.models import User
from django.utils.decorators import method_decorator
from django.db.models import Sum, IntegerField, When, Case, Q
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import api_view

from gearfarm.utils.base64_to_image_file import base64_string_to_file
from gearfarm.utils import farm_response
from auth_top.authentication import TokenAuthentication
from auth_top.serializers import TopUserViewSerializer
from gearfarm.utils.simple_responses import api_success, api_bad_request, api_suspended, api_permissions_required, \
    api_invalid_authentication_key, api_not_found, api_request_params_required,build_pagination_response
from gearfarm.utils.simple_decorators import request_data_fields_required, request_params_required
from geargitlab.gitlab_client import GitlabOauthClient
from gearfarm.utils.const import DEVELOPMENT_GUIDES
from farmbase.utils import gen_uuid, in_group, last_week_start, next_week_end, this_week_end, \
    get_phone_verification_code
from auth_top.models import TopToken, TopUser
from geargitlab.gitlab_client import GitlabClient
from projects.models import Project, ProjectPrototype
from projects.serializers import ProjectWithDeveloperListSerializer, ProjectPrototypeSerializer
from oauth.aliyun_client import AliyunApi

from clients.models import Client
from clients.serializers import ClientSerializer, ProjectClientSerializer
from farmbase.utils import get_user_data
from projects.models import ProjectClient, DeliveryDocument, DeliveryDocumentType
from projects.serializers import ProjectDetailClientSerializer, DeliveryDocumentSerializer
from projects.api import get_client_calendar_serializer_data
from gearmail.serializers import EmailRecordSerializer

gitlab_client = GitlabClient()
logger = logging.getLogger()


@method_decorator(request_data_fields_required(['username']), name='post')
class MyInfo(APIView):
    def get(self, request):
        client = request.client
        data = ClientSerializer(client).data
        return api_success(data)

    def post(self, request):
        client = request.client
        top_user = request.top_user
        phone = request.data.get('phone', None)
        username = request.data.get('username')
        avatar = request.data.get('avatar', None)

        if phone:
            if Client.objects.filter(phone=phone, is_active=True).exclude(pk=client.id).exists():
                return api_bad_request("手机号已存在")
            client.phone = phone
        client.username = username
        if avatar is not None:
            file = base64_string_to_file(avatar)
            if file:
                client.avatar = file
        client.save()
        data = ClientSerializer(client).data
        return api_success(data)


@api_view(['GET'])
@request_params_required('phone', 'code_type')
def phone_code(request):
    client = request.client
    code_type = request.GET.get('code_type', None)
    phone = request.GET.get('phone', None)
    if code_type not in ['change_my_phone']:
        return api_bad_request('请输入正确的code_type')
    if phone:
        if Client.objects.filter(phone=phone, is_active=True).exclude(pk=client.id).exists():
            return api_bad_request("手机号已被其他人绑定")
        code_key = '{}-{}-{}-code'.format('client', code_type, phone)
        if settings.DEVELOPMENT:
            code = settings.DEVELOPMENT_DD_CODE
            cache.set(code_key, {'code': code, 'time': timezone.now()}, 60 * 10)
            return api_success('测试环境验证码:{}'.format(code))

        code_data = cache.get(code_key, None)
        if code_data and code_data['time'] > timezone.now() - timedelta(minutes=1, seconds=30):
            return api_bad_request('不可频繁发送')

        code = get_phone_verification_code()
        aliyun_client = AliyunApi(access_key_id=settings.ALIYUN_ACCESS_KEY_ID,
                                  access_key_secret=settings.ALIYUN_ACCESS_KEY_SECRET)
        aliyun_client.send_login_check_code_sms(phone, code, '【齿轮易创-客户】')
        cache.set(code_key, {'code': code, 'time': timezone.now()}, 60 * 10)
        return api_success('短信发送成功')
    return api_bad_request(message="手机号必填")


@api_view(['GET'])
def my_projects(request):
    client = request.client
    projects = client.projects.order_by('done_at', '-created_at')
    data = ProjectWithDeveloperListSerializer(projects, many=True).data
    return api_success(data=data)


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


@api_view(['POST'])
@request_data_fields_required(['username', 'phone', 'is_admin'])
def add_project_client(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    phone = request.data.get('phone')
    username = request.data.get('username')
    if not all([phone, username]):
        return api_bad_request("手机号、姓名不能为空")
    is_admin = True if request.data.get('is_admin') else False
    permissions = []
    if not is_admin:
        permissions = request.data.get('permissions', [])
    client = Client.objects.filter(phone=phone, is_active=True).first()
    if not client:
        client = Client.objects.create(phone=phone, username=username, creator=request.top_user)
    project_client, created = ProjectClient.objects.get_or_create(project=project, client=client)
    project_client.is_admin = is_admin
    if not is_admin:
        project_client.permissions = permissions
    project_client.save()
    data = ProjectClientSerializer(project_client).data
    return api_success(data)


@api_view(['GET'])
def project_detail(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    data = ProjectDetailClientSerializer(project).data
    return api_success(data)


@api_view(['GET'])
def project_my_permissions(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    project_client = get_object_or_404(ProjectClient, project=project, client=request.client)
    data = ProjectClientSerializer(project_client).data
    return api_success(data['permissions'])


@api_view(['GET'])
def project_clients(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    obj_list = []
    if request.client:
        current_client = ProjectClient.objects.filter(client_id=request.client.id, project_id=project.id).first()
        if current_client:
            obj_list.append(current_client)
        other_list = list(
            project.project_clients.exclude(client_id=request.client.id).filter(client__is_active=True).order_by(
                '-created_at').distinct())
        obj_list.extend(other_list)
    else:
        obj_list = project.project_clients.filter(client__is_active=True).order_by('-created_at')

    return build_pagination_response(request, obj_list, ProjectClientSerializer)


@method_decorator(request_data_fields_required(['username', 'phone', 'is_admin']), name='post')
class ProjectClientDetail(APIView):
    def get(self, request, project_id, client_id):
        project_client = get_object_or_404(ProjectClient, project_id=project_id, client_id=client_id)
        data = ProjectClientSerializer(project_client).data
        return api_success(data=data)

    def post(self, request, project_id, client_id):
        project_client = get_object_or_404(ProjectClient, project_id=project_id, client_id=client_id)
        client = project_client.client

        if request.client.id == client.id:
            return api_bad_request("不能编辑自己的权限")
        phone = request.data.get('phone')
        username = request.data.get('username')
        if not all([phone, username]):
            return api_bad_request("手机号、姓名不能为空")

        if Client.objects.filter(phone=phone, is_active=True).exclude(pk=client.id).exists():
            return api_bad_request("手机号已存在")
        is_admin = True if request.data.get('is_admin') else False
        permissions = []
        if not is_admin:
            permissions = request.data.get('permissions', [])
        client.phone = phone
        client.username = username
        client.save()
        project_client.is_admin = is_admin
        if not is_admin:
            project_client.permissions = permissions
        project_client.save()

        data = ProjectClientSerializer(project_client).data
        return api_success(data=data)

    def delete(self, request, project_id, client_id):
        project_client = get_object_or_404(ProjectClient, project_id=project_id, client_id=client_id)
        project_client.delete()
        return api_success()


@api_view(['GET'])
def project_members(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    manager_data = None
    if project.manager:
        manager_data = get_user_data(project.manager)
        manager_data['roles'] = [{"field_name": 'manager', "name": "项目经理", "short_name": 'PMO'}]

    product_manager_data = None
    if project.product_manager:
        if project.product_manager_id == project.manager_id:
            manager_data['roles'].append({"field_name": 'product_manager', "name": "产品经理", "short_name": 'PM'})
        else:
            product_manager_data = get_user_data(project.product_manager)
            product_manager_data['roles'] = [{"field_name": 'product_manager', "name": "产品经理", "short_name": 'PM'}]
    members = []
    if manager_data:
        members.append(manager_data)
    if product_manager_data:
        members.append(product_manager_data)
    return api_success(data=members)


@api_view(['GET'])
def project_last_calendar(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    calendar = project.calendars.order_by('-created_at').first()
    if not calendar:
        return api_not_found()
    data = get_client_calendar_serializer_data(calendar)
    return api_success(data)


@api_view(['GET'])
def project_calendars(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    calendars = project.calendars.filter(is_public=True).order_by('-created_at')
    data = []
    for i in calendars:
        item = get_client_calendar_serializer_data(i)
        data.append(item)
    return api_success(data)


@api_view(['GET'])
def project_design(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    links = getattr(project, 'links', None)
    design_link = None
    if links:
        design_link = links.ui_link
    return api_success(design_link)


@api_view(['GET'])
def project_designs(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    links = getattr(project, 'links', None)
    design_links = []
    if links:
        ui_links = json.loads(links.ui_links, encoding='utf-8') if links.ui_links else []
        for ui_link in ui_links:
            name = ui_link.get('name', '').strip() or 'UI设计稿'
            link = ui_link.get('link', '').strip()
            if name and link:
                design_links.append({
                    'name': name,
                    'link': link
                })
    return api_success(design_links)


@api_view(['GET'])
def project_email_records(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    obj_list = project.email_records.filter(status=1).order_by('-created_at')
    return build_pagination_response(request, obj_list, EmailRecordSerializer)


@api_view(['GET'])
def project_prototypes(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    prototypes = ProjectPrototype.client_public_prototypes(project.prototypes.filter(is_deleted=False)).order_by('-created_at')
    data = ProjectPrototypeSerializer(prototypes, many=True).data
    return api_success(data=data)


@api_view(['GET'])
def project_deployment_servers(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    data = []
    if project.deployment_servers:
        deployment_servers = json.loads(project.deployment_servers, encoding='utf-8')
        for server in deployment_servers:
            show_to_client = server.get('show_to_client', False)
            if show_to_client:
                data.append(server)
    return api_success(data=data)


@api_view(['GET'])
def project_delivery_documents(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    delivery_documents = project.delivery_documents.filter(is_deleted=False).order_by('document_type__number')
    result_data = {
        "compress_zip": None,
        "delivery_documents": [],
        "other_documents": [],
    }
    for doc in delivery_documents:
        if doc.document_type.number == DeliveryDocumentType.DELIVERY_DOCUMENT_NUMBER:
            result_data['compress_zip'] = doc
        elif doc.document_type.number == DeliveryDocumentType.UNCLASSIFIED_DOCUMENT_NUMBER:
            result_data['other_documents'].append(doc)
        else:
            result_data['delivery_documents'].append(doc)

    if result_data['compress_zip']:
        result_data['compress_zip'] = DeliveryDocumentSerializer(result_data['compress_zip']).data
    if result_data['delivery_documents']:
        result_data['delivery_documents'] = DeliveryDocumentSerializer(result_data['delivery_documents'],
                                                                       many=True).data
    if result_data['other_documents']:
        result_data['other_documents'] = DeliveryDocumentSerializer(result_data['other_documents'], many=True).data

    return api_success(result_data)


@api_view(['POST'])
@request_data_fields_required('authentication_key')
def one_time_authentication_login(request):
    authentication_key = request.data.get('authentication_key')
    authentication_data = cache.get(authentication_key, None)
    if not authentication_data:
        return api_invalid_authentication_key()
    if 'client' in authentication_data:
        client_id = authentication_data['client']['id']
        client = Client.objects.filter(id=client_id).first()
        if not client:
            return api_bad_request(message="未找到账户")
        if client.is_active:
            token_data = get_client_cache_token(client)
            cache.delete(authentication_key)
            top_user = client.top_user
            token_data['user_info'] = top_user.user_info()
            return api_success(data=token_data)
        return api_suspended()
    return api_invalid_authentication_key()


def get_client_cache_token(client):
    real_token, created = TopToken.get_or_create(client=client)
    # 这种方式获取的Token认证用户 不可进行编辑操作 只能GET请求
    real_token_data = {"token": real_token.key, 'user_type': real_token.user_type, 'editable': False}
    # 临时token有效期 2小时
    access_token = settings.ONE_TIME_AUTH_PREFIX + TopToken.generate_key()
    cache.set(access_token, real_token_data, 60 * 60 * 2)
    access_token_data = {"token": access_token, 'user_type': real_token.user_type, 'editable': False}
    return access_token_data


@api_view(['GET'])
def download_delivery_document(request, uid):
    signature = request.GET.get('X-Gear-Signature', None)
    if not signature:
        return api_request_params_required('X-Gear-Signature')
    signature_key = cache.get(signature, None)
    if not signature_key:
        return api_bad_request('X-Gear-Signature参数无效')
    document = DeliveryDocument.objects.filter(uid=uid, is_deleted=False).first()
    if not document:
        return api_not_found("文档不存在")
    wrapper = FileWrapper(document.file.file)
    response = FileResponse(wrapper, content_type='application/{}'.format(document.document_type.suffix))
    response['Content-Disposition'] = "attachment; filename*=utf-8''{}".format(escape_uri_path(document.filename))
    response['Access-Control-Expose-Headers'] = 'Content-Disposition'
    return response


@api_view(['GET'])
def download_delivery_document_signature(request):
    signature = gen_uuid(18)
    expires = 60 * 60
    cache.set(signature, True, expires)
    data = {
        'signature': signature,
        'expires': expires
    }
    return api_success(data)
