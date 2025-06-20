from base64 import b64decode
from copy import deepcopy
import logging
import uuid
import mimetypes
import re
from wsgiref.util import FileWrapper
import mimetypes
import os
import posixpath
import re
import stat

from django.db import transaction
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from django.http import FileResponse
from django.utils.encoding import escape_uri_path
from django.db.models import Sum, IntegerField, When, Case, Q
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status as response_status
from rest_framework.pagination import PageNumberPagination
from pypinyin import lazy_pinyin

from gearfarm.utils.common_utils import get_file_suffix
from gearfarm.utils.base64_to_image_file import base64_string_to_file
from farmbase.permissions_utils import has_function_perm, has_any_function_perms, has_function_perms, \
    func_perm_required, func_perm_any_required
from farmbase.utils import gen_uuid
from gearfarm.utils import farm_response
from gearfarm.utils.farm_response import api_success, api_bad_request, api_permissions_required, \
    build_pagination_queryset_data
from gearfarm.utils.decorators import request_data_fields_required
from farmbase.permissions_utils import func_perm_required
from developers.models import Developer, Role, Document, DocumentReadLog, DocumentVersion

from developers.utils import has_cooperation_with_developer_at_present
from developers.serializers import DeveloperCreateSerializer, DeveloperListSerializer, RoleSerializer, \
    DeveloperSimpleSerializer, \
    DeveloperDetailSerializer, DeveloperStatusSerializer, DeveloperExportSerializer, DocumentListSerializer, \
    DocumentEditSerializer, DocumentSyncLogSerializer, DocumentReadLogSerializer, DocumentVersionSerializer, \
    DeveloperVerySimpleSerializer, DocumentVersionSimpleSerializer, DocumentDetailSerializer
from developers.tasks import update_all_developers_cache_data, update_developer_cache_data, \
    build_document_version_clean_html, get_developer_quip_documents, rebuild_developer_quip_documents, \
    rebuild_ongoing_projects_dev_docs_checkpoints_status, send_project_developer_daily_works_to_manager_and_tpm, \
    send_project_developer_daily_works_to_developers, DEVELOPERS_EXTRA_CACHE_KEY, update_active_developers_cache_data
from geargitlab.gitlab_client import GitlabClient
from geargitlab.tasks import crawl_gitlab_user_data, get_gitlab_user_data
from logs.models import Log
from projects.serializers import JobPositionCandidateSerializer, JobPositionCandidateViewSerializer
from oauth.quip_utils import get_folders_docs, get_quip_doc_html, get_quip_doc
from projects.models import Project

gitlab_client = GitlabClient()
logger = logging.getLogger()


class developer_rate(APIView):
    def get(self, request, developer_id, format=None):
        get_object_or_404(Developer, id=developer_id)
        developers_data = cache.get(DEVELOPERS_EXTRA_CACHE_KEY, {})
        if not developers_data or developer_id not in developers_data:
            developer_cache_data = developers_data.get(developer_id, {})
        else:
            developer_cache_data = developers_data.get(developer_id, {})
        data = developer_cache_data['star_rating']
        return Response(data)


@api_view(['GET'])
def active_developers(request):
    developers = Developer.active_developers()
    data = DeveloperSimpleSerializer(developers, many=True).data
    data = sorted(data, key=lambda x: ''.join(lazy_pinyin(x['name'])), reverse=False)
    return api_success(data)


class DeveloperList(APIView):
    # @method_decorator(cache_page(60 * 5))
    def get(self, request):
        params = request.GET
        normal = params.get("normal", True) in ['1', 'true', 'True', 1, True]
        status = params.get("status", None)
        fulltime_status = params.get("fulltime_status", None)
        search_value = request.GET.get('search_value', None)

        roles = params.get("roles", None)
        development_languages = params.get("development_languages", None)
        frameworks = params.get("frameworks", None)
        order_by = params.get("order_by", None)
        order_dir = params.get("order_dir", None)

        # 状态查询
        developers = Developer.objects.all()
        developers = developers.exclude(status='0') if normal else developers.filter(status='0')
        if normal and status:
            developers = Developer.objects.filter(status=status)
        if fulltime_status:
            fulltime_status_list = fulltime_status.split(',')
            developers = developers.filter(fulltime_status__in=fulltime_status_list)
        # 文本检索
        if search_value:
            developers = developers.filter(Q(name__icontains=search_value) | Q(phone__icontains=search_value))
        # 标签查询
        if roles:
            roles_list = roles.split(',')
            developers = developers.filter(roles__in=roles_list)
        if development_languages:
            development_language_list = development_languages.split(',')
            developers = developers.filter(development_languages__in=development_language_list)
        if frameworks:
            framework_list = frameworks.split(',')
            developers = developers.filter(frameworks__in=framework_list)

        developers_cache_data = cache.get(DEVELOPERS_EXTRA_CACHE_KEY, {})
        if not developers_cache_data:
            developers_cache_data = update_all_developers_cache_data()
        developers = developers.distinct()

        # 多种字段排序的处理：字段 + 技术
        # 排序：可分配性、评分、加入时间、 项目数、姓名："employability", "average_star_rating"，"created_at"，"project_total"，"name"
        # 其中可分配性为组合排序：可分配值、进行中项目数(越小越可分配)、最近完成项目完成时间(越小越可分配)、评分(越大越可分配)、参与的项目总数(越大越可分配)
        #  employability, -active_projects_len, -done_at_num, star_rating, project_total
        def order_by_employability_key(obj):
            employability_group = developers_cache_data.get(obj.id, {}).get('employability_group', [])
            return employability_group

        if order_by and order_dir:
            reverse = order_dir == 'desc'
            order_by = 'name_pinyin' if order_by == 'name' else order_by
            if order_by == 'employability':
                developers = sorted(developers, key=order_by_employability_key, reverse=reverse)
            if order_by in ['name_pinyin', 'created_at']:
                order_by = '-' + order_by if reverse else order_by
                developers = developers.order_by(order_by)
            else:
                developers = sorted(developers, key=lambda x: getattr(x, order_by), reverse=reverse)

        data, headers = build_pagination_queryset_data(request, developers, DeveloperListSerializer)
        gitlab_users = cache.get('gitlab-users', {})
        for developer in data:
            developer_id = developer['id']
            developer_cache_data = developers_cache_data.get(developer_id, {})
            if not developer_cache_data:
                developer_cache_data = update_developer_cache_data(developer_id)
            # 评分
            developer['star_rating'] = developer_cache_data['star_rating']
            # 合作伙伴
            developer['partners'] = developer_cache_data['partners']
            # 绑定的gitlab账户
            developer['gitlab_user'] = None
            gitlab_user_id = developer['gitlab_user_id']
            if gitlab_user_id:
                developer['gitlab_user'] = gitlab_users.get(gitlab_user_id) or get_gitlab_user_data(gitlab_user_id)

        if not cache.get("active_developers_cache_updated", False):
            update_active_developers_cache_data.delay()
            cache.set("active_developers_cache_updated", True, 60 * 15)
        return api_success(data, headers=headers)

    @transaction.atomic
    def post(self, request):
        request_data = deepcopy(request.data)
        phone = request_data.get('phone', None)

        if phone:
            existed_developer = Developer.objects.filter(phone=phone).first()
            if existed_developer:
                return api_bad_request("手机号已被{}绑定".format(existed_developer.name))

        avatar_string = request_data.get('avatar', None)
        development_languages = request_data.get("development_languages", None)
        frameworks = request_data.get("frameworks", None)
        front_side_of_id_card_string = request.data.get('front_side_of_id_card', None)
        back_side_of_id_card_string = request.data.get('back_side_of_id_card', None)

        avatar_file = base64_string_to_file(avatar_string)
        if avatar_file:
            request_data["avatar"] = avatar_file
        else:
            request_data.pop('avatar', None)

        front_side_of_id_card_file = base64_string_to_file(front_side_of_id_card_string)
        if front_side_of_id_card_file:
            request_data["front_side_of_id_card"] = front_side_of_id_card_file
        else:
            request_data.pop('front_side_of_id_card', None)

        back_side_of_id_card_file = base64_string_to_file(back_side_of_id_card_string)
        if back_side_of_id_card_file:
            request_data["back_side_of_id_card"] = back_side_of_id_card_file
        else:
            request_data.pop('back_side_of_id_card', None)

        serializer = DeveloperCreateSerializer(data=request_data)
        if serializer.is_valid():
            savepoint = transaction.savepoint()
            try:
                developer = serializer.save()
                if development_languages:
                    developer.development_languages.add(*development_languages)
                if frameworks:
                    developer.frameworks.add(*frameworks)
            except Exception as e:
                logger.error(e)
                transaction.savepoint_rollback(savepoint)
                raise
            else:
                Log.build_create_object_log(request.user, developer)
                serializer = DeveloperSimpleSerializer(developer)
                return Response({"result": True, "data": serializer.data})
        return Response({"result": False, "message": serializer.errors})


class DeveloperDetail(APIView):
    def get(self, request, developer_id, format=None):
        developer = get_object_or_404(Developer, pk=developer_id)
        data = DeveloperDetailSerializer(developer).data
        developers_data = cache.get(DEVELOPERS_EXTRA_CACHE_KEY, {})
        if not developers_data or developer_id not in developers_data:
            developer_cache_data = update_developer_cache_data(developer_id)
        else:
            developer_cache_data = developers_data.get(developer_id, {})
        data['star_rating'] = developer_cache_data['star_rating']
        data['partners'] = developer_cache_data['partners']
        return Response({"result": True, "data": data})

    @transaction.atomic
    def post(self, request, developer_id, format=None):
        developer = get_object_or_404(Developer, pk=developer_id)

        request_data = deepcopy(request.data)

        phone = request.data.get('phone', None)
        if phone and phone != developer.phone and Developer.objects.filter(phone=phone).exists():
            return Response({"result": False, "message": "手机号已被{}绑定".format(Developer.objects.get(phone=phone).name)})

        avatar_string = request_data.get('avatar', None)
        development_languages = request_data.get("development_languages", None)
        frameworks = request_data.get("frameworks", None)
        front_side_of_id_card_string = request.data.get('front_side_of_id_card', None)
        back_side_of_id_card_string = request.data.get('back_side_of_id_card', None)

        avatar_file = base64_string_to_file(avatar_string)
        if avatar_file:
            request_data["avatar"] = avatar_file
        else:
            request_data.pop('avatar', None)

        front_side_of_id_card_file = base64_string_to_file(front_side_of_id_card_string)
        if front_side_of_id_card_file:
            request_data["front_side_of_id_card"] = front_side_of_id_card_file
        else:
            request_data.pop('front_side_of_id_card', None)

        back_side_of_id_card_file = base64_string_to_file(back_side_of_id_card_string)
        if back_side_of_id_card_file:
            request_data["back_side_of_id_card"] = back_side_of_id_card_file
        else:
            request_data.pop('back_side_of_id_card', None)

        origin = deepcopy(developer)
        serializer = DeveloperCreateSerializer(developer, data=request_data)
        if serializer.is_valid():
            savepoint = transaction.savepoint()
            try:
                developer = serializer.save()
                if development_languages is not None:
                    developer.development_languages.clear()
                    developer.development_languages.add(*development_languages)
                if frameworks is not None:
                    developer.frameworks.clear()
                    developer.frameworks.add(*frameworks)
            except Exception as e:
                logger.error(e)
                transaction.savepoint_rollback(savepoint)
                raise
            else:
                Log.build_update_object_log(operator=request.user, original=origin, updated=developer)
                serializer = DeveloperSimpleSerializer(developer)
                return Response({"result": True, "data": serializer.data})
        return Response({"result": False, "message": str(serializer.errors)})


@api_view(['GET'])
def developers_tags(request):
    development_language_list = []
    framework_list = []
    developers = Developer.objects.prefetch_related("frameworks", "development_languages").all()
    if developers.exists():
        development_languages = developers.first().development_languages.all()
        frameworks = developers.first().frameworks.all()
        for developer in developers:
            development_languages = development_languages | developer.development_languages.all()
            frameworks = frameworks | developer.frameworks.all()
        development_language_list = development_languages.distinct().values()
        framework_list = frameworks.distinct().values()
    return Response({'development_language_list': development_language_list, "framework_list": framework_list})


class RoleList(APIView):
    def get(self, request):
        roles = Role.objects.all()
        serializer = RoleSerializer(roles, many=True)
        return farm_response.api_success(serializer.data)


@api_view(['GET'])
def role_developers(request, role_id):
    role = get_object_or_404(Role, id=role_id)
    developers = role.developers.filter(status='1')
    serializer = DeveloperSimpleSerializer(developers, many=True)
    return Response({"result": True, "data": serializer.data})


@api_view(['POST'])
def developer_status(request, developer_id):
    developer = get_object_or_404(Developer, id=developer_id)
    if request.data.get('status', None) is None:
        return Response({"result": False, "message": "请提供有效的status参数"})
    status = str(request.data['status'])
    # 弃用
    if status == '0' and not request.data.get('abandoned_reason'):
        return Response({"result": False, "message": "请输入弃用理由"})
    if status == '2' and not request.data.get('expected_work_at'):
        return Response({"result": False, "message": "请输入预计可接单时间"})
    origin = deepcopy(developer)
    serializer = DeveloperStatusSerializer(developer, data=request.data)
    if serializer.is_valid():
        developer = serializer.save()
        Log.build_update_object_log(request.user, origin, developer)
        return Response({"result": True, "data": serializer.data})
    return Response({"result": False, "message": serializer.errors})


@api_view(['POST'])
def change_developer_id_card(request, developer_id):
    developer = get_object_or_404(Developer, id=developer_id)
    origin = deepcopy(developer)
    front_side_of_id_card_string = request.data.get('front_side_of_id_card', None)
    back_side_of_id_card_string = request.data.get('back_side_of_id_card', None)

    front_side_of_id_card_file = base64_string_to_file(front_side_of_id_card_string)
    if front_side_of_id_card_file:
        developer.front_side_of_id_card = front_side_of_id_card_file

    back_side_of_id_card_file = base64_string_to_file(back_side_of_id_card_string)
    if back_side_of_id_card_file:
        developer.back_side_of_id_card = back_side_of_id_card_file

    if any([front_side_of_id_card_file, back_side_of_id_card_file]):
        developer.save()
        Log.build_update_object_log(request.user, origin, developer)
        return Response({"result": True, 'message': ''})
    else:
        return Response({"result": False, "message": "请提供有效的图片base64字符串"})


@api_view(['GET'])
def developer_private_permission(request, id):
    developer = get_object_or_404(Developer, id=id)
    has_perm = has_function_perm(request.user, 'view_all_developer_id_card_info')
    has_cooperation = has_cooperation_with_developer_at_present(request.user, developer.id)
    return api_success({"has_perm": has_perm or has_cooperation})


@api_view(['GET'])
def download_developer_id_card_image(request, id):
    developer = get_object_or_404(Developer, id=id)
    has_perm = has_function_perm(request.user, 'view_all_developer_id_card_info')
    has_cooperation = has_cooperation_with_developer_at_present(request.user, developer.id)
    if not any([has_perm, has_cooperation]):
        return api_permissions_required()
    id_card_type = request.GET.get('type', None)
    if id_card_type not in ['front_side', 'back_side']:
        return api_bad_request("id_card_type not  in ['front_side', 'back_side']")
    file = None
    file_name = "身份证照片"
    if id_card_type == 'front_side' and developer.front_side_of_id_card:
        file = developer.front_side_of_id_card
        file_name = '身份证正面照片.{}'.format(get_file_suffix(file.name))
    elif id_card_type == 'back_side' and developer.back_side_of_id_card:
        file = developer.back_side_of_id_card
        file_name = '身份证反面照片.{}'.format(get_file_suffix(file.name))
    if file:
        content_type, encoding = mimetypes.guess_type(file.name)
        content_type = content_type or 'application/octet-stream'
        wrapper = FileWrapper(file)
        response = FileResponse(wrapper, content_type=content_type)
        response['Content-Disposition'] = "attachment; filename*=utf-8''{}".format(
            escape_uri_path(developer.name + file_name))
        response['Access-Control-Expose-Headers'] = 'Content-Disposition'
        if encoding:
            response["Content-Encoding"] = encoding
        return response
    return farm_response.api_not_found()


@api_view(['GET'])
def position_candidates(request, developer_id):
    developer = get_object_or_404(Developer, id=developer_id)
    candidates = developer.position_candidates.all().order_by('-created_at')
    serializer = JobPositionCandidateViewSerializer(candidates, many=True)
    return Response({"result": True, 'data': serializer.data})


@api_view(['GET'])
def ongoing_projects_jobs(request, developer_id):
    from projects.serializers import JobSerializer
    developer = get_object_or_404(Developer, id=developer_id)
    jobs = developer.active_project_jobs().order_by('-project__created_at')
    data = JobSerializer(jobs, many=True).data
    return api_success(data)


@api_view(['GET'])
def closed_projects_jobs(request, developer_id):
    from projects.serializers import JobSerializer
    developer = get_object_or_404(Developer, id=developer_id)
    jobs = developer.finished_project_jobs().order_by('-project__done_at')
    data = JobSerializer(jobs, many=True).data
    return api_success(data)


@api_view(['GET'])
def projects_jobs(request, developer_id):
    from projects.serializers import JobSerializer
    developer = get_object_or_404(Developer, id=developer_id)
    jobs = developer.job_positions.all()
    data = JobSerializer(jobs, many=True).data
    return api_success(data)


@api_view(['POST'])
def block_gitlab_user(request, developer_id):
    developer = get_object_or_404(Developer, pk=developer_id)
    gitlab_user_id = developer.gitlab_user_id
    if not gitlab_user_id:
        return Response({"result": False, 'message': '未绑定gitlab账户'})
    try:
        result = gitlab_client.block_user(user_id=gitlab_user_id)
        if result:
            message = "禁用工程师Gitlab帐号"
            Log.objects.create(content=message, operator=request.user, content_object=developer)
            crawl_gitlab_user_data(gitlab_user_id)
            return Response({"result": True, 'data': None})
    except Exception as e:
        crawl_gitlab_user_data(gitlab_user_id)
        return Response({"result": False, 'message': str(e)})
    return Response({"result": False, 'message': '禁用失败'})


@api_view(['POST'])
def unblock_gitlab_user(request, developer_id):
    developer = get_object_or_404(Developer, pk=developer_id)
    gitlab_user_id = developer.gitlab_user_id
    if not gitlab_user_id:
        return Response({"result": False, 'message': '未绑定gitlab账户'})
    result = gitlab_client.unblock_user(user_id=gitlab_user_id)
    if result:
        crawl_gitlab_user_data(gitlab_user_id)
        message = "解封工程师Gitlab帐号"
        Log.objects.create(content=message, operator=request.user, content_object=developer)
        return Response({"result": True, 'data': None})
    return Response({"result": False, 'message': '解禁失败'})


@api_view(['POST'])
def unbind_gitlab_user(request, developer_id):
    developer = get_object_or_404(Developer, pk=developer_id)
    gitlab_user_id = developer.gitlab_user_id
    if not gitlab_user_id:
        return Response({"result": False, 'message': '未绑定gitlab账户'})
    origin = deepcopy(developer)
    developer.gitlab_user_id = None
    developer.save()
    Log.build_update_object_log(request.user, origin, developer, comment='解绑gitlab账户')
    return Response({"result": True, "data": None})


@api_view(['GET'])
def gitlab_user_projects(request, developer_id):
    developer = get_object_or_404(Developer, pk=developer_id)
    gitlab_user_id = developer.gitlab_user_id
    if not gitlab_user_id:
        return Response({"result": False, 'message': '未绑定gitlab账户'})
    gitlab_projects = cache.get('gitlab-projects', {})
    gitlab_groups = cache.get('gitlab-groups', {})

    project_list = []
    group_list = []
    user_data = get_gitlab_user_data(gitlab_user_id)
    if user_data:
        project_ids = user_data.get('projects')
        group_ids = user_data.get('groups')
        if project_ids:
            for project_id in project_ids:
                if project_id in gitlab_projects:
                    project_data = gitlab_projects[project_id]
                    project_list.append(project_data)
            project_list = sorted(project_list,
                                  key=lambda x: x['members'].get(gitlab_user_id, {'access_level': 60})['access_level'])

        if group_ids:
            for group_id in group_ids:
                if group_id in gitlab_groups:
                    group_data = gitlab_groups[group_id]
                    group_list.append(group_data)
            group_list = sorted(group_list,
                                key=lambda x: x['members'].get(gitlab_user_id, {'access_level': 60})['access_level'])

        return Response(
            {"result": True, "data": {'projects': project_list, 'groups': group_list, 'user': user_data}})
    return Response({"result": False, 'message': 'git用户名无效'})


@api_view(['DELETE'])
def leave_git_groups_projects(request, developer_id, all=False):
    developer = get_object_or_404(Developer, pk=developer_id)
    block = request.data.get('block', None)
    gitlab_user_id = developer.gitlab_user_id
    gitlab_users = cache.get('gitlab-users', {})
    gitlab_projects = cache.get('gitlab-projects', {})
    gitlab_groups = cache.get('gitlab-groups', {})

    if gitlab_user_id and gitlab_user_id in gitlab_users:
        try:
            user_data = gitlab_users[gitlab_user_id]
            project_ids = user_data['projects'] if all else request.data.get('projects', [])
            group_ids = user_data['groups'] if all else request.data.get('groups', [])
            deleted_projects = []
            for project_id in project_ids:
                try:
                    gitlab_client.delete_project_members(project_id=project_id, user_id=gitlab_user_id)
                    if project_id in gitlab_projects:
                        deleted_projects.append(gitlab_projects[project_id]['name_with_namespace'])
                except:
                    continue
            for group_id in group_ids:
                try:
                    gitlab_client.delete_group_members(group_id=group_id, user_id=gitlab_user_id)
                    if group_id in gitlab_groups:
                        deleted_projects.append(gitlab_groups[group_id]['name'])
                except:
                    continue
            if block:
                gitlab_client.block_user(user_id=gitlab_user_id)
            project_str = ','.join(deleted_projects)
            if all:
                message = "将工程师从所有Gitlab项目中移除"
                message = message + '。项目列表【{project_str}】'.format(project_str=project_str)
                Log.objects.create(content=message, operator=request.user, content_object=developer)
            else:
                message = "将工程师从Gitlab项目【{project_str}】中移除".format(project_str=project_str)
                message = message + '，并禁用其Gitlab帐号' if block else message
                Log.objects.create(content=message, operator=request.user, content_object=developer)
            crawl_gitlab_user_data(gitlab_user_id)
            return Response({"result": True, "data": user_data})
        except Exception as e:
            logger.error(e)
            crawl_gitlab_user_data(gitlab_user_id)
            return Response({"result": False, 'message': str(e)})
    return Response({"result": False, 'message': '用户名为必填'})


@api_view(['DELETE'])
def gitlab_user_leave_project(request, developer_id, project_id):
    developer = get_object_or_404(Developer, pk=developer_id)
    gitlab_user_id = developer.gitlab_user_id
    gitlab_users = cache.get('gitlab-users', {})
    project_name = request.data.get('name_with_namespace')
    if gitlab_user_id and gitlab_user_id in gitlab_users:
        try:
            user_data = gitlab_users[gitlab_user_id]
            gitlab_client.delete_project_members(project_id=project_id, user_id=gitlab_user_id)
            if project_id in user_data['projects']:
                user_data['projects'].remove(project_id)
            gitlab_users[gitlab_user_id] = user_data
            cache.set('gitlab-users', gitlab_users, None)
            crawl_gitlab_user_data.delay(gitlab_user_id)
            message = "将工程师从Gitlab项目【{project_name}】中移除".format(project_name=project_name)
            Log.objects.create(content=message, operator=request.user, content_object=developer)
            return Response({"result": True, "data": user_data})
        except Exception as e:
            logger.error(e)
            return Response({"result": False, 'message': str(e)})
    return Response({"result": False, 'message': '用户名为必填'})


@api_view(['DELETE'])
def gitlab_user_leave_group(request, developer_id, group_id):
    developer = get_object_or_404(Developer, pk=developer_id)
    gitlab_user_id = developer.gitlab_user_id
    gitlab_users = cache.get('gitlab-users', {})
    group_name = request.data.get('name')
    if gitlab_user_id and gitlab_user_id in gitlab_users:
        try:
            user_data = gitlab_users[gitlab_user_id]
            gitlab_client.delete_group_members(group_id=group_id, user_id=gitlab_user_id)
            if group_id in user_data['groups']:
                user_data['groups'].remove(group_id)
            gitlab_users[gitlab_user_id] = user_data
            cache.set('gitlab-users', gitlab_users, None)
            crawl_gitlab_user_data.delay(gitlab_user_id)
            message = "将工程师从Gitlab项目组【{group_name}】中移除".format(group_name=group_name)
            Log.objects.create(content=message, operator=request.user, content_object=developer)
            return Response({"result": True, "data": user_data})
        except Exception as e:
            logger.error(e)
            return Response({"result": False, 'message': str(e)})
    return Response({"result": False, 'message': '用户名为必填'})


@api_view(['GET'])
def developers_gitlab_committers(request):
    developers = Developer.objects.filter(gitlab_user_id__isnull=False)

    gitlab_users = cache.get('gitlab-users', {})
    data = []
    for developer in developers:
        gitlab_user_id = developer.gitlab_user_id
        if gitlab_user_id and gitlab_user_id in gitlab_users:
            user_data = gitlab_users[gitlab_user_id]
            developer_data = {'id': developer.id, 'name': developer.id, 'committers': user_data.get('committers', [])}
            data.append(developer_data)
    return Response({"result": True, "data": data})


class DeveloperCommitters(APIView):
    def get(self, request, developer_id, format=None):
        developer = get_object_or_404(Developer, pk=developer_id)
        data = None
        if developer.gitlab_user_id:
            data = get_gitlab_user_data(developer.gitlab_user_id)
        return Response({"result": True, "data": data})

    def post(self, request, developer_id, format=None):
        developer = get_object_or_404(Developer, pk=developer_id)
        gitlab_user_id = developer.gitlab_user_id
        if gitlab_user_id:
            user_data = get_gitlab_user_data(gitlab_user_id)
            if user_data:
                committers = request.data.get('committers', [])
                user_data['committers'] = committers
                default_one = {'committer_name': user_data['name'], 'committer_email': user_data['email']}
                default_two = {'committer_name': user_data['username'], 'committer_email': user_data['email']}
                if default_one not in user_data['committers']:
                    user_data['committers'].append(default_one)
                if default_two not in user_data['committers']:
                    user_data['committers'].append(default_two)
                gitlab_users = cache.get('gitlab-users', {})
                gitlab_users[gitlab_user_id] = deepcopy(user_data)
                cache.set('gitlab-users', gitlab_users, None)
                return Response({"result": True, "data": user_data})
            return Response({"result": False, "message": "获取gitlab账户信息失败"})
        return Response({"result": False, "message": "工程师未绑定gitlab账户"})


@api_view(['GET'])
def one_time_authentication_key(request, developer_id):
    developer = get_object_or_404(Developer, pk=developer_id)
    if not developer.is_active:
        return Response({"result": False, "message": "该工程师已弃用"})
    authentication_key = 'dev{}{}'.format(developer.id, gen_uuid(8))
    key_data = {'authentication_key': authentication_key, 'created_at': timezone.now(), 'expired_seconds': 3600,
                'developer': {'id': developer.id, 'name': developer.name, 'phone': developer.phone}}
    cache.set(authentication_key, key_data, 3600)
    return Response({"result": True, "data": key_data})


@api_view(['GET'])
def export_excel(request):
    from xlwt import Workbook

    from wsgiref.util import FileWrapper

    from django.http import FileResponse
    from django.utils.encoding import escape_uri_path
    from django.conf import settings

    developer_list = Developer.objects.all().order_by('created_at')

    leads_data = DeveloperExportSerializer(developer_list, many=True).data
    w = Workbook()  # 创建一个工作簿
    ws = w.add_sheet("远程工程师统计")  # 创建一个工作表

    export_fields = [
        {'field_name': 'created_at', 'verbose_name': '创建时间', 'col_width': 16},
        {'field_name': 'status_display', 'verbose_name': '状态', 'col_width': 8},
        {'field_name': 'name', 'verbose_name': '名称', 'col_width': 10},
        {'field_name': 'roles', 'verbose_name': '职位', 'col_width': 16},
        {'field_name': 'development_languages', 'verbose_name': '开发语言', 'col_width': 18},
        {'field_name': 'frameworks', 'verbose_name': '框架工具', 'col_width': 18},
        {'field_name': 'abandoned_at', 'verbose_name': '弃用时间', 'col_width': 16},
        {'field_name': 'abandoned_reason', 'verbose_name': '弃用理由', 'col_width': 25},
        {'field_name': 'project_total', 'verbose_name': '项目总数', 'col_width': 8},
        {'field_name': 'star_rating', 'verbose_name': '综合评分', 'col_width': 8},
    ]

    for index_num, field in enumerate(export_fields):
        ws.write(0, index_num, field['verbose_name'])

    for index_num, lead_data in enumerate(leads_data):
        for field_num, field in enumerate(export_fields):
            ws.write(index_num + 1, field_num, lead_data[field['field_name']])

    for i in range(len(export_fields)):
        ws.col(i).width = 256 * export_fields[i]['col_width']

    path = settings.MEDIA_ROOT + 'DeveloperStatisticTable.xls'
    filename = 'DeveloperStatisticTable.xls'
    w.save(path)  # 保存
    wrapper = FileWrapper(open(path, 'rb'))
    response = FileResponse(wrapper, content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = "attachment; filename*=utf-8''{}".format(escape_uri_path(filename))
    return response


@api_view(['GET'])
def quip_developer_documents(request):
    doc_list = get_developer_quip_documents()
    rebuild_developer_quip_documents.delay()
    return farm_response.api_success(data=doc_list)


@method_decorator(func_perm_required('manage_developers_documents'), name='post')
class DocumentList(APIView):
    def get(self, request):
        docs = Document.active_documents().order_by('index')
        data = DocumentListSerializer(docs, many=True).data
        rebuild_developer_quip_documents.delay()
        return farm_response.api_success(data=data)

    @transaction.atomic
    def post(self, request):
        request_data = deepcopy(request.data)
        title = request.data.get('title', None)
        if Document.active_documents().filter(title=title).exists():
            return farm_response.api_bad_request("已存在相同名字的文档")

        quip_doc_id = request.data.get('quip_doc_id', None)
        if not quip_doc_id:
            return farm_response.api_request_params_required('quip_doc_id')
        doc_data = get_quip_doc(quip_doc_id)

        version_data = dict()
        version_data['quip_doc_id'] = quip_doc_id
        version_data['html'] = doc_data['html']
        version_data['version'] = '1.0'
        version_data['version_mode'] = 'large'
        version_data['status'] = 'online'
        version_data['submitter'] = request.user.id
        version_data['remarks'] = request_data.get('remarks', None)
        request_data['is_public'] = request_data.get('is_public', False)
        request_data['index'] = Document.get_new_index()

        serializer = DocumentDetailSerializer(data=request_data)
        if serializer.is_valid():
            document = serializer.save()
            version_data['document'] = document.id
            version_serializer = DocumentVersionSerializer(data=version_data)
            if not version_serializer.is_valid():
                return farm_response.api_bad_request(version_serializer.errors)
            version = version_serializer.save()
            if settings.DEVELOPMENT:
                build_document_version_clean_html(version.id)
            else:
                build_document_version_clean_html.delay(version.id)
            rebuild_ongoing_projects_dev_docs_checkpoints_status.delay()
            return farm_response.api_success(data=serializer.data)
        return farm_response.api_bad_request(serializer.errors)


@method_decorator(func_perm_required('manage_developers_documents'), name='post')
@method_decorator(func_perm_required('manage_developers_documents'), name='delete')
class DocumentDetail(APIView):
    def get(self, request, id):
        document = get_object_or_404(Document, pk=id)
        data = DocumentDetailSerializer(document, many=False).data
        return farm_response.api_success(data=data)

    @transaction.atomic
    def post(self, request, id):
        document = get_object_or_404(Document, pk=id)
        request_data = deepcopy(request.data)
        title = request.data.get('title', None)
        if Document.active_documents().exclude(id=document.id).filter(title=title).exists():
            return farm_response.api_bad_request("已存在相同名字的文档")
        serializer = DocumentEditSerializer(document, data=request_data)
        if serializer.is_valid():
            document = serializer.save()
            data = DocumentListSerializer(document, many=False).data
            return farm_response.api_success(data=data)
        return farm_response.api_bad_request(serializer.errors)

    def delete(self, request, id):
        document = get_object_or_404(Document, pk=id)
        document.deleted = True
        document.save()
        return farm_response.api_success()


@api_view(['POST'])
@request_data_fields_required(['quip_doc_id', 'version_mode'])
@func_perm_required('manage_developers_documents')
def update_document_version(request, id):
    document = get_object_or_404(Document, pk=id, deleted=False)
    version_mode = request.data.get('version_mode', None)
    if version_mode not in ['large', 'mini']:
        return farm_response.api_bad_request("update_mode not in ['large_version',     'mini_version']")

    request_data = deepcopy(request.data)

    origin_online_version = deepcopy(document.online_version)

    quip_doc_id = request.data.get('quip_doc_id', None)
    if not quip_doc_id:
        return farm_response.api_request_params_required('quip_doc_id')
    doc_data = get_quip_doc(quip_doc_id)
    version = Document.get_new_version(document, version_mode)

    version_data = dict()
    version_data['quip_doc_id'] = quip_doc_id
    version_data['html'] = doc_data['html']
    version_data['version'] = version
    version_data['version_mode'] = version_mode
    version_data['status'] = 'online'
    version_data['submitter'] = request.user.id
    version_data['remarks'] = request_data.get('remarks', None)
    version_data['document'] = document.id

    version_serializer = DocumentVersionSerializer(data=version_data)
    if version_serializer.is_valid():
        version = version_serializer.save()
        if version.version_mode == 'large':
            rebuild_ongoing_projects_dev_docs_checkpoints_status.delay(True)
        if origin_online_version:
            origin_online_version.status = 'history'
            origin_online_version.save()
        if settings.DEVELOPMENT:
            build_document_version_clean_html(version.id)
        else:
            build_document_version_clean_html.delay(version.id)
        data = DocumentListSerializer(document, many=False).data
        return farm_response.api_success(data=data)
    return farm_response.api_bad_request(version_serializer.errors)


@api_view(['POST'])
@func_perm_required('document_confirm_sync')
def sync_document(request, id):
    document = get_object_or_404(Document, pk=id)
    request_data = deepcopy(request.data)
    request_data['document'] = document.online_version.id
    request_data['user'] = request.user.id
    serializer = DocumentSyncLogSerializer(data=request_data)

    if serializer.is_valid():
        sync_log = serializer.save()
        developer = sync_log.developer

        all_projects = developer.all_projects()
        for p in all_projects:
            p.rebuild_dev_docs_checkpoint_status()

        return farm_response.api_success(data=serializer.data)
    return farm_response.api_bad_request(serializer.errors)


@api_view(['POST'])
@func_perm_required('document_confirm_sync')
@request_data_fields_required(['project', 'document', 'developer'])
def project_developer_document_skip_sync(request):
    document_id = request.data.get('document')
    developer_id = request.data.get('developer')
    project_id = request.data.get('project')
    document = get_object_or_404(Document, pk=document_id)
    developer = get_object_or_404(Developer, pk=developer_id)
    project = get_object_or_404(Project, pk=project_id)

    document.skip_sync_project_developer_document(project, developer)
    project.rebuild_dev_docs_checkpoint_status()

    return farm_response.api_success()


@api_view(['GET'])
def developer_documents(request, developer_id):
    developer = get_object_or_404(Developer, pk=developer_id)
    docs = developer.active_developers_documents()
    documents_data = DocumentListSerializer(docs, many=True).data

    for document_data in documents_data:
        document = Document.objects.get(pk=document_data['id'])
        last_read_log = document.developer_last_large_version_read_log(developer)
        # 最近阅读记录
        document_data['last_read_log'] = DocumentReadLogSerializer(last_read_log).data if last_read_log else None

        # 最近阅读的版本
        last_read_version = document.developer_last_read_version(developer)
        document_data['last_read_version'] = DocumentVersionSimpleSerializer(
            last_read_version).data if last_read_version else None

        # 最近同步记录
        sync_log = document.developer_current_large_version_sync_log(developer)
        document_data['document_sync_log'] = DocumentSyncLogSerializer(sync_log).data if sync_log else None

    return farm_response.api_success(data=documents_data)


@api_view(['GET'])
def project_developers_documents(request, project_id):
    from projects.models import Project
    project = get_object_or_404(Project, pk=project_id)
    positions = project.job_positions.order_by('created_at')
    documents = Document.objects.none()

    developers = []

    documents_developers_dict = {}
    for position in positions:
        developer = position.developer
        if developer:
            if developer not in developers:
                developers.append(developer)
            docs = developer.active_developers_documents()
            for doc in docs:
                if doc.id not in documents_developers_dict:
                    documents_developers_dict[doc.id] = set()
                documents_developers_dict[doc.id].add(developer)
            documents = documents | docs

    developers_data = DeveloperVerySimpleSerializer(developers, many=True).data
    # developer_data_dict = {}
    # for developer in developers_data:
    #     developer_data_dict[developer['id']] = developer

    documents = documents.distinct().order_by('index')
    documents_data = []
    for document in documents:
        # online_version = document.online_version
        document_data = DocumentListSerializer(document, many=False).data
        # document_data['online_version'] = DocumentVersionSerializer(online_version, many=False).data
        document_data['developers'] = {}
        doc_developers_data = document_data['developers']

        doc_developers = documents_developers_dict.get(document.id, set())
        for developer in doc_developers:
            developer_data = DeveloperVerySimpleSerializer(developer, many=False).data
            read_log = document.developer_current_large_version_read_log(developer)

            developer_data['document_read_log'] = DocumentReadLogSerializer(read_log).data if read_log else None

            if document.project_developer_is_skipped(project, developer):
                developer_data['is_skipped_sync'] = True
            else:
                sync_log = document.developer_current_large_version_sync_log(developer)
                developer_data['document_sync_log'] = DocumentSyncLogSerializer(sync_log).data if sync_log else None

            doc_developers_data[developer.id] = developer_data
        documents_data.append(document_data)

    result_data = {"documents": documents_data, "developers": developers_data}
    return farm_response.api_success(result_data)


@api_view(['POST'])
@func_perm_required('manage_developers_documents')
def drag_document(request):
    origin_id = request.data.get('origin', None)
    target_id = request.data.get('target', None)
    if not all([origin_id, target_id]):
        return farm_response.api_bad_request('拖拽对象的id参数origin、目标对象的id参数target为必填')

    if origin_id == target_id:
        return farm_response.api_bad_request('拖拽对象 目标对象一致 无需移动')
    origin_obj = Document.active_documents().filter(pk=origin_id).first()
    target_obj = Document.active_documents().filter(pk=target_id).first()
    if not origin_obj:
        return farm_response.api_bad_request('拖拽对象不存在')
    if not target_obj:
        return farm_response.api_bad_request('目标对象不存在')

    # 目标对象的位置 比拖拽对象小      拖拽对象占距目标对象的位置   目标对象(包含)与拖拽对象之间的元素都下移一位 index+1
    target_index = target_obj.index
    origin_index = origin_obj.index
    if target_index < origin_index:
        middle_siblings = Document.active_documents().filter(index__gte=target_index, index__lt=origin_index)
        for sibling in middle_siblings:
            sibling.index = sibling.index + 1
            sibling.save()
        origin_obj.index = target_index
        origin_obj.save()

    # 目标对象的位置 比拖拽对象大      拖拽对象占距目标对象的位置   目标对象(包含)与拖拽对象之间的元素都上移一位 index-1
    if target_index > origin_index:
        middle_siblings = Document.active_documents().filter(index__gt=origin_index, index__lte=target_index)
        for sibling in middle_siblings:
            sibling.index = sibling.index - 1
            sibling.save()
        origin_obj.index = target_index
        origin_obj.save()
    return farm_response.api_success()


@api_view(['GET'])
def daily_works_message(request):
    data = send_project_developer_daily_works_to_developers(to_send=False)
    developer_data = send_project_developer_daily_works_to_manager_and_tpm(to_send=False)
    return farm_response.api_success({'users': data, 'developers': developer_data})


@api_view(['GET'])
def cache_rebuild(request):
    if settings.DEVELOPMENT:
        update_all_developers_cache_data()
    else:
        update_all_developers_cache_data.delay()
    for obj in Developer.objects.all():
        if not obj.name_pinyin:
            obj.name_pinyin = ''.join(lazy_pinyin(obj.name))
            obj.save()
    return api_success()
