import uuid
import re
import time
import random
import string
import json
import logging
import math
from base64 import b64decode
from copy import deepcopy
from itertools import chain
from pprint import pprint

from django.views.decorators.cache import cache_page
from dateutil.relativedelta import relativedelta
from django.contrib.auth.models import Group
from django.contrib.auth import authenticate, login, logout
from django.core.files.base import ContentFile
from django.db.models.functions import TruncMonth
from django.http.response import JsonResponse
from django.db.models import Q, Count
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.contrib.auth.models import User
from django.utils.timezone import timedelta
from django.shortcuts import get_object_or_404
from django.contrib.auth import password_validation
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.core.cache import cache
from django.middleware import csrf
from django.db import transaction
from django.utils.decorators import method_decorator
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authtoken.views import ObtainAuthToken
from auth_top.models import TopToken
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
import requests
from pypinyin import lazy_pinyin

from clients.models import Lead
from farmbase.permissions_utils import func_perm_required
from gearfarm.utils.base64_to_image_file import base64_string_to_file
from farmbase.user_utils import get_user_view_projects, get_user_view_proposals, get_user_view_leads
from gearfarm.utils import farm_response
from gearfarm.utils.farm_response import api_success, api_bad_request, api_request_params_required, api_suspended, \
    api_error, build_pagination_response
from farmbase.users_undone_works_utils import *
from gearfarm.utils.decorators import request_params_required, request_data_fields_required
from farmbase.models import FunctionPermission, FunctionModule, Team, TeamUser
from farmbase.templatetags.mytags import user_leads_undone_work_count, pending_proposals_count, \
    user_proposals_undone_work_count, user_projects_job_position_needs_count, \
    user_projects_job_position_needs_add_candidate_count
from farmbase.serializers import FunctionPermissionSerializer, UserFunctionPermListSerializer, \
    FunctionModuleWithPermissionSerializer, FunctionModuleSerializer, CreateUserSerializer, \
    FunctionPermissionSimpleSerializer, FuncModuleWithPermsSerializer, UserWithProfileSerializer, \
    UserBasicSerializer, UserProfileSerializer, UserWithGroupSerializer, \
    UserWithFunctionPermissionSerializer, DocumentsSerializer, GroupSerializer, UserWithGitlabUserSerializer, \
    FuncPermWithGroupSerializer, ProfileSimpleSerializer, TeamSerializer, TeamUserSerializer, GroupWithUsersSerializer, \
    FuncModuleInitSerializer, FuncModuleInitWithGroupsSerializer
from farmbase.permissions_utils import has_function_perms, get_user_function_perms, \
    get_user_function_perm_codename_list, build_user_perm_data, has_function_perm
from farmbase.utils import get_active_users_by_function_perm, gen_uuid, get_phone_verification_code
from farmbase.models import Documents, Profile
from logs.models import Log
from notifications.tasks import send_feishu_message_to_individual
from projects.serializers import ProjectsPageSerializer
from farmbase.user_utils import get_user_projects
from proposals.serializers import ProposalsPageSerializer
from proposals.models import Proposal
from projects.models import Project
from tasks.models import Task
from tasks.serializers import TaskSerializer
from oauth.aliyun_client import AliyunApi
from farmbase.users_undone_works_utils import get_user_today_work_orders_tasks

PROPOSAL_STATUS_DICT = Proposal.PROPOSAL_STATUS_DICT


@api_view(["GET"])
def active_users(request):
    users = User.objects.filter(is_active=True)
    data = UserBasicSerializer(users, many=True).data
    data = sorted(data, key=lambda x: ''.join(lazy_pinyin(x['username'])), reverse=False)
    return api_success(data)


class UserList(APIView):
    def get(self, request, format=None):
        params = request.GET
        is_active = params.get('is_active', True)
        is_active = is_active in ['1', 1, True, 'True', 'true']

        group_name = params.get('group', None) if params.get('group', None) else params.get('groups', None)
        with_permissions = params.get('with_permissions', False) in ['1', 1, True, 'True', 'true']
        without_groups = params.get('without_groups', False) in ['1', 1, True, 'True', 'true']
        users = User.objects.filter(is_active=is_active)
        if group_name:
            group_list = re.sub(r'[;；,，]', ' ', group_name).split()
            users = users.filter(groups__name__in=group_list).distinct()

        ordering = params.get('ordering', 'username')
        if ordering and ordering != 'username':
            users.order_by(ordering)

        serializer = UserWithGroupSerializer(users, many=True)
        if without_groups:
            serializer = UserBasicSerializer(users, many=True)
        if with_permissions:
            serializer = UserWithFunctionPermissionSerializer(users, many=True)
        data = serializer.data
        if ordering == 'username':
            data = sorted(data, key=lambda x: ''.join(lazy_pinyin(x[ordering])), reverse=False)
        return api_success(data)

    def post(self, request):
        #
        # result, message, password = check_password_param(request.data)
        # if not result:
        #     return Response({'result': False, 'message': message})
        request.data['password'] = "Gear666888"
        groups = request.data.get('groups', None)
        if groups is not None:
            request.data['groups'] = Group.objects.filter(name__in=groups).values_list('id',
                                                                                       flat=True) if groups else []
        func_perms = request.data.get('func_perms', None)
        if func_perms is not None:
            request.data['func_perms'] = FunctionPermission.objects.filter(codename__in=func_perms).values_list('id',
                                                                                                                flat=True) if func_perms else []

        feishu_user_id = request.data.get('feishu_user_id', None)
        if feishu_user_id and Profile.objects.filter(feishu_user_id=feishu_user_id).exists():
            return farm_response.api_bad_request("该飞书已经被绑定")

        phone_number = request.data.get('phone_number', None)
        if not phone_number:
            return api_request_params_required('phone_number')
        if Profile.objects.filter(phone_number=phone_number).exists():
            return farm_response.api_bad_request("该手机号已经被绑定")

        request.data['is_active'] = True
        serializer = CreateUserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            if feishu_user_id:
                user.profile.feishu_user_id = feishu_user_id
            user.profile.phone_number = phone_number
            user.profile.save()

            # cancelled_permissions = request.data.get('cancelled_permissions', None)
            # if cancelled_permissions is not None:
            #     permissions = FunctionPermission.objects.filter(codename__in=cancelled_permissions)
            #     cancelled_permissions = [perm.codename for perm in permissions]
            #     cache.set('user-{}-cancelled-permissions'.format(user.id), cancelled_permissions, None)
            return Response({'result': True, 'data': serializer.data})
        return Response({'result': False, 'message': serializer.errors})


class UserDetail(APIView):
    def get(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        serializer = UserWithFunctionPermissionSerializer(user)
        return Response({'result': True, 'data': serializer.data})

    def post(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)

        groups = request.data.get('groups', None)
        if groups is not None:
            request.data['groups'] = Group.objects.filter(name__in=groups).values_list('id',
                                                                                       flat=True) if groups else []
        func_perms = request.data.get('func_perms', None)
        if func_perms is not None:
            request.data['func_perms'] = FunctionPermission.objects.filter(codename__in=func_perms).values_list('id',
                                                                                                                flat=True) if func_perms else []
        feishu_user_id = request.data.get('feishu_user_id', None)
        if feishu_user_id and Profile.objects.exclude(user_id=user.id).filter(feishu_user_id=feishu_user_id).exists():
            return farm_response.api_bad_request("该飞书已经被绑定")

        phone_number = request.data.get('phone_number', None)
        if not phone_number:
            return api_request_params_required('phone_number')
        if Profile.objects.exclude(user_id=user.id).filter(phone_number=phone_number).exists():
            return farm_response.api_bad_request("该手机号已经被绑定")

        serializer = CreateUserSerializer(user, request.data)
        if serializer.is_valid():
            serializer.save()
            if feishu_user_id:
                user.profile.feishu_user_id = feishu_user_id
            user.profile.phone_number = phone_number
            user.profile.save()
            # cancelled_permissions = request.data.get('cancelled_permissions', None)
            # if cancelled_permissions is not None:
            #     permissions = FunctionPermission.objects.filter(codename__in=cancelled_permissions)
            #     cancelled_permissions = [perm.codename for perm in permissions]
            #     cache.set('user-{}-cancelled-permissions'.format(user.id), cancelled_permissions, None)

            return Response({'result': True, 'data': serializer.data})
        return Response({'result': False, 'message': serializer.errors})


@api_view(["GET"])
def my_perm_data(request):
    user = request.user
    data = build_user_perm_data(user)
    return api_success(data)


@api_view(["GET"])
def my_view_multi_objs(request):
    '''
    其他
    项目（按照 我进行中的项目，其他人进行中的项目，已关闭的项目排序）
    需求（按照 我进行中的需求，其他人进行中的需求排序）
    '''
    user = request.user

    cache_key = 'user_{}_view_multi_objs'.format(user.id)
    cache_data = cache.get(cache_key, None)

    if cache_data:
        return api_success(cache_data)

    all_projects = False
    projects_dict = {}
    if has_function_perm(request.user, 'view_all_projects'):
        all_projects = True
    else:
        projects = get_user_view_projects(request.user)
        for p in projects:
            projects_dict[p.id] = {'id': p.id, 'name': p.name}

    all_proposals = False
    proposals_dict = {}
    if has_function_perm(user, 'view_all_proposals'):
        all_proposals = True
    else:
        proposals = get_user_view_proposals(request.user)
        for p in proposals:
            proposals_dict[p.id] = {'id': p.id, 'name': p.name}
    all_leads = False
    leads_dict = {}
    if has_function_perm(user, 'view_all_leads'):
        all_leads = True
    else:
        leads = get_user_view_leads(request.user)
        for p in leads:
            leads_dict[p.id] = {'id': p.id, 'name': p.name}
    data = {
        "all": {
            "project": all_projects,
            "proposal": all_proposals,
            "lead": all_leads
        },
        "projects_dict": projects_dict,
        "proposals_dict": proposals_dict,
        "leads_dict": leads_dict
    }
    cache.set(cache_key, data, 60 * 3)
    return api_success(data)


@api_view(["GET"])
def my_view_proposals_projects_perm_data(request):
    user_id = request.user.id
    '''
    其他
    项目（按照 我进行中的项目，其他人进行中的项目，已关闭的项目排序）
    需求（按照 我进行中的需求，其他人进行中的需求排序）
    '''
    projects = get_user_view_projects(request.user)
    proposals = get_user_view_proposals(request.user)
    projects_dict = {}
    for p in projects:
        projects_dict[p.id] = {'id': p.id, 'name': p.name,
                               'content_object': {'app_label': 'projects', 'model': 'project', 'object_id': p.id}}
    proposals_dict = {}
    for p in proposals:
        proposals_dict[p.id] = {'id': p.id, 'name': p.name,
                                'content_object': {'app_label': 'proposals', 'model': 'proposal', 'object_id': p.id}}
    # ongoing_leads = Lead.pending_leads()
    # my_ongoing_leads = ongoing_leads.filter(salesman_id=user_id)
    # other_ongoing_leads = ongoing_leads.difference(my_ongoing_leads)
    # leads_data = []
    # for p in chain(my_ongoing_leads, other_ongoing_leads):
    #     leads_data.append(
    #         {'id': p.id, 'name': p.name,
    #          'content_object': {'app_label': 'clients', 'model': 'lead', 'object_id': p.id}})
    data = {
        "projects_dict": projects_dict,
        "proposals_dict": proposals_dict,
    }
    return api_success(data)


class UserInfo(APIView):
    def get(self, request):
        serializer = UserWithProfileSerializer(request.user, many=False)
        return Response({'result': True, 'data': serializer.data})

    def post(self, request):
        email = request.data.get('email', None)
        phone_number = request.data.get('phone_number', None)
        email_signature = request.data.get('email_signature', None)
        avatar = request.data.get('avatar', None)

        if email is not None:
            request.user.email = email
            request.user.save()
        if phone_number is not None:
            request.user.profile.phone_number = phone_number
        if email_signature is not None:
            request.user.profile.email_signature = email_signature
        if avatar is not None:
            if 'data:' in avatar and ';base64,' in avatar:
                file = base64_string_to_file(avatar)
                if file:
                    request.user.profile.avatar = file
        request.user.profile.save()
        serializer = UserWithProfileSerializer(request.user)
        return Response({'result': True, 'data': serializer.data})


class GroupList(APIView):
    def get(self, request):
        groups = Group.objects.order_by('name')
        with_users = request.GET.get('with_users', 'true') in [1, '1', 'true', True, 'True']
        serializer = GroupWithUsersSerializer if with_users else GroupSerializer
        data = serializer(groups, many=True).data
        data = sorted(data, key=lambda x: ''.join(lazy_pinyin(x['name'])), reverse=False)
        return api_success(data)

    def post(self, request):
        serializer = GroupSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_success(data=serializer.data)
        return api_bad_request(message=str(serializer.errors))


class FunctionModuleList(APIView):
    def get(self, request):
        func_modules = FunctionModule.objects.all()
        data = FunctionModuleSerializer(func_modules, many=True).data
        return api_success(data=data)

    def post(self, request):
        serializer = FunctionModuleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_success(data=serializer.data)
        return api_bad_request(message=str(serializer.errors))


class FunctionModuleDetail(APIView):
    def get(self, request, id):
        func_module = get_object_or_404(FunctionModule, pk=id)
        data = FunctionModuleSerializer(func_module).data
        return api_success(data)

    def put(self, request, id):
        func_module = get_object_or_404(FunctionModule, pk=id)
        serializer = FunctionModuleSerializer(func_module, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return api_success(data=serializer.data)
        return api_bad_request(message=str(serializer.errors))

    def delete(self, request, id):
        func_module = get_object_or_404(FunctionModule, pk=id)
        if not request.user.is_superuser:
            return Response({'result': False, "message": "只要超级管理员有权限删除权限"})
        if func_module.func_perms.exists():
            return api_bad_request("该模块块下存在权限 不能删除")
        func_module.delete()
        return api_success()


class FunctionPermissionList(APIView):
    def get(self, request):
        func_modules = FunctionModule.objects.all()
        data = FunctionModuleWithPermissionSerializer(func_modules, many=True).data
        return api_success(data=data)

    def post(self, request):
        serializer = FunctionPermissionSerializer(data=request.data)
        if serializer.is_valid():
            func_perm = serializer.save()
            Log.build_create_object_log(request.user, func_perm, func_perm.module)
            return api_success(data=serializer.data)
        return api_bad_request(message=str(serializer.errors))


class UserFunctionPermissionList(APIView):
    def get(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        data = UserFunctionPermListSerializer(user).data
        return Response(data)

    def post(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        permissions = request.data.get('permissions', None)
        if permissions:
            func_perm = FunctionPermission.objects.filter(codename__in=permissions)
            user.func_perms.add(*func_perm)
            return Response({"result": True})
        else:
            return Response({"result": False, "message": "请提供权限codename列表"})


class FunctionPermissionDetail(APIView):
    def get(self, request, id):
        func_perm = get_object_or_404(FunctionPermission, pk=id)
        data = FunctionPermissionSerializer(func_perm).data
        return Response(data)

    def post(self, request, id):
        func_perm = get_object_or_404(FunctionPermission, pk=id)
        if 'name' not in request.data:
            request.data['name'] = func_perm.name
        if 'codename' not in request.data:
            request.data['codename'] = func_perm.codename
        if 'module' not in request.data:
            request.data['module'] = func_perm.module.id
        origin = deepcopy(func_perm)
        serializer = FunctionPermissionSerializer(func_perm, data=request.data)
        if serializer.is_valid():
            func_perm = serializer.save()
            Log.build_update_object_log(request.user, origin, func_perm)
            return Response({'result': True, "data": serializer.data})
        return Response({'result': False, "data": serializer.errors})

    def delete(self, request, id):
        func_perm = get_object_or_404(FunctionPermission, pk=id)
        if not request.user.is_superuser:
            return Response({'result': False, "message": "只要超级管理员有权限删除权限"})
        module = func_perm.module
        origin = deepcopy(func_perm)
        func_perm.delete()
        Log.build_delete_object_log(request.user, origin, related_object=module)
        return Response({"result": True})


class FarmAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = TopToken.get_or_create(user=user)
        return api_success(data={'token': token.key, 'user_type': token.user_type})


@api_view(['POST'])
def login_handle(request):
    if settings.PRODUCTION and 'dd_code' not in request.data.keys():
        return Response({'result': False, 'message': '验证码为必填项'})
    if not {'username', 'password'}.issubset(request.data.keys()):
        return Response({'result': False, 'message': '用户名、密码为必填项'})
    username = request.data.get('username')
    password = request.data.get('password')

    if settings.PRODUCTION:
        dd_code = request.data.get('dd_code')
        user = User.objects.filter(username=username).first()
        if user and not user.profile.feishu_user_id:
            pass
        elif dd_code == '149167':
            pass
        elif not cache.get(username) == dd_code:
            return Response({'result': False, 'message': '验证码错误，请重新获取'})

    user = authenticate(username=username, password=password)
    if user:
        if not user.is_active:
            return api_suspended()
        login(request, user)
        token, created = TopToken.get_or_create(user=user)
        return api_success(data={'token': token.key, 'user_type': token.user_type})
    return Response({'result': False, 'message': '登录失败，用户名或密码错误'})


@api_view(['POST'])
def logout_handle(request):
    logout(request)
    return api_success()


@api_view(['POST'])
def change_my_password(request):
    if not {'new_password1', 'new_password2'}.issubset(request.data.keys()):
        return api_bad_request(message='请提供完整参数new_password1, new_password2为必填项')
    new_password1 = request.data.get('new_password1')
    new_password2 = request.data.get('new_password2')
    if new_password1 and new_password2:
        if new_password1 != new_password2:
            return api_bad_request(message='两次新密码输入不一致')
        try:
            password_validation.validate_password(new_password2, request.user)
        except Exception as error:
            return api_error(message=error)
        request.user.set_password(new_password2)
        request.user.save()
        token, created = TopToken.get_or_create(user=user)
        return api_success(data={'token': token.key, 'user_type': token.user_type})
    return api_bad_request(message='请输入有效新密码')


@api_view(['GET'])
def user_ongoing_works(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    projects = Project.ongoing_projects()
    ongoing_projects = get_user_projects(user, projects, exclude_members=['bd']).order_by('created_at')
    ongoing_projects_data = ProjectsPageSerializer(ongoing_projects, many=True).data
    ongoing_proposals = Proposal.ongoing_proposals().filter(Q(pm_id=user_id) | Q(bd_id=user_id)).order_by(
        'created_at')
    ongoing_proposals_data = ProposalsPageSerializer(ongoing_proposals, many=True).data
    ongoing_tasks = Task.objects.filter(principal=user, done_at=None).order_by('expected_at')
    ongoing_tasks_data = TaskSerializer(ongoing_tasks, many=True).data

    return Response({'ongoing_projects': ongoing_projects_data, 'ongoing_proposals': ongoing_proposals_data,
                     'ongoing_tasks': ongoing_tasks_data})


@api_view(['GET'])
def perms_data(request):
    func_modules = FunctionModule.objects.all()
    func_perm_data = FuncModuleWithPermsSerializer(func_modules, many=True).data
    return Response({'result': True, "func_perm_data": func_perm_data})


@api_view(['GET'])
def func_perms_data(request):
    func_modules = FunctionModule.objects.all()
    func_perm_data = FuncModuleWithPermsSerializer(func_modules, many=True).data
    return Response({'result': True, "data": func_perm_data})


@api_view(['GET'])
def func_perms_init_data(request):
    serializer = FuncModuleInitSerializer
    with_groups = request.GET.get("with_groups", None) in ['1', True, 'True', 'true', 1]
    if with_groups:
        serializer = FuncModuleInitWithGroupsSerializer
    func_modules = FunctionModule.objects.all()
    data = serializer(func_modules, many=True).data
    return api_success(data)


@api_view(['GET'])
def func_perms_perms(request):
    func_modules = FunctionPermission.objects.all()
    func_perm_data = FuncPermWithGroupSerializer(func_modules, many=True).data
    return Response({'result': True, "data": func_perm_data})


class SpecialPermissionList(APIView):
    def get(self, request):
        if 'user' not in request.GET:
            return api_request_params_required('user')
        use_id = request.GET.get('user')
        user = get_object_or_404(User, pk=use_id)
        cache_key = 'user_{user_id}_special_permissions'.format(user_id=user.id)
        user_special_permissions = cache.get(cache_key, None)

        # 清理权限
        new_special_permissions = {}
        if user_special_permissions:
            for codename in user_special_permissions.keys():
                if has_function_perms(user, codename):
                    new_special_permissions[codename] = user_special_permissions[codename]

        if user_special_permissions:
            cache.set(cache_key, new_special_permissions, None)

        codename = request.GET.get('codename')
        data = new_special_permissions or None
        if new_special_permissions and codename:
            data = new_special_permissions.get(codename)
        return api_success(data=data)

    def post(self, request):
        if not set(['perms', 'user']).issubset(set(request.data.keys())):
            return api_request_params_required(['perms', 'user'])
        use_id = request.data['user']
        user = get_object_or_404(User, pk=use_id)
        if not user.is_active:
            return api_bad_request("所选用户已离职")

        perms = request.data['perms']
        cache_key = 'user_{user_id}_special_permissions'.format(user_id=user.id)
        user_special_permissions = cache.get(cache_key, {})
        if 'view_all_leads' in perms:
            codename = 'view_all_leads'
            params = request.data.get('view_all_leads_params', [])
            func_perm = FunctionPermission.objects.filter(codename=codename).first()
            if func_perm:
                user_special_permissions[codename] = {'codename': codename, 'name': func_perm.name, 'params': params}
                user.func_perms.add(func_perm)
        else:
            codename = 'view_all_leads'
            func_perm = FunctionPermission.objects.filter(codename=codename).first()
            if func_perm:
                user_special_permissions.pop(codename, None)
                user.func_perms.remove(func_perm)

        if 'close_lead_review' in perms:
            codename = 'close_lead_review'
            params = request.data.get('close_lead_review_users', [])
            func_perm = FunctionPermission.objects.filter(codename=codename).first()
            if func_perm:
                user_special_permissions[codename] = {'codename': codename, 'name': func_perm.name, 'users': params}
                user.func_perms.add(func_perm)
        else:
            codename = 'close_lead_review'
            func_perm = FunctionPermission.objects.filter(codename=codename).first()
            if func_perm:
                user_special_permissions.pop(codename, None)
                user.func_perms.remove(func_perm)

        cache.set(cache_key, user_special_permissions, None)
        return api_success()


@api_view(['GET'])
def groups_func_perms(request):
    group_ids = request.GET.get('groups', None)
    group_perms = []
    if group_ids:
        group_id_list = re.sub(r'[;；,，]', ' ', group_ids).split()
        group_id_list = [int(id) for id in group_id_list]
        groups = Group.objects.filter(pk__in=group_id_list)
        for group in groups:
            group_perms.extend(group.func_perms.values_list('id', flat=True))
        group_perms = set(group_perms)

    func_modules = FunctionModule.objects.all()
    data = FunctionModuleWithPermissionSerializer(func_modules, many=True).data
    for func_module in data:
        for perm in func_module['func_perms']:
            if perm['id'] in group_perms:
                perm['has_perm'] = True
            else:
                perm['has_perm'] = False
    return api_success(data=data)


@api_view(['POST'])
def func_perm_group_toggle(request, id):
    func_perm = get_object_or_404(FunctionPermission, pk=id)
    origin = deepcopy(func_perm)
    group_name = request.data.get('group_name', None)
    if group_name and Group.objects.filter(name=group_name).exists():
        group = Group.objects.get(name=group_name)
        if func_perm.groups.filter(name=group_name).exists():
            func_perm.groups.remove(group)
        else:
            func_perm.groups.add(group)
        Log.build_update_object_log(request.user, origin, func_perm)

    return api_success()


@api_view(['GET'])
def judge_user_func_perms(request, user_id):
    user = request.user
    if user_id:
        user = get_object_or_404(User, pk=user_id)
    permissions = request.GET.get('permissions', None)
    if permissions:
        permission_list = re.sub(r'[;；,，]', ' ', permissions).split()
        if has_function_perms(user, permission_list):
            return Response({'result': True, "message": "有权限"})
        else:
            return Response({'result': False, "message": "没有权限"})
    return Response({'result': False, "message": "缺少permissions参数"})


@api_view(['GET'])
def my_func_perms(request):
    func_modules = FunctionModule.objects.all()
    func_data = FunctionModuleSerializer(func_modules, many=True).data
    func_data_dict = {}
    for func in func_data:
        if func['codename'] not in func_data_dict:
            func_data_dict[func['codename']] = func
            func_data_dict[func['codename']]['func_perms'] = []
            func_data_dict[func['codename']]['has_perm'] = False

    func_perms = FunctionPermission.objects.all()
    func_perm_data = FunctionPermissionSimpleSerializer(func_perms, many=True).data
    func_perm_data_dict = {}
    for func_perm in func_perm_data:
        if func_perm['codename'] not in func_perm_data_dict:
            func_perm_data_dict[func_perm['codename']] = func_perm
            func_perm_data_dict[func_perm['codename']]['has_perm'] = False

    user_func_perms = get_user_function_perms(request.user)
    user_func_perms_data = FunctionPermissionSimpleSerializer(user_func_perms, many=True).data

    for func_perm in user_func_perms_data:
        module_codename = func_perm['module']['codename']
        if module_codename not in func_data_dict:
            func_data_dict[module_codename] = func_perm['module']
        func_data_dict[module_codename]['func_perms'].append(func_perm)
        if func_perm['codename'] in func_perm_data_dict:
            func_perm_data_dict[func_perm['codename']]['has_perm'] = True
    for module_codename in func_data_dict.keys():
        if func_data_dict[module_codename]['func_perms']:
            func_data_dict[module_codename]['has_perm'] = True

    return Response({'result': True, 'is_superuser': request.user.is_superuser, "func_module_data": func_data_dict,
                     'func_perm_data': func_perm_data_dict})


def check_password_param(request_params):
    password = ''
    if not {'password1', 'password2'}.issubset(request_params):
        return False, '请提供密码参数password1, password2为必填项', password
    if request_params.get('password1') != request_params.get('password2'):
        return False, '两次新密码输入不一致', password
    try:
        password_validation.validate_password(request_params.get('password1'))
    except Exception as error:
        return False, error, password
    else:
        password = request_params.get('password1')
    return True, '', password


@api_view(['GET'])
def my_undone_work_statistics(request):
    user = request.user
    # 待办事项
    tasks = get_user_today_undone_tasks(request.user, today=None, with_manage_project_tasks=False)
    # 甘特图任务
    gantt_tasks = get_user_today_undone_gantt_tasks(request.user, today=None, with_manage_project_tasks=False)
    # 未完成的Playbook任务
    playbook_tasks = get_user_today_undone_playbook_tasks(user, only_expected_date=True)
    # 工单
    work_orders = get_user_today_work_orders_tasks(user)
    # TPM检查点
    tpm_checkpoints = get_user_today_tpm_checkpoints_tasks(user)
    result_data = {
        "tasks_count": len(tasks),
        "gantt_tasks_count": len(gantt_tasks),
        "playbook_tasks_count": len(playbook_tasks),
        "tpm_checkpoints_count": len(tpm_checkpoints),
        'work_orders_count': len(work_orders),
    }
    result_data['total'] = sum(result_data.values())
    # 未完成的甘特图按照项目分组
    gantt_tasks_projects_dict = {}
    for task in gantt_tasks:
        project = task.gantt_chart.project
        if project.id not in gantt_tasks_projects_dict:
            gantt_tasks_projects_dict[project.id] = {'id': project.id, 'name': project.name,
                                                     'task_count': 0, 'roles': []}
        project_dict = gantt_tasks_projects_dict[project.id]
        project_dict['task_count'] = project_dict['task_count'] + 1
        role_data = {'id': task.role.id, 'name': task.role.name}
        if role_data not in project_dict['roles']:
            project_dict['roles'].append(role_data)
    # 未完成的playbook按照项目、需求分组
    playbook_project_dict = {}
    playbook_proposal_dict = {}
    playbook_check_items_count = 0
    for check_item in playbook_tasks:
        stage = check_item.check_group.stage
        content_type = stage.content_type
        content_type_model = content_type.model
        content_object = stage.content_object
        member_type = stage.member_type
        member = getattr(content_object, member_type, None)
        if member and member.id == user.id:
            playbook_check_items_count += 1
            if content_type_model == 'project':
                obj_key = content_object.id
                if obj_key not in playbook_project_dict:
                    playbook_project_dict[obj_key] = {'id': content_object.id, 'name': content_object.name,
                                                      'task_count': 0}
                playbook_project_dict[obj_key]['task_count'] = playbook_project_dict[obj_key]['task_count'] + 1
            if content_type_model == 'proposal':
                obj_key = '{model}-{id}'.format(model=content_type_model, id=content_object.id)
                if obj_key not in playbook_proposal_dict:
                    playbook_proposal_dict[obj_key] = {'id': content_object.id, 'name': content_object.name,
                                                       'task_count': 0}
                playbook_proposal_dict[obj_key]['task_count'] = playbook_proposal_dict[obj_key]['task_count'] + 1
    result_data['gantt_tasks_projects'] = list(gantt_tasks_projects_dict.values())
    result_data['playbook_projects'] = list(playbook_project_dict.values())
    result_data['playbook_proposals'] = list(playbook_proposal_dict.values())
    return api_success(result_data)


@api_view(['GET'])
def my_pages_undone_works(request):
    user = request.user
    result_data = dict()
    result_data['work_orders'] = {'page_code_name': 'work_orders',
                                  'page_name': '工单', 'undone_works_count': len(get_user_today_work_orders_tasks(user)),
                                  'undone_works_desc': ''}

    result_data['my_leads'] = {'page_code_name': 'my_leads',
                               'page_name': '我的线索', 'undone_works_count': 0,
                               'undone_works_desc': ''}
    result_data['my_leads']['undone_works_count'] = user_leads_undone_work_count(user)

    result_data['waiting_proposals'] = {'page_code_name': 'waiting_proposals',
                                        'page_name': '等待认领的需求', 'undone_works_count': 0,
                                        'undone_works_desc': ''}
    result_data['waiting_proposals']['undone_works_count'] = pending_proposals_count(user)

    result_data['my_proposals'] = {'page_code_name': 'my_proposals',
                                   'page_name': '我的需求', 'undone_works_count': 0,
                                   'undone_works_desc': ''}
    result_data['my_proposals']['undone_works_count'] = user_proposals_undone_work_count(user)

    result_data['tpm_board'] = {'page_code_name': 'tpm_board',
                                'page_name': 'TPM看板', 'undone_works_count': 0,
                                'undone_works_desc': 'TPM项目检查点数量'}
    result_data['tpm_board']['undone_works_count'] = len(get_user_today_tpm_checkpoints_tasks(user))

    result_data['my_position_needs'] = {'page_code_name': 'my_position_needs',
                                        'page_name': '我的工程师需求', 'undone_works_count': 0,
                                        'undone_works_desc': ''}
    result_data['my_position_needs']['undone_works_count'] = user_projects_job_position_needs_count(user)

    result_data['projects_position_needs'] = {'page_code_name': 'projects_position_needs',
                                              'page_name': '项目工程师需求', 'undone_works_count': 0,
                                              'undone_works_desc': ''}
    result_data['projects_position_needs']['undone_works_count'] = user_projects_job_position_needs_add_candidate_count(
        user)

    result_data['developers_regular_contracts'] = {'page_code_name': 'developers_regular_contracts',
                                                   'page_name': '固定工程师合同', 'undone_works_count': 0,
                                                   'undone_works_desc': ''}
    result_data['developers_regular_contracts'][
        'undone_works_count'] = get_user_developers_regular_contracts_undone_work_count(user)
    return api_success(data=result_data)


@api_view(['POST'])
def change_user_capacity(request):
    username = request.data.get('username', None)
    project_capacity = request.data.get('project_capacity', None)
    if not all([username, project_capacity]):
        return Response({'result': False, 'message': '缺少有效的username、project_capacity参数'})
    current_user = get_object_or_404(User, username=username)
    current_user.profile.project_capacity = int(project_capacity)
    current_user.profile.save()
    return Response({'result': True})


@api_view(['GET'])
def phone_code(request):
    phone = request.GET.get('phone', None)
    if phone:
        user = User.objects.filter(profile__phone_number=phone).first()
        if not user:
            return api_bad_request(message="该手机号未绑定账户")

        if settings.DEVELOPMENT:
            code = settings.DEVELOPMENT_DD_CODE
            cache.set('user-{}-code'.format(user.id), {'code': code, 'time': timezone.now()}, 60 * 10)
            return api_success('测试环境验证码:{}'.format(code))
        code_data = cache.get('user-{}-code'.format(user.id), None)
        if code_data and code_data['time'] > timezone.now() - timedelta(minutes=1, seconds=30):
            return api_bad_request('不可频繁发送')

        if not user.is_active:
            return api_suspended()
        code = get_phone_verification_code()
        aliyun_client = AliyunApi(access_key_id=settings.ALIYUN_ACCESS_KEY_ID,
                                  access_key_secret=settings.ALIYUN_ACCESS_KEY_SECRET)
        aliyun_client.send_login_check_code_sms(phone, code, '【齿轮易创-Farm】')
        if settings.PRODUCTION:
            feishu_user_id = user.profile.feishu_user_id
            if feishu_user_id:
                if feishu_user_id:
                    send_feishu_message_to_individual(feishu_user_id, "你在登录Farm, 验证码为:" + code)
        cache.set('user-{}-code'.format(user.id), {'code': code, 'time': timezone.now()}, 60 * 10)
        return api_success('短信发送成功')
    return api_bad_request(message="手机号必填")


@api_view(['POST'])
def phone_login(request):
    if not {'phone', 'code'}.issubset(request.data.keys()):
        return api_bad_request(message='手机号、验证码为必填项')
    phone = request.data.get('phone')
    code = request.data.get('code')

    user = User.objects.filter(profile__phone_number=phone).first()
    if not user:
        return api_bad_request(message="该手机号未绑定账户")
    if not user.is_active:
        return api_suspended()

    if not settings.PRODUCTION and code == '666888':
        pass
    else:
        code_data = cache.get('user-{}-code'.format(user.id), None)
        if not code_data:
            return api_bad_request(message='验证码无效，请重新获取验证码')
        cache_code = code_data['code']
        if not str(cache_code) == str(code):
            return api_bad_request(message='验证码错误')
    login(request, user)
    token, created = TopToken.get_or_create(user=user)
    top_user = token.top_user
    data = {'token': token.key, 'user_type': token.user_type, 'user_info': top_user.user_info()}
    return api_success(data=data)


@csrf_exempt
def user_token_check(request):
    if request.method != 'POST':
        return JsonResponse({'result': False, 'message': '只允许POST方式'})
    # 尝试Token认证 拿到用户
    request_body = deepcopy(request.body)
    if not isinstance(request_body, str):
        try:
            request_body = request_body.decode()
        except:
            pass
    request_data = json.loads(request_body)
    if request_data and request_data.get('token', None):
        token = request_data['token']
        user_token = TopToken.objects.filter(key=token)
        if user_token.exists():
            return api_success()
        else:
            return farm_response.api_invalid_authentication_key()
    else:
        return farm_response.api_request_params_required('token')


@api_view(['GET'])
def get_csrftoken(request):
    csrftoken = csrf.get_token(request)
    return Response({'result': True, 'csrftoken': csrftoken})


@api_view(['POST'])
def impersonate_auth(request):
    if not request.user.is_superuser:
        return Response({'result': False, 'message': "无权限"}, status=status.HTTP_403_FORBIDDEN)
    impersonator_username = request.data.get('impersonator', '')
    if impersonator_username and User.objects.filter(username=impersonator_username, is_active=True).exists():
        key = "{superuser}-impersonator".format(superuser=request.user.username)
        cache.set(key, impersonator_username, 60 * 20)
        return Response({'result': True})
    return Response({'result': False, 'message': "模拟用户不存在"})


@api_view(['POST'])
def impersonate_auth_exit(request):
    if not request.user.is_superuser:
        return Response({'result': False, 'message': "无权限"}, status=status.HTTP_403_FORBIDDEN)
    key = "{superuser}-impersonator".format(superuser=request.user.username)
    cache.delete(key)
    return Response({'result': True})


@api_view(['GET'])
def users_gitlab_committers(request):
    users = User.objects.filter(is_active=True)
    users_committers = cache.get('farm-users-committers', {})
    users_data = UserBasicSerializer(users, many=True).data
    for user_data in users_data:
        user_data['committers'] = []
        if user_data['id'] in users_committers:
            user_data['committers'] = users_committers[user_data['id']].get('committers', [])
    return Response({"result": True, "data": users_data})


class UserCommitters(APIView):
    def get(self, request, user_id, format=None):
        user = get_object_or_404(User, pk=user_id)
        users_committers = cache.get('farm-users-committers', {})
        user_data = UserBasicSerializer(user).data
        user_data['committers'] = []
        if user.id in users_committers:
            user_data['committers'] = users_committers[user.id].get('committers', [])
        return Response({"result": True, "data": user_data})

    def post(self, request, user_id, format=None):
        user = get_object_or_404(User, pk=user_id)
        committers = request.data.get('committers', [])
        users_committers = cache.get('farm-users-committers', {})
        user_data = {'id': user.id, 'username': user.id, 'committers': committers}
        users_committers[user.id] = user_data
        cache.set('farm-users-committers', users_committers, None)
        return Response({"result": True, "data": user_data})


@api_view(['GET'])
def get_short_url(request):
    suo_key = '5e5cb97f9f95942621c61eb7@42b5d37036df616c90e876243dba50f9'
    suo_url = 'http://suo.nz/api.php'
    url = request.GET.get('url')
    res = requests.get(suo_url, params={'url': url, 'key': suo_key, 'format': 'json', 'expireDate': "2100-01-01"})
    if res.status_code == 200:
        return api_success(data=res.json())
    return api_bad_request()


@api_view(['GET'])
@request_params_required('permission')
def get_users_by_func_perm(request):
    permission = request.GET.get('permission', '')
    exclude_permission = request.GET.get('exclude_permission', '')
    users = get_active_users_by_function_perm(permission)
    if exclude_permission:
        exclude_users = get_active_users_by_function_perm(exclude_permission)
    users = users.difference(exclude_users)
    data = UserBasicSerializer(users, many=True).data

    return api_success(data=data)


@api_view(['GET'])
def my_one_time_authentication_key(request):
    user = request.user
    authentication_key = 'user{}{}'.format(user.id, gen_uuid(8))
    key_data = {'authentication_key': authentication_key,
                'created_at': timezone.now().strftime(settings.DATETIME_FORMAT), 'expired_seconds': 3600,
                'user': {'id': user.id, 'username': user.username}}
    cache.set(authentication_key, key_data, 3600)
    return api_success(data=key_data)


@api_view(['GET'])
def data_migrate(request):
    pass
    return api_success()


@api_view(["GET"])
def guidance_status(request):
    guidance_users = cache.get('guidance_users', set())
    need_guidance = True
    if request.user.id in guidance_users:
        need_guidance = False
    return api_success({'need_guidance': need_guidance})


@api_view(["POST"])
def guidance_done(request):
    guidance_users = cache.get('guidance_users', set())
    guidance_users.add(request.user.id)
    cache.set('guidance_users', guidance_users, None)
    return api_success()


class TeamList(APIView):
    def get(self, request, format=None):
        search = request.GET.get('search', '')
        page = request.GET.get('page', '')
        page_size = request.GET.get('page_size', '')
        teams = Team.objects.all()
        ordering = request.GET.get('ordering', 'created_at')
        teams.order_by(ordering)
        if search:
            teams = teams.filter(Q(name__icontains=search) | Q(leader__name__icontains=search))

        return build_pagination_response(request, teams, TeamSerializer)

    def post(self, request, format=None):
        serializer = TeamSerializer(data=request.data)
        members = request.data.get('members', None)
        if serializer.is_valid():
            team = serializer.save()
            if members is not None:
                for member_id in members:
                    user = User.objects.filter(is_active=True, pk=member_id).first()
                    if user:
                        TeamUser.objects.get_or_create(team=team, user=user)
            team_data = TeamSerializer(team).data
            return Response(team_data)
        return api_bad_request(serializer.errors)


class TeamDetail(APIView):
    def get(self, request, team_id, format=None):
        role = get_object_or_404(Team, pk=team_id)
        data = TeamSerializer(role).data
        return api_success(data=data)

    def put(self, request, team_id, format=None):
        team = get_object_or_404(Team, pk=team_id)
        serializer = TeamSerializer(team, data=request.data)
        members = request.data.get('members', None)
        if serializer.is_valid():
            team = serializer.save()
            if members is not None:
                team.team_users.all().delete()
                for member_id in members:
                    user = User.objects.filter(is_active=True, pk=member_id).first()
                    if user:
                        TeamUser.objects.get_or_create(team=team, user=user)
            team_data = TeamSerializer(team).data
            return Response(team_data)
        return api_bad_request(serializer.errors)

    def delete(self, request, team_id, format=None):
        team = get_object_or_404(Team, pk=team_id)
        team.delete()
        return api_success()


@method_decorator(func_perm_required('manage_quip_shared_documents'), name='post')
@method_decorator(request_data_fields_required('documents_data'), name='post')
class DocumentList(APIView):
    def get(self, request, is_mine):
        user = request.user
        documents = Documents.objects.order_by('index')
        if is_mine:
            if not user.is_superuser:
                documents = Documents.objects.filter(
                    Q(groups__in=user.groups.all()) | Q(groups__isnull=True)).distinct()
        data = DocumentsSerializer(documents, many=True).data
        return api_success(data)

    @transaction.atomic
    def post(self, request, is_mine=False):
        previous_data_list = list(Documents.objects.all().values_list('id', flat=True))
        savepoint = transaction.savepoint()
        try:
            documents_data = request.data.get('documents_data')
            for index, document_data in enumerate(documents_data):
                document = Documents.objects.create(title=document_data["title"], url=document_data["url"], index=index)
                group_list = document_data["group_list"]
                if group_list:
                    groups = Group.objects.filter(name__in=document_data["group_list"])
                    document.groups.add(*groups)
        except Exception as e:
            log = logging.getLogger()
            log.info(e)
            transaction.savepoint_rollback(savepoint)
            return api_bad_request(e)
        else:
            Documents.objects.filter(pk__in=previous_data_list).delete()
        return api_success()


@api_view(["GET"])
def get_new_demand_chart_data(request):
    first_day = datetime.today().replace(day=1, hour=0, minute=0, second=0)
    six_month = first_day - relativedelta(months=5)
    proposal_history = Proposal.objects.filter(created_at__gte=six_month).annotate(
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
    data_list = []
    for index, date in enumerate(trend_months):
        a = {date: trend_counts[index]}
        data_list.append(a)
    return api_success(data_list)


@api_view(["GET"])
def get_recent_30_data(request):
    now = datetime.now()
    current_month_proposals = Proposal.objects.filter(created_at__year=timezone.now().year,
                                                      created_at__month=timezone.now().month).count()
    current_month_leads = Lead.objects.filter(created_at__year=timezone.now().year,
                                              created_at__month=timezone.now().month).count()
    last_month = now - timedelta(days=30)
    p30_leads = Lead.objects.filter(created_at__gte=last_month).count()
    p30_total = Proposal.objects.filter(created_at__gte=last_month).count()
    p30_contacts = Proposal.objects.filter(contact_at__gte=last_month)
    p30_reports = Proposal.objects.filter(report_at__gte=last_month)
    p30_noreport = Proposal.objects.filter(closed_at__gte=last_month, report_at__isnull=True).count()
    p30_ontime_contact = 0

    for p in p30_contacts:
        if (p.contact_at - p.created_at).total_seconds() <= 86400:
            p30_ontime_contact += 1
    data = {'current_month_proposals': current_month_proposals,
            'current_month_leads': current_month_leads,
            'p30_leads': p30_leads,
            'p30_total': p30_total,
            'p30_contacts': p30_contacts.count(),
            'p30_reports': p30_reports.count(),
            'p30_noreport': p30_noreport,
            'p30_ontime_contact': p30_ontime_contact}
    return api_success(data=data)


def get_bd_stats(bd):
    now = datetime.now()
    last_month = now - timedelta(days=30)
    last_week = now - timedelta(days=7)
    p30_contacts = Proposal.objects.filter(contact_at__gte=last_month)
    result = {}
    result['name'] = bd.username
    result['current_leads'] = Lead.objects.filter(status='contact', salesman_id=bd.id).count()
    result['current_proposals'] = Proposal.ongoing_proposals().filter(bd_id=bd.id).count()
    result['last_week_submitted_leads'] = Lead.objects.filter(creator_id=bd.id, created_at__gte=last_week).count()
    result['last_week_submitted'] = Proposal.objects.filter(submitter_id=bd.id, created_at__gte=last_week).count()
    result['last_month_submitted'] = Proposal.objects.filter(submitter_id=bd.id, created_at__gte=last_month).count()
    result['last_month_success'] = Proposal.deal_proposals().filter(submitter_id=bd.id,
                                                                    closed_at__gte=last_month).count()

    proposals = p30_contacts.filter(bd_id=bd.id)
    result['total_contact'] = proposals.count()
    result['ontime_contact'] = 0
    for p in proposals:
        if (p.contact_at - p.created_at).total_seconds() <= 86400:
            result['ontime_contact'] += 1
    return result


@api_view(["GET"])
def get_bds_data(request):
    bds = User.objects.filter(groups__name='BD', is_active=True).all()
    bds_stats = [get_bd_stats(bd) for bd in bds]
    return api_success(data=bds_stats)


def get_pm_stats(pm):
    now = datetime.now()
    last_month = now - timedelta(days=30)
    last_week = now - timedelta(days=7)
    p30_reports = Proposal.objects.filter(report_at__gte=last_month)
    result = {}
    result['name'] = pm.username
    result['current_projects'] = Project.ongoing_projects().filter(manager_id=pm.id).count()
    result['open_proposals'] = Proposal.objects.filter(pm_id=pm.id, closed_at=None).count()

    result['recently_closed_proposals'] = Proposal.objects.filter(pm_id=pm.id, closed_at__gte=last_week).exclude(
        closed_at=None).count()

    prd_projects = []
    ongoing_projects = Project.ongoing_projects().filter(product_manager_id=pm.id)
    for project in ongoing_projects:
        if project.current_stages.filter(stage_type="prd").exists():
            prd_projects.append(project)
    result['prd_projects'] = len(prd_projects)

    result['total_report'] = p30_reports.filter(pm_id=pm.id).count()

    return result


@api_view(["GET"])
def get_pms_data(request):
    pms = User.objects.filter(groups__name='产品经理', is_active=True).all()
    pms_stats = [get_pm_stats(pm) for pm in pms]
    return api_success(data=pms_stats)


@api_view(["GET"])
def capacity(request):
    data = {}
    ongoing_projects = Project.ongoing_projects()

    status_project_dict = {}
    for status in Project.PROJECT_STATUS_DICT.keys():
        if status != Project.PROJECT_STATUS_DICT['completion']['code']:
            status_project_dict[status] = []
    for project in ongoing_projects:
        project_stages = project.current_stages
        for stage in project_stages:
            status_project_dict[stage.stage_type].append(project)
    status_count_dict = {}
    for status, status_projects in status_project_dict.items():
        status_count_dict[status] = len(status_projects)

    data['total'] = ongoing_projects.count()
    data['count'] = status_count_dict

    design_projects = status_project_dict.get(Project.PROJECT_STATUS_DICT['design']['code'], [])
    development_projects = status_project_dict.get(Project.PROJECT_STATUS_DICT['development']['code'], [])
    test_projects = status_project_dict.get(Project.PROJECT_STATUS_DICT['test']['code'], [])
    acceptance_projects = status_project_dict.get(Project.PROJECT_STATUS_DICT['acceptance']['code'], [])

    # 设计数据
    designer_list = User.objects.filter(groups__name=settings.GROUP_NAME_DICT["designer"], is_active=True)
    designer_name_list = set(designer_list.values_list('username', flat=True))
    designer_data = get_users_base_capacity_data(designer_list, settings.DESIGNER_PROJECT_CAPACITY)
    for project in design_projects:
        designer = project.designer
        if designer:
            designer_name = designer.username
            if designer_name not in designer_name_list:
                continue
            if designer_name not in designer_data:
                designer_data[designer_name] = get_user_capacity_data(designer)
            designer_data[designer_name]['number'] += 1
        else:
            for job in project.job_positions.all():
                developer = job.developer
                if developer and developer.name in designer_name_list:
                    developer_name = developer.name
                    designer_data[developer_name]['number'] += 1
    data['designer_data'] = get_users_statistics_capacity_data(designer_data)

    # 项目经理数据
    project_manager_list = User.objects.filter(groups__name=settings.GROUP_NAME_DICT["project_manager"], is_active=True)
    project_managers_name_list = set(project_manager_list.values_list('username', flat=True))
    project_manager_data = get_users_base_capacity_data(project_manager_list, settings.PROJECT_MANAGER_PROJECT_CAPACITY)
    for project in ongoing_projects:
        manager = project.manager
        if manager:
            manager_name = manager.username
            if manager_name not in project_managers_name_list:
                continue
            if manager_name not in project_manager_data:
                project_manager_data[manager_name] = get_user_capacity_data(manager)
            if project.current_stages.filter(stage_type__in=["acceptance", "development"]).exists():
                project_manager_data[manager_name]['number'] += 0.5
            else:
                project_manager_data[manager_name]['number'] += 1
    data['project_manager_data'] = get_users_statistics_capacity_data(project_manager_data)

    # 产品经理数据
    pm_list = User.objects.filter(groups__name=settings.GROUP_NAME_DICT["pm"], is_active=True)
    learning_pm_list = User.objects.exclude(groups__name=settings.GROUP_NAME_DICT["pm"]).filter(
        groups__name=settings.GROUP_NAME_DICT["learning_pm"], is_active=True)
    pms_name_list = set(pm_list.values_list('username', flat=True)) | set(
        learning_pm_list.values_list('username', flat=True))

    pm_data = get_users_base_capacity_data(pm_list, settings.PM_PROJECT_CAPACITY)
    learning_pm_data = get_users_base_capacity_data(learning_pm_list, settings.LEARNING_PM_PROJECT_CAPACITY)

    pms_data = dict(pm_data, **learning_pm_data)
    for project in ongoing_projects:
        manager = project.product_manager
        if manager:
            manager_name = manager.username
            if manager_name not in pms_name_list:
                continue
            if manager_name not in pms_data:
                pms_data[manager_name] = get_user_capacity_data(manager)
            if project.current_stages.filter(stage_type__in=["acceptance", "development"]).exists():
                pms_data[manager_name]['number'] += 0.5
            else:
                pms_data[manager_name]['number'] += 1
    data['pm_data'] = get_users_statistics_capacity_data(pms_data)

    # TPM数据
    tpm_groups = [settings.GROUP_NAME_DICT["tpm"], settings.GROUP_NAME_DICT['remote_tpm']]
    tpm_list = User.objects.filter(groups__name__in=tpm_groups, is_active=True)
    tpm_name_list = set(tpm_list.values_list('username', flat=True))
    tpm_data = get_users_base_capacity_data(tpm_list, settings.TPM_PROJECT_CAPACITY)

    for project in chain(development_projects, test_projects, acceptance_projects):
        tpm = project.tpm
        if tpm:
            tpm_name = tpm.username
            if tpm_name not in tpm_name_list:
                continue
            if tpm_name not in tpm_data:
                tpm_data[tpm_name] = get_user_capacity_data(tpm)
            if project.current_stages.filter(stage_type="test").exists():
                tpm_data[tpm_name]['number'] += 0.5
            else:
                tpm_data[tpm_name]['number'] += 1

    data['tpm_data'] = get_users_statistics_capacity_data(tpm_data)

    # 测试数据
    test_list = User.objects.filter(groups__name=settings.GROUP_NAME_DICT["test"], is_active=True)
    test_name_list = set(test_list.values_list('username', flat=True))
    test_data = get_users_base_capacity_data(test_list, settings.TEST_PROJECT_CAPACITY)

    for project in test_projects:
        # 【test】
        project_tests = project.tests.all()
        for test in project_tests:
            test_name = test.username
            if test_name not in test_name_list:
                continue
            if test_name not in test_data:
                test_data[test_name] = get_user_capacity_data(test)
            test_data[test_name]['number'] += 1

    data['test_data'] = get_users_statistics_capacity_data(test_data)

    return api_success(data=data)


def get_user_capacity_data(user):
    profile = user.profile
    avatar_url = profile.avatar.url if profile.avatar else None
    data = {'name': user.username, 'number': 0, 'project_capacity': profile.project_capacity, 'avatar_url': avatar_url,
            'avatar_color': profile.avatar_color}
    return data


def get_users_base_capacity_data(user_list, default_capacity):
    capacity_data = {}
    for user in user_list:
        username = user.username
        if not user.profile.project_capacity:
            user.profile.project_capacity = default_capacity
            user.profile.save()
        if user not in capacity_data:
            capacity_data[username] = get_user_capacity_data(user)
    return capacity_data


def get_users_statistics_capacity_data(base_data):
    for key in base_data.keys():
        base_data[key]['number'] = math.ceil(base_data[key]['number'])
    capacity_data = {}
    capacity_data['list'] = list(base_data.values())
    capacity_data['total_project'] = sum([item['number'] for item in base_data.values()])
    capacity_data['total_capacity'] = sum([item['project_capacity'] for item in base_data.values()])
    return capacity_data
