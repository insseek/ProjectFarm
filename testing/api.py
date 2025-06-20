import json
import logging
import os
import re
from copy import deepcopy
from datetime import timedelta, datetime
from wsgiref.util import FileWrapper

from django.db import transaction
from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.utils.encoding import escape_uri_path
from django_filters.rest_framework import DjangoFilterBackend
from django.conf import settings
from django.core.mail import send_mail
from django.core.cache import cache
from rest_framework import viewsets, status, filters
from rest_framework.viewsets import GenericViewSet
from rest_framework import generics, mixins, views
from rest_framework.mixins import (ListModelMixin, CreateModelMixin, RetrieveModelMixin, UpdateModelMixin,
                                   DestroyModelMixin)
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action, api_view
from rest_framework.pagination import PageNumberPagination
from pypinyin import lazy_pinyin
from xlwt import Workbook
from xlutils.copy import copy as xlutils_copy
import xlrd
import xlwt

from auth_top.models import TopUser
from auth_top.utils import get_top_user_data
from auth_top.serializers import TopUserViewSerializer, TopUserSimpleViewSerializer
from comments.models import Comment
from auth_top.permissions_init import has_app_function_perms
from farmbase.utils import gen_uuid
from gearfarm.utils import simple_responses
from gearfarm.utils.common_utils import get_date_str_list
from gearfarm.utils.simple_decorators import request_data_fields_required, request_params_required
from gearfarm.utils.simple_responses import api_success, api_created_success, api_bad_request, api_not_found
from farmbase.permissions_utils import has_function_perms
from testing.serializers import (TestCaseLibrarySerializer, BugSimpleSerializer,
                                 TestCaseLibraryUpdateSerializer, TestCaseModuleSerializer,
                                 TestCaseModuleWithChildrenSerializer, TestCaseModuleWithChildrenWithCaseSerializer,
                                 TestCaseModuleUpdateSerializer,
                                 TestCaseSerializer, TestCaseUpdateSerializer, TestCaseStatusSerializer,
                                 ProjectListSerializer, ProjectDetailSerializer,
                                 ProjectPlatformSerializer, ProjectPlatformUpdateSerializer,
                                 ProjectTagSerializer, ProjectTagUpdateSerializer, ProjectTagListSerializer,
                                 ProjectTestCaseModuleSerializer,

                                 ProjectTestCaseModuleWithChildrenSerializer,
                                 ProjectTestCaseModuleWithChildrenWithCaseSerializer,
                                 ProjectTestCaseModuleUpdateSerializer,
                                 ProjectTestCaseSerializer, ProjectTestCaseUpdateSerializer,
                                 ProjectTestCaseStatusSerializer, ProjectTestPlanListSerializer,
                                 ProjectTestPlanSerializer, ProjectTestPlanVerifyFieldSerializer,
                                 TestPlanModuleWithChildrenSerializer, TestPlanCaseSerializer,
                                 TestPlanCaseStatusSerializer, BugSerializer, BugUpdateSerializer,
                                 BugAssigneeSerializer, BugStatusSerializer, BugOperationLogSerializer,
                                 BugExportSerializer, ProjectTestCaseReviewLogSerializer, TestCaseReviewLogSerializer,
                                 ProjectTestCaseExecuteLogSerializer, TestDayBugStatisticSerializer)
from projects.models import Project
from testing.models import (TestCaseLibrary, TestCaseModule, TestCase, ProjectPlatform, ProjectTestCaseModule,
                            ProjectTestCase,
                            ProjectTag, ProjectTestPlan, TestPlanModule, TestPlanCase, Bug, BugOperationLog,
                            ProjectTestCaseReviewLog, TestCaseReviewLog, ProjectTestCaseExecuteLog, TestDayBugStatistic)
from testing.filters import ProjectFilter, TestCaseFilter, ProjectTestCaseFilter, ProjectTestPlanFilter, \
    TestPlanCaseFilter, BugFilter
from notifications.utils import create_top_user_notification
from testing.decorators import project_test_cases_params_verify, project_test_plan_cases_params_verify, \
    test_cases_params_verify, project_test_cases_batch_copy_params_verify
from exports.utils import build_excel_response
from testing.tasks import build_project_today_pending_bugs_statistics

logger = logging.getLogger()


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


class TestCaseLibraryViewSet(viewsets.ModelViewSet):
    """
    用例库
    """
    queryset_model = TestCaseLibrary
    serializer_class = TestCaseLibrarySerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter,)
    search_fields = ('name', 'description',)
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        """
           A viewset that provides default `create()`, `retrieve()`, `update()`,
           `partial_update()`, `destroy()` and `list()` actions.
           """
        if self.action in ['update', 'partial_update']:
            self.serializer_class = TestCaseLibraryUpdateSerializer
        return super(TestCaseLibraryViewSet, self).get_serializer_class()

    # def get_queryset(self):
    #     return TestCaseLibrary.objects.order_by('created_at')

    def get_queryset(self):
        page = self.request.query_params.get('page')
        page_size = self.request.query_params.get('page_size')
        if not all([page, page_size]):
            self.pagination_class = None
        queryset = self.queryset_model.objects.order_by('-created_at')
        return queryset

    def create(self, request, *args, **kwargs):
        """创建"""
        top_user = self.request.top_user
        request_data = deepcopy(request.data)
        request_data['creator'] = top_user.id
        serializer = self.get_serializer(data=request_data)
        if not serializer.is_valid(raise_exception=False):
            return api_bad_request(serializer.errors)

        self.perform_create(serializer)
        return api_created_success(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.modules.exists():
            return api_bad_request('该用例库已存在模块 不能删除')
        return super().destroy(request, *args, **kwargs)


@method_decorator(
    request_data_fields_required(['origin_id', 'target_parent_id', 'target_previous_id', 'target_next_id']),
    name='drag_tree')
@method_decorator(request_params_required(['library']), name='list')
class TestCaseModuleViewSet(viewsets.ModelViewSet):
    """
    用例库模块
    """
    # queryset = TestCaseModule.objects.order_by('created_at')
    queryset_model = TestCaseModule
    queryset = TestCaseModule.objects.all()
    serializer_class = TestCaseModuleSerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter,)
    search_fields = ('name', 'description',)

    def get_serializer_class(self):
        """
           A viewset that provides default `create()`, `retrieve()`, `update()`,
           `partial_update()`, `destroy()` and `list()` actions.
           """
        with_cases = self.request.query_params.get('with_cases') in ['True', 'true', '1', True, 1]

        if self.action in ['update', 'partial_update']:
            self.serializer_class = TestCaseModuleUpdateSerializer
        elif self.action == 'list':
            library = self.request.query_params.get('library')
            if library:
                self.serializer_class = TestCaseModuleWithChildrenSerializer
            if with_cases:
                self.serializer_class = TestCaseModuleWithChildrenWithCaseSerializer

        return super(TestCaseModuleViewSet, self).get_serializer_class()

    def get_queryset(self):
        queryset = TestCaseModule.objects.all()
        library = self.request.query_params.get('library')
        if library:
            queryset = queryset.filter(library_id=library, parent_id=None).order_by('index')
        return queryset

    def create(self, request, *args, **kwargs):
        """创建"""
        top_user = self.request.top_user
        request_data = deepcopy(request.data)
        request_data['creator'] = top_user.id
        serializer = self.get_serializer(data=request_data)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data
        parent = validated_data.get('parent')
        library = validated_data.get('library')
        if parent and parent.library_id != library.id:
            return api_bad_request("父级模块的用例库 和所选用例库不一致")

        self.perform_create(serializer)
        return api_created_success(serializer.data)

    # 用例库模块拖拽
    @action(methods=['patch'], detail=False)
    def drag(self, request, *args, **kwargs):
        return drag_same_level_obj(request, self.queryset)

    # 项目用例库 模块拖拽
    @action(methods=['patch'], detail=False)
    def drag_tree(self, request, *args, **kwargs):
        return drag_sort_tree_obj(request, self.queryset)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.contained_test_cases.exists():
            return api_bad_request('该模块或其子模块下包含用例 不能删除')
        return super().destroy(request, *args, **kwargs)


@method_decorator(test_cases_params_verify, name='list')
@method_decorator(test_cases_params_verify, name='list_groups')
@method_decorator(test_cases_params_verify, name='filter_data')
@method_decorator(test_cases_params_verify, name='statistics_data')
@method_decorator(test_cases_params_verify, name='list_delete')
@method_decorator(test_cases_params_verify, name='list_move')
@method_decorator(request_data_fields_required(['cases', 'target_module']), name='batch_move')
@method_decorator(request_data_fields_required(['cases']), name='batch_delete')
@method_decorator(request_data_fields_required(['target_module']), name='list_move')
class TestCaseViewSet(viewsets.ModelViewSet):
    """
    用例库用例
    """
    queryset = TestCase.active_cases()
    serializer_class = TestCaseSerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter,)
    search_fields = ('description',)

    filter_fields = ('status',)
    filter_class = TestCaseFilter

    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        """
           A viewset that provides default `create()`, `retrieve()`, `update()`,
           `partial_update()`, `destroy()` and `list()` actions.
           """
        if self.action in ['update', 'partial_update']:
            self.serializer_class = TestCaseUpdateSerializer
        return super(TestCaseViewSet, self).get_serializer_class()

    def get_queryset(self):
        queryset = TestCase.active_cases()
        library = self.request.query_params.get('library')
        module = self.request.query_params.get('module')
        if module:
            queryset = queryset.filter(module_id=module).order_by('created_at')
        elif library:
            queryset = queryset.filter(module__library_id=library).order_by('created_at')

        page = self.request.query_params.get('page')
        page_size = self.request.query_params.get('page_size')
        if not all([page, page_size]):
            self.pagination_class = None

        return queryset

    def get_new_queryset(self):
        queryset = TestCase.active_cases()
        library = self.request.query_params.get('library')
        module = self.request.query_params.get('module')
        if module:
            module_ob = get_object_or_404(TestCaseModule, pk=module)
            queryset = module_ob.contained_test_cases.order_by('created_at')
        elif library:
            queryset = queryset.filter(module__library_id=library).order_by('created_at')
        return queryset

    @action(methods=['get'], detail=False)
    def list_groups(self, request, *args, **kwargs):
        queryset = self.get_new_queryset()
        queryset = self.filter_queryset(queryset)
        queryset = queryset.order_by('module__full_index')
        # queryset = sorted(queryset, key=lambda x: (x.module.full_index, x.module.id), reverse=False)
        page = self.request.query_params.get('page')
        page_size = self.request.query_params.get('page_size')
        if not all([page, page_size]):
            self.pagination_class = None
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            case_list = serializer.data
            res_data = self.make_groups(case_list)
            return self.get_paginated_response(res_data)

        serializer = self.get_serializer(queryset, many=True)
        case_list = serializer.data
        res_data = self.make_groups(case_list)
        return Response(res_data)

    @staticmethod
    def make_groups(case_list):
        case_data = {}
        for query in case_list:
            module_id = query['module']['id']
            if module_id not in case_data:
                case_data[module_id] = deepcopy(query['module'])
                case_data[module_id]['cases'] = []
            case_data[module_id]['cases'].append(query)
        for key in case_data:
            case_data[key]['cases'] = sorted(case_data[key]['cases'], key=lambda x: x['index'], reverse=False)
        case_data = sorted(case_data.values(), key=lambda x: x['full_index'], reverse=False)
        return case_data

    @action(methods=['get'], detail=False)
    def filter_data(self, request, *args, **kwargs):
        status_data = [{'value': value, 'label': label} for value, label in TestCase.STATUS_CHOICES]
        return api_success({"status": status_data})

    @action(methods=['get'], detail=False)
    def statistics_data(self, request, *args, **kwargs):
        queryset = self.get_new_queryset()
        queryset = self.filter_queryset(queryset)
        data = {'total': queryset.count()}
        for value, label in TestCase.STATUS_CHOICES:
            data[value] = queryset.filter(status=value).count()
        return api_success(data)

    def create(self, request, *args, **kwargs):
        """创建"""
        top_user = self.request.top_user
        request_data = deepcopy(request.data)
        request_data['creator'] = top_user.id
        serializer = self.get_serializer(data=request_data)
        serializer.is_valid(raise_exception=True)
        # self.perform_create(serializer)
        instance = serializer.save()
        TestCaseReviewLog.build_create_object_log(request.top_user, instance)
        return api_created_success(serializer.data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        origin = deepcopy(instance)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        if origin.status == 'rejected' and instance.status == 'rejected':
            editable_fields = ['description', 'precondition', 'expected_result']
            for field in editable_fields:
                if getattr(origin, field) != getattr(instance, field):
                    instance.status = 'pending'
                    instance.save()
                    break
        serializer = TestCaseSerializer(instance)
        TestCaseReviewLog.build_update_object_log(request.top_user, origin, instance)
        return Response(serializer.data)

    @action(methods=['patch'], detail=True, serializer_class=TestCaseStatusSerializer)
    def status(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}
        TestCaseReviewLog.build_log(request.top_user, instance, log_type=request.data.get('status', None),
                                    remarks=request.data.get('remarks', ''))
        return Response(serializer.data)

    @action(methods=['get'], detail=True)
    def review_logs(self, request, *args, **kwargs):
        instance = self.get_object()
        review_logs = instance.review_logs.order_by('created_at')
        data = TestCaseReviewLogSerializer(review_logs, many=True).data
        return api_success(data=data)

    # 筛选列表中全部用例删除
    @action(methods=['post'], detail=False)
    def list_delete(self, request, *args, **kwargs):
        queryset = self.get_new_queryset()
        queryset = self.filter_queryset(queryset)
        queryset.update(is_active=False)
        return api_success()

    # 筛选列表中全部用例移动
    @action(methods=['patch'], detail=False)
    def list_move(self, request, *args, **kwargs):
        queryset = self.get_new_queryset()
        cases = self.filter_queryset(queryset)
        target_module = get_object_or_404(TestCaseModule, pk=request.data.get('target_module'))
        if cases:
            if cases.first().library.id != target_module.library_id:
                return api_bad_request("用例只能在本用例库中移动")
        for obj in cases:
            origin_module = obj.module
            module_changed = target_module.id != origin_module.id
            if module_changed:
                obj.module_id = target_module.id
                obj.hauler_id = request.top_user.id
                obj.index = 0
                obj.created_at = timezone.now()
                if module_changed:
                    obj.status = 'pending'
                obj.save()
        return api_success()

    @action(methods=['post'], detail=False)
    def batch_delete(self, request, *args, **kwargs):
        queryset = self.queryset
        cases_ids = request.data.get('cases', [])
        if cases_ids:
            queryset.filter(pk__in=cases_ids).update(is_active=False)
        return api_success()

    @action(methods=['patch'], detail=False)
    def batch_move(self, request, *args, **kwargs):
        queryset = self.queryset
        cases_ids = request.data.get('cases', [])
        target_module = get_object_or_404(TestCaseModule, pk=request.data.get('target_module'))
        cases = queryset.filter(pk__in=cases_ids).order_by('created_at')
        library_ids = set([case.module.library_id for case in cases])
        if len(library_ids) > 1:
            return api_bad_request("所选用例应该属于同一个用例库")
        if library_ids:
            origin_library_id = list(library_ids)[0]
            if origin_library_id != target_module.library_id:
                return api_bad_request("用例只能在本用例库中移动")
        if not len(library_ids):
            return api_bad_request("没有选中任何有效用例")

        for obj in cases:
            origin_module = obj.module
            module_changed = target_module.id != origin_module.id
            if module_changed:
                obj.module_id = target_module.id
                obj.hauler_id = request.top_user.id
                obj.created_at = timezone.now()
                obj.index = 0
                obj.status = 'pending'
                obj.save()

        return api_success()

    # 同一个模块用例下拖拽
    @action(methods=['patch'], detail=False)
    def drag(self, request, *args, **kwargs):
        return drag_same_level_obj(request, self.queryset)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return api_success()

    @action(methods=['get'], detail=False)
    def batch_export(self, request, *args, **kwargs):
        case_ids = re.sub(r'[;；,，]', ' ', self.request.query_params.get('cases', '')).split()
        queryset = TestCase.active_cases().filter(pk__in=case_ids).order_by('created_at')
        library_ids = set([case.module.library_id for case in queryset])
        if len(library_ids) > 1:
            return api_bad_request("所选用例应该属于同一个用例库")
        if not len(library_ids):
            return api_bad_request("没有选中任何有效用例")
        serializer = self.get_serializer(queryset, many=True)
        case_list = serializer.data
        res_data = self.make_groups(case_list)
        return api_success(res_data)

    @action(methods=['get'], detail=False)
    def list_export(self, request, *args, **kwargs):
        queryset = self.get_new_queryset()
        queryset = self.filter_queryset(queryset)
        serializer = self.get_serializer(queryset, many=True)
        case_list = serializer.data
        res_data = self.make_groups(case_list)
        return api_success(res_data)


@method_decorator(request_params_required(['status']), name='list')
@method_decorator(request_params_required(['status']), name='filter_data')
class ProjectViewSet(viewsets.ReadOnlyModelViewSet):
    """
    项目列表
    """
    serializer_class = ProjectListSerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    search_fields = ('name', 'manager__username', 'test__username')

    filter_fields = ('managers', 'tests')
    filter_class = ProjectFilter
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        """
           A viewset that provides default `create()`, `retrieve()`, `update()`,
           `partial_update()`, `destroy()` and `list()` actions.
           """

        if self.action == 'list':
            self.serializer_class = ProjectListSerializer

        elif self.action == 'retrieve':
            self.serializer_class = ProjectDetailSerializer

        return super(ProjectViewSet, self).get_serializer_class()

    def get_queryset(self):
        page = self.request.query_params.get('page')
        page_size = self.request.query_params.get('page_size')
        if not all([page, page_size]):
            self.pagination_class = None

        top_user = self.request.top_user
        user_projects = Project.top_user_projects(top_user)
        user_projects_ids = set(user_projects.values_list('id', flat=True))

        queryset = Project.objects.none()

        if top_user.is_freelancer:
            queryset = user_projects
        elif top_user.is_employee:
            if has_function_perms(top_user.user, 'view_all_projects'):
                queryset = Project.objects.all()
            else:
                if has_function_perms(top_user.user, 'view_ongoing_projects'):
                    queryset = queryset | Project.ongoing_projects()
                if has_function_perms(top_user.user, 'view_projects_finished_in_60_days'):
                    queryset = queryset | Project.completion_projects().filter(
                        done_at__gte=timezone.now() - timedelta(days=60))

        status_value = self.request.query_params.get('status')
        if status_value == 'ongoing':
            user_projects = user_projects.filter(done_at__isnull=True).order_by('-created_at')
            other_projects = queryset.filter(done_at__isnull=True).exclude(
                pk__in=user_projects_ids).order_by(
                '-created_at')
            return (user_projects | other_projects).distinct()

        elif status_value == 'closed':
            user_projects = user_projects.filter(done_at__isnull=False).order_by('-done_at')
            other_projects = queryset.filter(done_at__isnull=False).exclude(
                pk__in=user_projects_ids).order_by(
                '-done_at')
            return (user_projects | other_projects).distinct()
        return queryset

    def list(self, request, *args, **kwargs):
        status_value = self.request.query_params.get('status')
        if status_value:
            if status_value not in ['ongoing', 'closed']:
                return api_bad_request('项目状态的可选值为ongoing、closed')

        queryset = self.filter_queryset(self.get_queryset())
        cache_key = 'top-user-{}-favorite-projects'.format(request.top_user.id)
        favorite_projects = cache.get(cache_key, set())
        status_sort_keys = {
            'prd': 5,
            'design': 4,
            'development': 3,
            'test': 1,
            'acceptance': 2,
        }

        queryset_list = queryset
        status_value = self.request.query_params.get('status')
        if status_value == 'ongoing':
            queryset_list = sorted(queryset, key=lambda q: (
                not (q.id in favorite_projects), sorted([status_sort_keys[i] for i in q.status], reverse=False),
                q.created_at))
        elif status_value == 'closed':
            queryset_list = sorted(queryset, key=lambda q: (q.id in favorite_projects, q.done_at), reverse=True)

        page = self.paginate_queryset(queryset_list)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            data = serializer.data
            for p in data:
                p['favorite'] = p['id'] in favorite_projects
            return self.get_paginated_response(data)
        serializer = self.get_serializer(queryset_list, many=True)
        data = serializer.data
        for p in data:
            p['favorite'] = p['id'] in favorite_projects
        return Response(data)

    @action(methods=['get'], detail=False)
    def filter_data(self, request, *args, **kwargs):
        status_value = self.request.query_params.get('status')
        if status_value:
            if status_value not in ['ongoing', 'closed']:
                return api_bad_request('项目状态的可选值为ongoing、closed')

        queryset = self.get_queryset()
        managers = set()
        tests = set()
        developer_tests = set()
        for obj in queryset:
            if obj.manager:
                managers.add(obj.manager)
            for test in obj.tests.all():
                tests.add(test)
            job_positions = obj.job_positions.filter(role__name='测试工程师')
            for job_position in job_positions:
                developer_tests.add(job_position.developer)
        managers_data = [get_top_user_data(user=user) for user in managers]
        tests_data = [get_top_user_data(user=user) for user in tests]
        developer_tests_data = [get_top_user_data(developer=developer) for developer in developer_tests]
        tests_data = tests_data + developer_tests_data
        managers_data = sorted(managers_data, key=lambda x: x['username'])
        tests_data = sorted(tests_data, key=lambda x: x['username'])
        return api_success({"tests": tests_data, 'managers': managers_data})


@api_view(['GET'])
def project_members(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    members = ProjectDetailSerializer(project).data['members']
    data = [m for m in members if m['is_active']]
    return api_success(data)


@api_view(['POST'])
def project_favorite_toggle(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    cache_key = 'top-user-{}-favorite-projects'.format(request.top_user.id)
    favorite_projects = cache.get(cache_key, set())
    if project.id in favorite_projects:
        favorite_projects.remove(project.id)
    else:
        favorite_projects.add(project.id)

    cache.set(cache_key, favorite_projects, None)
    return api_success()


@method_decorator(request_params_required('project'), name='list')
class ProjectPlatformViewSet(viewsets.ModelViewSet):
    """
    项目平台
    """
    queryset_model = ProjectPlatform
    queryset = ProjectPlatform.objects.order_by('created_at')
    serializer_class = ProjectPlatformSerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter,)

    def get_serializer_class(self):
        """
           A viewset that provides default `create()`, `retrieve()`, `update()`,
           `partial_update()`, `destroy()` and `list()` actions.
           """
        if self.action in ['update', 'partial_update']:
            self.serializer_class = ProjectPlatformUpdateSerializer
        return super(ProjectPlatformViewSet, self).get_serializer_class()

    def get_queryset(self):
        queryset = ProjectPlatform.objects.order_by('created_at')
        project = self.request.query_params.get('project')
        if project:
            return queryset.filter(project_id=project).order_by('created_at')
        return queryset

    def create(self, request, *args, **kwargs):
        """创建"""
        top_user = self.request.top_user
        request_data = deepcopy(request.data)
        request_data['creator'] = top_user.id
        name = request_data.get('name')
        # 默认的处理
        if name:
            request_data['name'] = self.build_platform_name(name)

        serializer = self.get_serializer(data=request_data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return api_created_success(serializer.data)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_default:
            return api_bad_request("默认平台不允许编辑")
        name = request.data.get('name')
        # 默认的处理
        if name:
            request.data['name'] = self.build_platform_name(name)
        return super().update(request, *args, **kwargs)

    def build_platform_name(self, name):
        name = name.strip()
        for default_name in self.queryset_model.DEFAULT_DATA:
            if name.lower() == default_name.lower():
                return default_name
        return name

    @action(methods=['get'], detail=False)
    def default_data(self, request, *args, **kwargs):
        return api_success(list(ProjectPlatform.DEFAULT_DATA))

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.test_case_modules.exists():
            return api_bad_request('该平台下已有测试用例模块，不允许删除')
        if instance.test_cases.exists():
            return api_bad_request('该平台下已有测试用例，不允许删除')
        if instance.test_plans.exists():
            return api_bad_request('该平台下已有测试计划，不允许删除')
        if instance.bugs.exists():
            return api_bad_request('该平台下已有bug，不允许删除')
        return super().destroy(request, *args, **kwargs)


@method_decorator(request_params_required('project'), name='list')
class ProjectTagViewSet(viewsets.ReadOnlyModelViewSet):
    """
    项目标签
    """
    queryset_model = ProjectTag
    serializer_class = ProjectTagSerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter,)

    def get_serializer_class(self):
        """
           A viewset that provides default `retrieve()` `list()` actions.
           """
        if self.action == 'list':
            self.serializer_class = ProjectTagListSerializer

        return super(ProjectTagViewSet, self).get_serializer_class()

    def get_queryset(self):
        queryset = self.queryset_model.objects.order_by('index')
        project_id = self.request.query_params.get('project')

        if project_id:
            project = get_object_or_404(Project, pk=project_id)
            self.queryset_model.init_data(project)
            return queryset.filter(project_id=project.id).order_by('index')
        return queryset


@method_decorator(
    request_data_fields_required(['origin_id', 'target_parent_id', 'target_previous_id', 'target_next_id']),
    name='drag_tree')
class ProjectTestCaseModuleViewSet(viewsets.ModelViewSet):
    """
    项目用例模块
    """
    # queryset = ProjectTestCaseModule.objects.order_by('created_at')
    queryset_model = ProjectTestCaseModule
    queryset = ProjectTestCaseModule.objects.all()
    serializer_class = ProjectTestCaseModuleSerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter,)
    search_fields = ('name', 'description',)

    def get_serializer_class(self):
        """
           A viewset that provides default `create()`, `retrieve()`, `update()`,
           `partial_update()`, `destroy()` and `list()` actions.
           """
        with_cases = self.request.query_params.get('with_cases') in ['True', 'true', '1', True, 1]

        if self.action in ['update', 'partial_update']:
            self.serializer_class = ProjectTestCaseModuleUpdateSerializer
        elif self.action == 'list':
            project = self.request.query_params.get('project')
            platform = self.request.query_params.get('platform')
            if project or platform:
                self.serializer_class = ProjectTestCaseModuleWithChildrenSerializer
            if with_cases:
                self.serializer_class = ProjectTestCaseModuleWithChildrenWithCaseSerializer

        return super(ProjectTestCaseModuleViewSet, self).get_serializer_class()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        platform_id = self.request.query_params.get('platform')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            data = serializer.data
            new_data = self.build_clean_data_filter_platform(data, platform_id)
            return self.get_paginated_response(new_data)
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data
        new_data = self.build_clean_data_filter_platform(data, platform_id)
        return Response(new_data)

    def build_clean_data_filter_platform(self, data, platform_id):
        with_cases = self.request.query_params.get('with_cases') in ['True', 'true', '1', True, 1]
        if platform_id:
            new_data = []
            platform_id_str = str(platform_id)
            for item in data:
                module_platforms_ids = [str(platform['id']) for platform in item['platforms']]
                if platform_id_str in module_platforms_ids:
                    children = item.get('children', [])
                    if children:
                        item['children'] = self.build_clean_data_filter_platform(children, platform_id)
                    else:
                        item['children'] = []
                    if with_cases:
                        test_cases = []
                        approved_test_cases = []
                        for case in item['test_cases']:
                            case_platforms_ids = [str(platform['id']) for platform in case['platforms']]
                            if platform_id_str in case_platforms_ids:
                                test_cases.append(case)
                        for case in item['approved_test_cases']:
                            case_platforms_ids = [str(platform['id']) for platform in case['platforms']]
                            if platform_id_str in case_platforms_ids:
                                approved_test_cases.append(case)
                        item['test_cases'] = test_cases
                        item['approved_test_cases'] = approved_test_cases
                        item['approved_test_cases_count'] = len(approved_test_cases)
                    new_data.append(item)
            return new_data
        else:
            return data

    def get_queryset(self):
        queryset = ProjectTestCaseModule.objects.all()
        project = self.request.query_params.get('project')
        platform = self.request.query_params.get('platform')
        if project:
            queryset = queryset.filter(project_id=project, parent_id=None).order_by('index')
        if platform:
            queryset = queryset.filter(platforms__id=platform, parent_id=None).distinct().order_by('index')
        return queryset

    def create(self, request, *args, **kwargs):
        """创建"""
        top_user = self.request.top_user
        request_data = deepcopy(request.data)
        request_data['creator'] = top_user.id
        serializer = self.get_serializer(data=request_data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        parent = validated_data.get('parent')
        project = validated_data.get('project')
        platforms = validated_data.get('platforms')
        if parent and parent.project_id != project.id:
            return api_bad_request("父级模块的项目、 和所选项目不一致")
        if platforms:
            for platform in platforms:
                if platform.project_id != project.id:
                    return api_bad_request("所选平台不属于该项目")
                if parent:
                    if not parent.platforms.filter(pk=platform.id).exists():
                        return api_bad_request("平台必须包含在父级模块中")
        else:
            return api_bad_request("平台必选")

        self.perform_create(serializer)
        return api_created_success(serializer.data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        origin_platforms = deepcopy(instance.platforms.all())
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        new_platforms = validated_data.get('platforms', None)
        if new_platforms is not None:
            new_platforms_id = [item.id for item in new_platforms]
            for platform in origin_platforms:
                if platform.id not in new_platforms_id:
                    if instance.test_cases.filter(platforms__id=platform.id).exists():
                        return api_bad_request('该模块下 已存在{}平台的用例 不能解除关联'.format(platform.name))
                    if instance.children.filter(platforms__id=platform.id).exists():
                        return api_bad_request('该模块下 已存在{}平台的子模块 不能解除关联'.format(platform.name))
        self.perform_update(serializer)
        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}
        return Response(serializer.data)

    # 项目用例库 同级模块拖拽
    @action(methods=['patch'], detail=False)
    def drag(self, request, *args, **kwargs):
        return drag_same_level_obj(request, self.queryset)

    # 项目用例库 模块拖拽
    @action(methods=['patch'], detail=False)
    def drag_tree(self, request, *args, **kwargs):
        return drag_sort_tree_obj(request, self.queryset)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # 模块 包含用例 不能删除
        # 模块 包含bug  不能删除
        if instance.contained_test_cases.exists():
            return api_bad_request('该模块或其子模块下包含用例 不能删除')
        if instance.contained_bugs.exists():
            return api_bad_request('该模块或其子模块下包含Bug 不能删除')
        return super().destroy(request, *args, **kwargs)


@method_decorator(request_data_fields_required(['project', 'module', 'platforms']), name='create')
@method_decorator(request_data_fields_required(['module', 'platforms']), name='update')
@method_decorator(request_data_fields_required(['cases', 'module', 'platforms']),
                  name='import_from_library')
@method_decorator(request_params_required('cases'),
                  name='batch_export')
@method_decorator(project_test_cases_params_verify, name='list')
@method_decorator(project_test_cases_params_verify, name='list_groups')
@method_decorator(project_test_cases_params_verify, name='filter_data')
@method_decorator(project_test_cases_params_verify, name='statistics_data')
@method_decorator(project_test_cases_params_verify, name='list_clone')
@method_decorator(project_test_cases_params_verify, name='list_move')
@method_decorator(project_test_cases_params_verify, name='list_delete')
@method_decorator(project_test_cases_batch_copy_params_verify(), name='batch_move')
@method_decorator(project_test_cases_batch_copy_params_verify(), name='batch_clone')
@method_decorator(project_test_cases_batch_copy_params_verify(required_params=['target_module', 'platforms']),
                  name='list_clone')
@method_decorator(project_test_cases_batch_copy_params_verify(required_params=['target_module', 'platforms']),
                  name='list_move')
class ProjectTestCaseViewSet(viewsets.ModelViewSet):
    """
    项目用例
    """
    queryset = ProjectTestCase.active_cases()
    serializer_class = ProjectTestCaseSerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter,)
    search_fields = ('description',)

    filter_fields = ('status', 'tags', 'creators', 'cases', 'case_type', 'flow_type')
    filter_class = ProjectTestCaseFilter
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        """
           A viewset that provides default `create()`, `retrieve()`, `update()`,
           `partial_update()`, `destroy()` and `list()` actions.
           """
        if self.action in ['update', 'partial_update']:
            self.serializer_class = ProjectTestCaseUpdateSerializer
        return super(ProjectTestCaseViewSet, self).get_serializer_class()

    def get_queryset_by_params(self):
        queryset = ProjectTestCase.active_cases()
        project = self.request.query_params.get('project')
        platform = self.request.query_params.get('platform')
        module = self.request.query_params.get('module')
        if module:
            queryset = queryset.filter(module_id=module).order_by('created_at')
        elif platform:
            queryset = queryset.filter(platforms__id=platform).order_by('created_at')
        elif project:
            queryset = queryset.filter(module__project_id=project).order_by('created_at')
        return queryset

    def get_queryset(self):
        queryset = self.get_queryset_by_params()
        page = self.request.query_params.get('page')
        page_size = self.request.query_params.get('page_size')
        if not all([page, page_size]):
            self.pagination_class = None
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def get_new_queryset(self):
        project = self.request.query_params.get('project')
        platform = self.request.query_params.get('platform')
        module = self.request.query_params.get('module')
        queryset = ProjectTestCase.active_cases()
        if module:
            module_obj = get_object_or_404(ProjectTestCaseModule, pk=module)
            queryset = module_obj.contained_test_cases.order_by('created_at')
        elif platform:
            queryset = queryset.filter(platforms__id=platform).order_by('created_at')
        elif project:
            queryset = queryset.filter(module__project_id=project).order_by('created_at')
        return queryset

    @action(methods=['get'], detail=False)
    def list_groups(self, request, *args, **kwargs):
        queryset = self.get_new_queryset()
        queryset = self.filter_queryset(queryset)
        page = self.request.query_params.get('page')
        page_size = self.request.query_params.get('page_size')
        if not all([page, page_size]):
            self.pagination_class = None

        ordering = self.request.query_params.get('ordering', None)
        if not ordering:
            queryset = queryset.order_by('module__full_index')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            case_list = serializer.data
            res_data = self.make_groups(case_list)
            return self.get_paginated_response(res_data)

        serializer = self.get_serializer(queryset, many=True)
        case_list = serializer.data
        res_data = self.make_groups(case_list)
        return Response(res_data)

    @staticmethod
    def make_groups(case_list):
        case_data = {}
        for query in case_list:

            module_id = query['module']['id']
            if module_id not in case_data:
                case_data[module_id] = deepcopy(query['module'])
                case_data[module_id]['cases'] = []
            case_data[module_id]['cases'].append(query)
        for key in case_data:
            case_data[key]['cases'] = sorted(case_data[key]['cases'], key=lambda x: x['index'], reverse=False)
        case_data = sorted(case_data.values(), key=lambda x: x['full_index'], reverse=False)
        return case_data

    @staticmethod
    def make_groups_by_platform(case_list, platform_id=None):
        platforms_case_data = {}
        for case in case_list:
            for platform_data in case['platforms']:
                platform_name = platform_data['name']

                if platform_id and str(platform_data['id']) != str(platform_id):
                    continue

                if platform_name not in platforms_case_data:
                    platforms_case_data[platform_name] = deepcopy(platform_data)
                    platforms_case_data[platform_name]['case_data'] = {}
                case_data = platforms_case_data[platform_name]['case_data']
                module_id = case['module']['id']
                if module_id not in case_data:
                    case_data[module_id] = deepcopy(case['module'])
                    case_data[module_id]['module_full_name'] = case['module']['full_name']
                    case_data[module_id]['cases'] = []
                case_data[module_id]['cases'].append(case)

        for platform_name in platforms_case_data:
            case_data = platforms_case_data[platform_name]['case_data']
            for key in case_data:
                case_data[key]['cases'] = sorted(case_data[key]['cases'], key=lambda x: x['index'], reverse=False)
            case_data = sorted(case_data.values(), key=lambda x: x['full_index'], reverse=False)
            platforms_case_data[platform_name]['case_data'] = case_data

        platforms_case_data = sorted(platforms_case_data.values(), key=lambda x: ['created_at'],
                                     reverse=False)
        return platforms_case_data

    @action(methods=['get'], detail=False)
    def filter_data(self, request, *args, **kwargs):
        queryset = self.get_new_queryset()
        status_data = [{'value': value, 'label': label} for value, label in ProjectTestCase.STATUS_CHOICES]
        case_type_data = [{'value': value, 'label': label} for value, label in ProjectTestCase.CASE_TYPE]
        flow_type_data = [{'value': value, 'label': label} for value, label in ProjectTestCase.FLOW_TYPE]
        creators = set()
        tags = set()

        for q in queryset:
            if q.creator:
                creators.add(q.creator)
            for t in q.tags.all():
                tags.add(t)

        creators_data = TopUserSimpleViewSerializer(creators, many=True).data
        creators_data = sorted(creators_data, key=lambda x: lazy_pinyin(x['username']))
        tags_data = ProjectTagListSerializer(tags, many=True).data
        tags_data = sorted(tags_data, key=lambda x: x['index'])
        return api_success(
            {"status": status_data, 'creators': creators_data, 'tags': tags_data, 'case_type': case_type_data,
             'flow_type': flow_type_data})

    @action(methods=['get'], detail=False)
    def statistics_data(self, request, *args, **kwargs):
        queryset = self.get_new_queryset()
        queryset = self.filter_queryset(queryset)
        data = {'total': queryset.count()}
        for value, label in ProjectTestCase.STATUS_CHOICES:
            data[value] = queryset.filter(status=value).count()
        return api_success(data)

    def build_project_tags(self, request_data, project_id):
        tags = request_data.get('tags', None)
        if tags is not None:
            tag_ids = set()
            if tags:
                for name in tags:
                    tag, created = ProjectTag.objects.get_or_create(project_id=project_id, name=name)
                    tag_ids.add(tag.id)
            request_data['tags'] = list(tag_ids)
        return request_data

    def create(self, request, *args, **kwargs):
        """创建"""
        top_user = self.request.top_user
        user = top_user.user
        request_data = deepcopy(request.data)
        request_data['creator'] = top_user.id
        project_id = request_data.get('project')
        request_data = self.build_project_tags(request_data, project_id)
        if request_data['case_type'] == 'no_smoking' and request_data['flow_type'] == 'others':
            request_data['status'] = 'approved'
        serializer = self.get_serializer(data=request_data)

        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data
        project = validated_data.get('project')
        module = validated_data.get('module')
        platforms = validated_data.get('platforms')
        if module.project_id != project.id:
            return api_bad_request("父级模块的项目、 和所选项目不一致")

        if platforms:
            for platform in platforms:
                if platform.project_id != project.id:
                    return api_bad_request("所选平台不属于该项目")
                if not module.platforms.filter(pk=platform.id).exists():
                    return api_bad_request("所选平台不属于该模块")
        else:
            return api_bad_request("平台必选")
        instance = serializer.save()
        project_obj = get_object_or_404(Project, pk=project_id)
        if (project_obj.manager and project_obj.manager == user) or (
                project_obj.product_manager and project_obj.product_manager == user):
            instance.status = 'approved'
            instance.save()
        ProjectTestCaseReviewLog.build_create_object_log(request.top_user, instance)
        return api_created_success(serializer.data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        origin = deepcopy(instance)
        project = instance.project
        request_data = deepcopy(request.data)
        request_data = self.build_project_tags(request_data, project.id)

        serializer = self.get_serializer(instance, data=request_data, partial=partial)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        module = validated_data.get('module')
        platforms = validated_data.get('platforms')
        if module.project_id != project.id:
            return api_bad_request("父级模块的项目、 和所选项目不一致")
        if platforms:
            for platform in platforms:
                if platform.project_id != project.id:
                    return api_bad_request("所选平台不属于该项目")
                if not module.platforms.filter(pk=platform.id).exists():
                    return api_bad_request("所选平台不属于该模块")
        else:
            return api_bad_request("平台必选")
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        if origin.status == 'rejected' and instance.status == 'rejected':
            editable_fields = ['description', 'precondition', 'expected_result']
            for field in editable_fields:
                if getattr(origin, field) != getattr(instance, field):
                    instance.status = 'pending'
                    instance.save()
                    break
        if (origin.case_type == 'no_smoking' and origin.flow_type == 'others') and (
                instance.case_type != 'no_smoking' or instance.flow_type != 'others') and not instance.review_logs.filter(
            log_type__in=['approved', 'rejected']):
            instance.status = 'pending'
            instance.save()
        serializer = ProjectTestCaseSerializer(instance)
        ProjectTestCaseReviewLog.build_update_object_log(request.top_user, origin, instance)
        return Response(serializer.data)

    @action(methods=['patch'], detail=True, serializer_class=ProjectTestCaseStatusSerializer)
    def status(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}
        ProjectTestCaseReviewLog.build_log(request.top_user, instance, log_type=request.data.get('status', None),
                                           remarks=request.data.get('remarks', ''))
        return Response(serializer.data)

    def move_cases(self, cases, target_project, target_module, platforms_ids):
        origin_project_id = cases.first().project.id
        is_same_project = target_project.id == origin_project_id
        case_update_data = {"project": target_project.id, 'module': target_module.id,
                            'platforms': platforms_ids, 'tags': [], 'status': 'pending', 'index': 0}
        for case in cases:
            origin_case = deepcopy(case)
            case_data = deepcopy(case_update_data)
            case_data['created_at'] = timezone.now()
            if is_same_project:
                case_data['tags'] = case.tags.values_list('id', flat=True)
            serializer = self.get_serializer(case, data=case_data, partial=True)
            serializer.is_valid(raise_exception=True)
            new_case = serializer.save()
            ProjectTestCaseReviewLog.build_update_object_log(self.request.top_user, origin_case, new_case, remarks="移动")

    @action(methods=['patch'], detail=False)
    def list_move(self, request, *args, **kwargs):
        queryset = self.get_new_queryset()
        queryset = self.filter_queryset(queryset)

        target_module = ProjectTestCaseModule.objects.get(pk=request.data.get('target_module'))
        target_project = target_module.project
        platforms_ids = ProjectPlatform.objects.filter(pk__in=request.data.get('platforms')).values_list('id',
                                                                                                         flat=True)
        if queryset:
            self.move_cases(queryset, target_project, target_module, platforms_ids)
        return api_success()

    @action(methods=['patch'], detail=False)
    def batch_move(self, request, *args, **kwargs):
        target_module = ProjectTestCaseModule.objects.get(pk=request.data.get('target_module'))
        target_project = target_module.project
        platforms_ids = ProjectPlatform.objects.filter(pk__in=request.data.get('platforms')).values_list('id',
                                                                                                         flat=True)
        cases = ProjectTestCase.active_cases().filter(pk__in=request.data.get('cases')).order_by('created_at')
        if cases:
            self.move_cases(cases, target_project, target_module, platforms_ids)
        return api_success()

    @action(methods=['post'], detail=False)
    def batch_delete(self, request, *args, **kwargs):
        queryset = self.queryset
        cases = request.data.get('cases')
        if cases:
            queryset.filter(pk__in=cases).update(is_active=False)
        return api_success()

    @action(methods=['post'], detail=False)
    def list_delete(self, request, *args, **kwargs):
        queryset = self.get_new_queryset()
        queryset = self.filter_queryset(queryset)
        queryset.update(is_active=False)
        return api_success()

    def clone_cases(self, request, cases, target_project, target_module, platforms_ids):
        origin_project_id = cases.first().project.id
        is_same_project = target_project.id == origin_project_id
        case_data_template = {'project': target_project.id, 'module': target_module.id,
                              'platforms': platforms_ids, 'description': None, 'precondition': None,
                              'expected_result': None}
        for case in cases:
            case_data = deepcopy(case_data_template)
            fields = ['description', 'precondition', 'expected_result']
            for field in fields:
                case_data[field] = getattr(case, field)
            case_data['creator'] = request.top_user.id
            if is_same_project:
                case_data['tags'] = case.tags.values_list('id', flat=True)
            serializer = self.get_serializer(data=case_data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)

    @action(methods=['post'], detail=False)
    def batch_clone(self, request, *args, **kwargs):
        target_module = ProjectTestCaseModule.objects.get(pk=request.data.get('target_module'))
        target_project = target_module.project

        platforms_ids = ProjectPlatform.objects.filter(pk__in=request.data.get('platforms')).values_list('id',
                                                                                                         flat=True)
        cases = ProjectTestCase.active_cases().filter(pk__in=request.data.get('cases')).order_by('created_at')
        if cases:
            self.clone_cases(request, cases, target_project, target_module, platforms_ids)

        return api_success()

    # 复制筛选的列表
    @action(methods=['post'], detail=False)
    def list_clone(self, request, *args, **kwargs):
        target_module = ProjectTestCaseModule.objects.get(pk=request.data.get('target_module'))
        target_project = target_module.project
        platforms_ids = ProjectPlatform.objects.filter(pk__in=request.data.get('platforms')).values_list('id',
                                                                                                         flat=True)
        queryset = self.get_new_queryset()
        cases = self.filter_queryset(queryset)
        if cases:
            self.clone_cases(request, cases, target_project, target_module, platforms_ids)
        return api_success()

    @action(methods=['get'], detail=False)
    def batch_export(self, request, *args, **kwargs):

        case_ids = re.sub(r'[;；,，]', ' ', self.request.query_params.get('cases', '')).split()
        queryset = ProjectTestCase.active_cases().filter(pk__in=case_ids).order_by('created_at')
        project_ids = set(queryset.values_list('project_id', flat=True))
        if len(project_ids) > 1:
            return api_bad_request("所移动的用例 不属于同一个项目")
        if not len(project_ids):
            return api_bad_request("没有选中任何有效用例")
        serializer = self.get_serializer(queryset, many=True)
        case_list = serializer.data

        platform_id = self.request.query_params.get('platform', None)
        res_data = self.make_groups_by_platform(case_list, platform_id=platform_id)

        project = queryset.first().project
        return self.build_cases_export_excel_response(res_data, project)

    @action(methods=['get'], detail=False)
    def list_export(self, request, *args, **kwargs):
        queryset = self.get_new_queryset()
        queryset = self.filter_queryset(queryset)
        if not len(queryset):
            return api_bad_request("没有任何有效用例")
        serializer = self.get_serializer(queryset, many=True)
        case_list = serializer.data
        platform_id = self.request.query_params.get('platform', None)
        res_data = self.make_groups_by_platform(case_list, platform_id=platform_id)
        project = queryset.first().project
        return self.build_cases_export_excel_response(res_data, project)

    @staticmethod
    def build_cases_export_excel_response(res_data, project):
        from wsgiref.util import FileWrapper
        from django.http import FileResponse
        from django.utils.encoding import escape_uri_path
        from django.conf import settings
        import xlwt
        from xlwt import Workbook
        export_fields = [
            {'field_name': 'module_full_name', 'verbose_name': '用例模块（必填）', 'col_width': 30},
            {'field_name': 'case_type', 'verbose_name': '是否冒烟', 'col_width': 30},
            {'field_name': 'flow_type', 'verbose_name': '用例类型', 'col_width': 30},
            {'field_name': 'description', 'verbose_name': '用例描述（必填）', 'col_width': 36},
            {'field_name': 'precondition', 'verbose_name': '前置条件', 'col_width': 36},
            {'field_name': 'expected_result', 'verbose_name': '预期结果（必填）', 'col_width': 36},
            {'field_name': 'tags_str', 'verbose_name': '标签', 'col_width': 36},
        ]
        w = Workbook()  # 创建一个工作簿
        alignment = xlwt.Alignment()  # Create Alignment
        # May be: HORZ_GENERAL, HORZ_LEFT, HORZ_CENTER, HORZ_RIGHT,
        # HORZ_FILLED, HORZ_JUSTIFIED, HORZ_CENTER_ACROSS_SEL, HORZ_DISTRIBUTED
        # alignment.horz = xlwt.Alignment.HORZ_CENTER  # 水平居中
        # May be: VERT_TOP, VERT_CENTER, VERT_BOTTOM, VERT_JUSTIFIED, VERT_DISTRIBUTED
        alignment.vert = xlwt.Alignment.VERT_CENTER  # 垂直居中
        style = xlwt.XFStyle()  # Create Style
        style.alignment = alignment  # Add Alignment to Style

        for platform_data in res_data:
            sheet_name = platform_data['name']
            ws = w.add_sheet(sheet_name)  # 创建一个工作表
            # 写表头
            for index_num, field in enumerate(export_fields):
                ws.write(0, index_num, field['verbose_name'], style)
            # 表头宽度
            for i in range(len(export_fields)):
                ws.col(i).width = 256 * export_fields[i]['col_width']

            case_index = 1
            for index_num, module_data in enumerate(platform_data['case_data']):
                for case_data in module_data['cases']:
                    # 案例的数据
                    case_fields_value = []
                    for field in export_fields:
                        case_fields_value.append(case_data.get(field['field_name']))
                    # 写入案例列表的单元格
                    for field_num, field_value in enumerate(case_fields_value):
                        ws.write(case_index, field_num, field_value, style)
                    case_index += 1

        file_path = settings.MEDIA_ROOT + 'testing/project-{}-cases-{}.xls'.format(project.id,
                                                                                   timezone.now().strftime(
                                                                                       '%Y_%m_%d_%H_%M_%S'))
        dir_path = os.path.dirname(file_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        w.save(file_path)  # 保存
        # datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
        filename = "{}-用例列表-{}.xls".format(project.name, timezone.now().strftime(
            '%Y_%m_%d_%H_%M_%S'))
        wrapper = FileWrapper(open(file_path, 'rb'))
        response = FileResponse(wrapper, content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = "attachment; filename*=utf-8''{}".format(escape_uri_path(filename))
        response['Access-Control-Expose-Headers'] = 'Content-Disposition'
        return response

    @staticmethod
    def build_cases_with_merge_cell_export_excel_response(res_data, project):
        from wsgiref.util import FileWrapper
        from django.http import FileResponse
        from django.utils.encoding import escape_uri_path
        from django.conf import settings
        import xlwt
        from xlwt import Workbook
        module_export_fields = [
            {'field_name': 'module_full_name', 'verbose_name': '模块名称', 'col_width': 20}
        ]
        case_export_fields = [
            {'field_name': 'description', 'verbose_name': '用例描述', 'col_width': 32},
            {'field_name': 'precondition', 'verbose_name': '前置条件', 'col_width': 32},
            {'field_name': 'expected_result', 'verbose_name': '预期结果', 'col_width': 32}
        ]
        module_fields = [item['field_name'] for item in module_export_fields]
        case_fields = [item['field_name'] for item in case_export_fields]
        module_fields_length = len(module_fields)
        case_fields_length = len(case_fields)
        w = Workbook()  # 创建一个工作簿
        export_fields = []
        export_fields.extend(module_export_fields)
        export_fields.extend(case_export_fields)

        alignment = xlwt.Alignment()  # Create Alignment
        # May be: HORZ_GENERAL, HORZ_LEFT, HORZ_CENTER, HORZ_RIGHT,
        # HORZ_FILLED, HORZ_JUSTIFIED, HORZ_CENTER_ACROSS_SEL, HORZ_DISTRIBUTED
        # alignment.horz = xlwt.Alignment.HORZ_CENTER  # 水平居中
        # May be: VERT_TOP, VERT_CENTER, VERT_BOTTOM, VERT_JUSTIFIED, VERT_DISTRIBUTED
        alignment.vert = xlwt.Alignment.VERT_CENTER  # 垂直居中
        style = xlwt.XFStyle()  # Create Style
        style.alignment = alignment  # Add Alignment to Style

        for platform_data in res_data:
            sheet_name = platform_data['name']
            ws = w.add_sheet(sheet_name)  # 创建一个工作表
            # 写表头
            for index_num, field in enumerate(export_fields):
                ws.write(0, index_num, field['verbose_name'], style)
            # 表头宽度
            for i in range(len(export_fields)):
                ws.col(i).width = 256 * export_fields[i]['col_width']

            case_index = 1
            for index_num, module_data in enumerate(platform_data['case_data']):
                # 项目的数据
                module_fields_value = []
                for field in module_fields:
                    module_fields_value.append(module_data.get(field))

                module_case_length = 0
                for case_data in module_data['cases']:
                    # 案例的数据
                    case_fields_value = []
                    for field in case_fields:
                        case_fields_value.append(case_data.get(field))
                    # 写入案例列表的单元格
                    for field_num, field_value in enumerate(case_fields_value):
                        payment_field_num = module_fields_length + field_num
                        ws.write(case_index, payment_field_num, field_value, style)
                    module_case_length += 1
                    case_index += 1

                # 写入模块的单元格(合并单元格)
                if module_case_length:
                    bottom_row = case_index - 1
                    top_row = bottom_row - module_case_length + 1
                    for field_num, field_value in enumerate(module_fields_value):
                        project_field_num = field_num
                        ws.write_merge(top_row, bottom_row, project_field_num, project_field_num, field_value, style)
                        # ws.write_merge(top_row, bottom_row, left_column, right_column, 'Long Cell')

        file_path = settings.MEDIA_ROOT + 'testing/project-{}-cases-{}.xls'.format(project.id,
                                                                                   timezone.now().strftime(
                                                                                       '%Y_%m_%d_%H_%M_%S'))
        dir_path = os.path.dirname(file_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        w.save(file_path)  # 保存
        # datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
        filename = "{}-用例列表-{}.xls".format(project.name, timezone.now().strftime(
            '%Y_%m_%d_%H_%M_%S'))
        wrapper = FileWrapper(open(file_path, 'rb'))
        response = FileResponse(wrapper, content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = "attachment; filename*=utf-8''{}".format(escape_uri_path(filename))
        response['Access-Control-Expose-Headers'] = 'Content-Disposition'
        return response

    @action(methods=['get'], detail=False)
    def batch_export_json(self, request, *args, **kwargs):
        case_ids = re.sub(r'[;；,，]', ' ', self.request.query_params.get('cases', '')).split()
        queryset = ProjectTestCase.active_cases().filter(pk__in=case_ids).order_by('created_at')
        project_ids = set(queryset.values_list('project_id', flat=True))
        if len(project_ids) > 1:
            return api_bad_request("所移动的用例 不属于同一个项目")
        if not len(project_ids):
            return api_bad_request("没有选中任何有效用例")

        serializer = self.get_serializer(queryset, many=True)
        case_list = serializer.data

        platform_id = self.request.query_params.get('platform', None)
        res_data = self.make_groups_by_platform(case_list, platform_id=platform_id)

        return api_success(res_data)

    @action(methods=['get'], detail=False)
    def list_export_json(self, request, *args, **kwargs):
        queryset = self.get_new_queryset()
        queryset = self.filter_queryset(queryset)
        serializer = self.get_serializer(queryset, many=True)
        case_list = serializer.data

        platform_id = self.request.query_params.get('platform', None)
        res_data = self.make_groups_by_platform(case_list, platform_id=platform_id)

        return api_success(res_data)

    @action(methods=['patch'], detail=False)
    def import_from_library(self, request, *args, **kwargs):
        cases_id = request.data.get('cases')
        module_id = request.data.get('module')
        platforms_id = request.data.get('platforms')
        case_type = request.data.get('case_type')
        flow_type = request.data.get('flow_type')

        cases = TestCase.active_cases().filter(pk__in=cases_id).order_by('created_at')
        module = get_object_or_404(ProjectTestCaseModule, pk=module_id)
        platforms = ProjectPlatform.objects.filter(pk__in=platforms_id)
        project = module.project

        if platforms:
            for platform in platforms:
                if platform.project_id != project.id:
                    return api_bad_request("所选平台不属于该项目")
                if not module.platforms.filter(pk=platform.id).exists():
                    return api_bad_request("所选平台不属于该模块")
        else:
            return api_bad_request("平台必选")

        case_data_template = {'project': project.id, 'module': module.id,
                              'platforms': request.data['platforms'], 'description': None, 'precondition': None,
                              'expected_result': None, 'case_type': case_type, 'flow_type': flow_type}

        for case in cases:
            case_data = deepcopy(case_data_template)
            fields = ['description', 'precondition', 'expected_result']
            for field in fields:
                case_data[field] = getattr(case, field)
            case_data['creator'] = request.top_user.id
            serializer = self.get_serializer(data=case_data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)

        return api_success()

    # 项目用例  同一模块的项目用例拖拽
    @action(methods=['patch'], detail=False)
    def drag(self, request, *args, **kwargs):
        return drag_same_level_obj(request, self.queryset)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return api_success()

    @action(methods=['get'], detail=True)
    def operation_logs(self, request, *args, **kwargs):
        instance = self.get_object()
        review_logs = instance.review_logs.order_by('created_at')
        executed_logs = instance.executed_logs.order_by('executed_at')
        review_logs_data = ProjectTestCaseReviewLogSerializer(review_logs, many=True).data
        executed_logs_data = ProjectTestCaseExecuteLogSerializer(executed_logs, many=True).data
        data = {'review_logs': review_logs_data,
                'executed_logs': executed_logs_data}
        return api_success(data=data)

    @action(methods=['get'], detail=True)
    def review_logs(self, request, *args, **kwargs):
        instance = self.get_object()
        review_logs = instance.review_logs.order_by('created_at')
        data = ProjectTestCaseReviewLogSerializer(review_logs, many=True).data
        return api_success(data=data)

    @action(methods=['get'], detail=True)
    def executed_logs(self, request, *args, **kwargs):
        instance = self.get_object()
        executed_logs = instance.executed_logs.order_by('executed_at')
        data = ProjectTestCaseExecuteLogSerializer(executed_logs, many=True).data
        return api_success(data=data)


@method_decorator(request_params_required(['project']), name='list')
@method_decorator(request_params_required(['project']), name='filter_data')
@method_decorator(request_data_fields_required(['project', 'platform', 'modules']), name='create')
class ProjectTestPlanViewSet(ListModelMixin, CreateModelMixin, RetrieveModelMixin, GenericViewSet):
    """
    测试计划列表
    """
    serializer_class = ProjectTestPlanSerializer

    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter,)
    search_fields = ('index', 'platform__name')

    filter_fields = ('platforms',)
    filter_class = ProjectTestPlanFilter
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        """
           A viewset that provides default `create()`, `retrieve()`, `update()`,
           `partial_update()`, `destroy()` and `list()` actions.
           """
        if self.action == 'list':
            self.serializer_class = ProjectTestPlanListSerializer

        return super(ProjectTestPlanViewSet, self).get_serializer_class()

    def get_queryset(self):
        queryset = ProjectTestPlan.objects.order_by('-index')
        project = self.request.query_params.get('project')
        if project:
            queryset = queryset.filter(project_id=project).order_by('-index')

        page = self.request.query_params.get('page')
        page_size = self.request.query_params.get('page_size')
        if not all([page, page_size]):
            self.pagination_class = None

        return queryset

    @action(methods=['get'], detail=False)
    def filter_data(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        platforms = set()
        for obj in queryset:
            if obj.platform:
                platforms.add(obj.platform)

        platforms_data = [{'id': obj.id, 'name': obj.name} for obj in platforms]
        platforms_data = sorted(platforms_data, key=lambda x: x['name'])

        return api_success({"platforms": platforms_data})

    def create(self, request, *args, **kwargs):
        """创建"""
        top_user = self.request.top_user
        name = request.data.get('name', None)
        if not name:
            return api_bad_request('请填写计划名称')
        modules_id = request.data.get('modules')
        request_data = deepcopy(request.data)
        request_data['creator'] = top_user.id
        serializer = ProjectTestPlanVerifyFieldSerializer(data=request_data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        project = validated_data.get('project')
        platform = validated_data.get('platform')
        modules = validated_data.get('modules')
        test_type = request_data.get('test_type', '')
        case_tags = request_data.get('case_tags', '')
        execute_count = request_data.get('execute_count', '')

        if getattr(platform, 'project_id') != project.id:
            return api_bad_request("平台不属于该项目")

        if not modules:
            request_data.pop('modules', None)
            create_serializer = ProjectTestPlanSerializer(data=request_data)
            create_serializer.is_valid(raise_exception=True)
            create_serializer.save()
            return api_success()

        for module in modules:
            if module.project_id != project.id:
                return api_bad_request("所选模块不属于该项目")
            if not module.platforms.filter(pk=platform.id).exists():
                return api_bad_request("所选模块不属于该平台")
        all_approved_cases = ProjectTestCase.active_cases().filter(platforms__id=platform.id,
                                                                   status='approved').distinct()
        approved_cases = all_approved_cases.filter(module_id__in=modules_id).distinct()
        if not approved_cases.exists():
            return api_bad_request('未选中任何已审核通过的用例')

        if test_type:
            if test_type == 'smoking':
                approved_cases = approved_cases.filter(case_type=test_type)
            if test_type == 'main_process':
                approved_cases = approved_cases.filter(flow_type=test_type)
        if case_tags:
            approved_cases = approved_cases.filter(tags__id__in=case_tags)

        if execute_count:
            if execute_count == 3:
                approved_cases = approved_cases.filter(execution_count__gte=execute_count)
            else:
                approved_cases = approved_cases.filter(execution_count=execute_count)

        module_count = len(modules)
        project_module_count = ProjectTestCaseModule.objects.filter(project_id=project.id).count()
        full_volume_test = len(all_approved_cases) == len(approved_cases)
        request_data.pop('modules', None)
        request_data.pop('execution_count', None)
        request_data['full_volume_test'] = full_volume_test
        request_data['project_module_count'] = project_module_count
        request_data['module_count'] = module_count
        create_serializer = ProjectTestPlanSerializer(data=request_data)
        create_serializer.is_valid(raise_exception=True)
        plan = create_serializer.save()

        clean_module_tree = self.build_clean_module_tree_from_cases(project, approved_cases)
        self.build_plan_module_tree_from_module_tree(plan, clean_module_tree)
        for case in approved_cases:
            module = case.module
            plan_module = self.build_plan_module_from_module(plan, module)
            plan_case = TestPlanCase.objects.create(
                project=project,
                module=plan_module,
                plan=plan,
                case=case,
                case_type=case.case_type,
                flow_type=case.flow_type,
                description=case.description,
                precondition=case.precondition,
                expected_result=case.expected_result,
                creator=top_user
            )
            if case.tags.exists():
                plan_case.tags.add(*case.tags.all())

        return api_created_success(create_serializer.data)

    def build_clean_module_tree_from_cases(self, project, cases):
        module_ids = cases.values_list('module_id', flat=True)
        module_ids = set(module_ids)
        top_modules = project.test_case_modules.filter(parent_id=None).order_by('index')
        return self.build_module_tree_from_modules(top_modules, module_ids)

    def build_module_tree_from_modules(self, modules, module_ids, module_tree=None):
        module_tree = {} if module_tree is None else module_tree

        for index, module in enumerate(modules):
            key = module.id
            if module.id in module_ids:
                if key not in module_tree:
                    module_tree[key] = {'module': deepcopy(module), 'index': index, 'children': {}}

            descendants_ids = set(module.descendants.values_list('id', flat=True))
            if len(module_ids & descendants_ids):
                if key not in module_tree:
                    module_tree[key] = {'module': deepcopy(module), 'index': index, 'children': {}}

                children_tree = module_tree[key]['children']
                children_modules = deepcopy(module.children.order_by('index'))
                self.build_module_tree_from_modules(children_modules, module_ids, module_tree=children_tree)

        return module_tree

    def build_plan_module_tree_from_module_tree(self, plan, module_tree):
        module_data_list = sorted(module_tree.values(), key=lambda x: x['index'])
        for module_data in module_data_list:
            module = module_data['module']
            self.build_plan_module_from_module(plan, module)
            children_tree = module_data['children']
            if children_tree:
                self.build_plan_module_tree_from_module_tree(plan, children_tree)

    def build_plan_module_from_module(self, plan, module):
        top_user = self.request.top_user
        plan_module = plan.plan_modules.filter(module_id=module.id).first()
        if not plan_module:
            plan_module_parent = None
            if module.parent:
                plan_module_parent = self.build_plan_module_from_module(plan, module.parent)
            plan_module = TestPlanModule.objects.create(
                plan=plan,
                module=module,
                creator=top_user,
                parent=plan_module_parent,
                name=module.name
            )
        return plan_module

    @action(methods=['patch'], detail=True)
    def done(self, request, *args, **kwargs):
        instance = self.get_object()
        remarks = request.data.get('remarks', None)
        if instance.status not in ['ongoing', 'no_start']:
            return api_bad_request('已经完成，无需操作')

        instance.done_at = timezone.now()
        instance.status = 'done'
        if remarks:
            instance.remarks = remarks
        instance.save()
        instance.plan_cases.filter(status='pending').update(status='closed')
        data = self.get_serializer_class()(instance).data
        return api_success(data)


@api_view(['GET'])
@request_params_required('plan')
def test_plan_modules(request):
    plan_id = request.GET.get('plan')
    test_plan = get_object_or_404(ProjectTestPlan, pk=plan_id)
    modules = test_plan.plan_modules.filter(parent_id=None).order_by('index')
    data = TestPlanModuleWithChildrenSerializer(modules, many=True).data
    return api_success(data)


@method_decorator(request_data_fields_required(['status']), name='status')
@method_decorator(project_test_plan_cases_params_verify, name='list')
@method_decorator(project_test_plan_cases_params_verify, name='list_groups')
@method_decorator(project_test_plan_cases_params_verify, name='filter_data')
@method_decorator(project_test_plan_cases_params_verify, name='statistics_data')
class TestPlanCaseViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    """
    测试计划用例
    """
    queryset = TestPlanCase.objects.order_by('created_at')
    serializer_class = TestPlanCaseSerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter,)
    search_fields = ('description',)

    filter_fields = ('status', 'tags')
    filter_class = TestPlanCaseFilter

    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        """
           A viewset that provides default `create()`, `retrieve()`, `update()`,
           `partial_update()`, `destroy()` and `list()` actions.
           """
        return super(TestPlanCaseViewSet, self).get_serializer_class()

    def get_queryset(self):
        queryset = TestPlanCase.objects.all()
        plan = self.request.query_params.get('plan')
        module = self.request.query_params.get('module')
        if module:
            queryset = queryset.filter(module_id=module).order_by('created_at')
        elif plan:
            queryset = queryset.filter(plan_id=plan).order_by('created_at')

        page = self.request.query_params.get('page')
        page_size = self.request.query_params.get('page_size')
        if not all([page, page_size]):
            self.pagination_class = None

        return queryset

    def get_new_queryset(self):
        queryset = TestPlanCase.objects.all()
        plan = self.request.query_params.get('plan')
        module = self.request.query_params.get('module')

        if module:
            module_ob = get_object_or_404(TestPlanModule, pk=module)
            queryset = module_ob.contained_test_cases.order_by('created_at')
        elif plan:
            queryset = queryset.filter(plan_id=plan).order_by('created_at')

        return queryset

    @action(methods=['get'], detail=False)
    def list_groups(self, request, *args, **kwargs):
        queryset = self.get_new_queryset()
        queryset = self.filter_queryset(queryset)
        queryset = queryset.order_by('module__full_index')
        # queryset = sorted(queryset, key=lambda x: (x.module.full_index, x.module.id), reverse=False)

        page = self.request.query_params.get('page')
        page_size = self.request.query_params.get('page_size')
        if not all([page, page_size]):
            self.pagination_class = None
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            case_list = serializer.data
            res_data = self.make_groups(case_list)
            return self.get_paginated_response(res_data)

        serializer = self.get_serializer(queryset, many=True)
        case_list = serializer.data
        res_data = self.make_groups(case_list)
        return Response(res_data)

    @staticmethod
    def make_groups(case_list):
        case_data = {}
        for query in case_list:
            module_id = query['module']['id']
            if module_id not in case_data:
                case_data[module_id] = deepcopy(query['module'])
                case_data[module_id]['cases'] = []
            case_data[module_id]['cases'].append(query)
        for key in case_data:
            case_data[key]['cases'] = sorted(case_data[key]['cases'], key=lambda x: x['index'], reverse=False)
        case_data = sorted(case_data.values(), key=lambda x: x['full_index'], reverse=False)
        return case_data

    @action(methods=['get'], detail=False)
    def statistics_data(self, request, *args, **kwargs):
        queryset = self.get_new_queryset()
        queryset = self.filter_queryset(queryset)

        data = {'total': queryset.count()}
        for value, label in TestPlanCase.STATUS_CHOICES:
            data[value] = queryset.filter(status=value).count()
        return api_success(data)

    @action(methods=['get'], detail=False)
    def filter_data(self, request, *args, **kwargs):
        status_data = [{'value': value, 'label': label} for value, label in TestPlanCase.STATUS_CHOICES]
        tags = set()
        queryset = self.get_new_queryset()
        # queryset = self.filter_queryset(queryset)
        for q in queryset:
            for t in q.tags.all():
                tags.add(t)
        tags_data = ProjectTagListSerializer(tags, many=True).data
        tags_data = sorted(tags_data, key=lambda x: x['index'])
        return api_success({"status": status_data, 'tags': tags_data})

    @action(methods=['patch'], detail=True, serializer_class=TestPlanCaseStatusSerializer)
    def status(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.plan.status == 'done':
            return api_bad_request("计划结束 不支持修改")
        status_value = request.data.get('status')
        if status_value not in ['pass', 'failed']:
            return api_bad_request("只能修改为通过、失败")
        instance.status = status_value
        instance.executor = request.top_user
        instance.executed_at = timezone.now()
        plan = instance.plan
        if not plan.practical_start_time:
            plan.practical_start_time = timezone.now()
        plan.executors.add(request.top_user.id)
        plan.save()
        instance.save()
        if instance.case:
            instance.case.save()
        data = self.get_serializer_class()(instance).data

        ProjectTestCaseExecuteLog.build_log(request.top_user, instance, status_value, status_value)
        return api_success(data)

    @action(methods=['patch'], detail=True, serializer_class=TestPlanCaseStatusSerializer)
    def relevance_bug(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status != 'failed':
            return api_bad_request('测试计划用例状态为{}不能关联bug'.format(instance.status_display()))
        bug_id = request.data.get('bug_id')
        bug = get_object_or_404(Bug, pk=bug_id)
        if instance.project != bug.project:
            return api_bad_request('所选bug和测试计划用例的项目不属于同一项目')
        if bug.plan_case:
            return api_bad_request('所选bug已关联测试计划用例，无法再次关联')
        bug.plan_case = instance
        bug.save()
        ProjectTestCaseExecuteLog.build_log(request.top_user, instance, 'relevance_bug', instance.status, bug=bug)
        data = TestPlanCaseSerializer(instance).data
        return api_success(data)

    @action(methods=['get'], detail=True)
    def review_logs(self, request, *args, **kwargs):
        instance = self.get_object()
        review_logs = instance.case.review_logs.filter(created_at__lte=instance.created_at).order_by('created_at')
        data = ProjectTestCaseReviewLogSerializer(review_logs, many=True).data
        return api_success(data=data)

    @action(methods=['get'], detail=True)
    def executed_logs(self, request, *args, **kwargs):
        instance = self.get_object()
        executed_logs = instance.executed_logs.order_by('executed_at')
        data = ProjectTestCaseExecuteLogSerializer(executed_logs, many=True).data
        return api_success(data=data)

    def destroy(self, request, *args, **kwargs):
        return api_bad_request('暂时删除功能不开放')


@method_decorator(request_params_required(['project']), name='list')
@method_decorator(request_params_required(['project']), name='filter_data')
@method_decorator(request_params_required(['project']), name='statistics_data')
@method_decorator(request_data_fields_required(['action']), name='status')
@method_decorator(request_data_fields_required(['assignee']), name='assignee')
@method_decorator(request_data_fields_required(['content']), name='comment')
@method_decorator(request_data_fields_required(['assignee', 'bugs']), name='batch_assign')
@method_decorator(request_data_fields_required(['action', 'bugs']), name='batch_status')
class BugViewSet(viewsets.ModelViewSet):
    """
    项目Bug
    """
    queryset = Bug.objects.order_by('-created_at')
    serializer_class = BugSerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter,)
    search_fields = ('index', 'title',)

    filter_fields = ('modules', 'bug_types', 'platforms', 'priorities', 'assignees', 'status', 'tags')
    filter_class = BugFilter
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        """
           A viewset that provides default `create()`, `retrieve()`, `update()`,
           `partial_update()`, `destroy()` and `list()` actions.
           """
        page = self.request.query_params.get('page')
        page_size = self.request.query_params.get('page_size')
        if not all([page, page_size]):
            self.pagination_class = None

        if self.action in ['update', 'partial_update']:
            self.serializer_class = BugUpdateSerializer
        return super(BugViewSet, self).get_serializer_class()

    # 获取详情
    def retrieve(self, request, *args, **kwargs):
        pk = kwargs['pk']
        instance = get_object_or_404(Bug, pk=pk)
        serializer = self.get_serializer(instance)
        data = serializer.data

        bug_siblings = self.get_bug_siblings(instance)
        bug_siblings_id = list(bug_siblings.values_list('id', flat=True))

        ordering = request.query_params.get('ordering', None) or '-created_at'
        bug_sibling_list = list(bug_siblings.order_by(ordering))

        previous_bug = None
        next_bug = None
        if bug_siblings_id:
            if instance.id in bug_siblings_id:
                current_bug_index = bug_siblings_id.index(instance.id)
                previous_bug_index = current_bug_index - 1
                next_bug_index = current_bug_index + 1
                if previous_bug_index >= 0:
                    previous_bug = bug_sibling_list[previous_bug_index]
                if next_bug_index < len(bug_sibling_list):
                    next_bug = bug_sibling_list[next_bug_index]

        data['previous_bug'] = self.get_bug_simple_data(previous_bug) if previous_bug else None
        data['next_bug'] = self.get_bug_simple_data(next_bug) if next_bug else None

        return Response(data)

    def get_bug_simple_data(self, bug):
        project = bug.project
        return {'id': bug.id, 'title': bug.title, 'project': {'id': project.id, 'name': project.name}}

    def get_bug_siblings(self, bug):
        queryset = bug.project.bugs.order_by('-created_at')
        queryset = self.filter_queryset(queryset)
        return queryset

    def get_queryset(self, ):
        params = self.request.query_params
        queryset = Bug.objects.order_by('-created_at')
        project = params.get('project')
        if project:
            queryset = queryset.filter(project_id=project).order_by('-created_at')
        search = self.request.query_params.get('search', '')
        if search and search.strip():
            search = search.strip()
            if search.startswith('#') and search.replace('#', '', 1).isdigit():
                bug_index = search.replace('#', '', 1)
                queryset = queryset.filter(Q(index=int(bug_index)) | Q(title__icontains=search))
                self.search_fields = []
        created_start_date = None
        created_end_date = None
        try:
            if params.get('created_start_date'):
                created_start_date = datetime.strptime(params.get('created_start_date'), '%Y-%m-%d')
            if params.get('created_end_date'):
                created_end_date = datetime.strptime(params.get('created_end_date'), '%Y-%m-%d')
        except Exception as e:
            raise e
        if created_start_date:
            start_time = datetime(created_start_date.year, created_start_date.month, created_start_date.day, 0, 0, 0)
            queryset = queryset.filter(created_at__gte=start_time)
        if created_end_date:
            end_time = datetime(created_end_date.year, created_end_date.month, created_end_date.day, 23, 59, 59)
            queryset = queryset.filter(created_at__lte=end_time)
        return queryset

    @action(methods=['get'], detail=False)
    def simple_list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        data = BugSimpleSerializer(queryset, many=True).data
        return api_success(data)

    @action(methods=['get'], detail=False)
    def export_excel(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        project_id = self.request.query_params.get('project', '')
        project_name = ''
        if project_id:
            project = get_object_or_404(Project, pk=project_id)
            project_name = project.name
        data = BugExportSerializer(queryset, many=True).data
        export_fields = [
            {'field_name': 'project_name', 'verbose_name': '项目名称', 'col_width': 10},
            {'field_name': 'title', 'verbose_name': 'bug名称', 'col_width': 20},
            {'field_name': 'module_full_name', 'verbose_name': '模块名称', 'col_width': 10},
            {'field_name': 'bug_type_display', 'verbose_name': 'bug类型', 'col_width': 10},
            {'field_name': 'platform_name', 'verbose_name': '平台', 'col_width': 10},
            {'field_name': 'priority_display', 'verbose_name': '优先级', 'col_width': 10},
            {'field_name': 'creator_username', 'verbose_name': '提交人', 'col_width': 10},
            {'field_name': 'assignee_username', 'verbose_name': '分配人', 'col_width': 10},
            {'field_name': 'fixed_by_username', 'verbose_name': '修复人', 'col_width': 10},
            {'field_name': 'status_display', 'verbose_name': '状态', 'col_width': 10},
            {'field_name': 'created_at', 'verbose_name': '提交日期', 'col_width': 15},
        ]

        response = build_excel_response(data, export_fields, 'Project{}BugTable'.format(project_id),
                                        verbose_filename='项目【{}】Bug列表'.format(project_name))
        return response

    @action(methods=['get'], detail=False)
    def filter_data(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        status_value = self.request.query_params.get('status')
        if status_value:
            if status_value not in ['pending', 'fixed', 'confirmed', 'closed']:
                return api_bad_request("status可选值为['pending', 'fixed', 'confirmed', 'closed']")
            queryset = queryset.filter(status=status_value)

        data = {
            'modules': [], 'platforms': [], 'tags': [],
            'assignees': [], 'creators': [], 'fixed_by': [],
            'priorities': [], 'bug_types': [], 'status': []
        }

        module_ids = set()
        modules_data = []
        platform_ids = set()
        platforms_data = []
        tag_ids = set()
        tags_data = []

        assignee_ids = set()
        assignees_data = []
        creator_ids = set()
        creators_data = []

        fixed_by_ids = set()
        fixed_by_data = []

        bug_types = set()
        bug_priorities = set()
        bug_status = set()

        for q in queryset:
            bug_types.add(q.bug_type)
            bug_priorities.add(q.priority)
            bug_status.add(q.status)

            if q.module_id and q.module_id not in module_ids:
                obj = q.module
                obj_data = {'id': obj.id, 'name': obj.name, 'full_name': obj.full_name, 'full_index': obj.full_index}
                modules_data.append(obj_data)
                module_ids.add(obj.id)

            if q.platform_id and q.platform_id not in platform_ids:
                obj = q.platform
                obj_data = {'id': obj.id, 'name': obj.name, 'created_at': obj.created_at}
                platforms_data.append(obj_data)
                platform_ids.add(obj.id)

            for tag in q.tags.all():
                if tag.id not in tag_ids:
                    tags_data.append({'id': tag.id, 'name': tag.name, 'index': tag.index})
                    tag_ids.add(tag.id)

            if q.assignee_id and q.assignee_id not in assignee_ids:
                obj = q.assignee
                obj_data = {'id': obj.id, 'username': obj.username, 'avatar': obj.avatar,
                            'avatar_color': obj.avatar_color}
                assignees_data.append(obj_data)
                assignee_ids.add(obj.id)

            if q.creator_id and q.creator_id not in creator_ids:
                obj = q.creator
                obj_data = {'id': obj.id, 'username': obj.username, 'avatar': obj.avatar,
                            'avatar_color': obj.avatar_color}
                creators_data.append(obj_data)
                creator_ids.add(obj.id)

            if q.fixed_by_id and q.fixed_by_id not in fixed_by_ids:
                obj = q.fixed_by
                obj_data = {'id': obj.id, 'username': obj.username, 'avatar': obj.avatar,
                            'avatar_color': obj.avatar_color}
                fixed_by_data.append(obj_data)
                fixed_by_ids.add(obj.id)

        data['modules'] = sorted(modules_data, key=lambda x: x['full_index'])
        data['platforms'] = sorted(platforms_data, key=lambda x: x['created_at'])
        data['tags'] = sorted(tags_data, key=lambda x: x['index'])

        data['assignees'] = sorted(assignees_data, key=lambda x: x['username'])
        data['creators'] = sorted(creators_data, key=lambda x: x['username'])
        data['fixed_by'] = sorted(fixed_by_data, key=lambda x: x['username'])

        # bug状态
        data['status'] = [{'value': value, 'label': label} for value, label in Bug.STATUS_CHOICES if
                          value in bug_status]
        # bug优先级
        data['priorities'] = [{'value': value, 'label': label} for value, label in Bug.PRIORITY_CHOICES if
                              value in bug_priorities]
        # bug类型
        data['bug_types'] = [{'value': value, 'label': label} for value, label in Bug.BUG_TYPE_CHOICES if
                             value in bug_types]
        return api_success(data)

    @action(methods=['get'], detail=False)
    def statistics_data(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        my_created_count = len(queryset.filter(creator_id=request.top_user.id))
        my_assigned_count = len(
            queryset.filter(assignee_id=request.top_user.id).filter(status__in=['pending', 'fixed']))
        data = {'all': len(queryset), 'my_created': my_created_count, 'my_assigned': my_assigned_count}
        for value, label in Bug.STATUS_CHOICES:
            data[value] = queryset.filter(status=value).count()
        return api_success(data)

    def build_project_tags(self, request_data, project_id):
        tags = request_data.get('tags', None)
        if tags is not None:
            tag_ids = set()
            if tags:
                for name in tags:
                    name = name.strip()
                    if name:
                        tag, created = ProjectTag.objects.get_or_create(project_id=project_id, name=name)
                        tag_ids.add(tag.id)
            request_data['tags'] = list(tag_ids)
        return request_data

    def create(self, request, *args, **kwargs):
        """创建"""
        top_user = self.request.top_user
        request_data = deepcopy(request.data)
        request_data['creator'] = top_user.id
        project_id = request_data.get('project')
        plan_case = None
        if 'plan_case' in request_data:
            plan_case = TestPlanCase.objects.filter(pk=request_data['plan_case']).first()
            if not plan_case:
                return api_bad_request("测试计划用例不存在")
            if plan_case.plan.is_done:
                return api_bad_request("测试计划已完成 不能转bug")
            if plan_case.status != 'failed':
                return api_bad_request("用例执行失败 才能转bug")

            request_data['project'] = plan_case.project.id
            request_data['module'] = plan_case.module.module.id
            request_data['platform'] = plan_case.platform.id
            project_id = plan_case.project.id
        request_data = self.build_project_tags(request_data, project_id)
        serializer = self.get_serializer(data=request_data)
        serializer.is_valid(raise_exception=True)

        # 用例转的 不需要验证
        if not plan_case:
            validated_data = serializer.validated_data
            project = validated_data.get('project')
            module = validated_data.get('module')
            platform = validated_data.get('platform')
            if module.project_id != project.id:
                return api_bad_request("模块不属于该项目")
            if platform.project_id != project.id:
                return api_bad_request("平台不属于该项目")
        bug = serializer.save()
        if bug.plan_case:
            ProjectTestCaseExecuteLog.build_log(request.top_user, bug.plan_case, 'create_bug', bug.plan_case.status,
                                                bug=bug)
        self.send_bug_notification(request, bug)

        BugOperationLog.build_log(bug, top_user, log_type='create', new_assignee=bug.assignee)
        return api_created_success(serializer.data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        origin = deepcopy(instance)
        project = instance.project
        request_data = deepcopy(request.data)
        request_data = self.build_project_tags(request_data, project.id)
        serializer = self.get_serializer(instance, data=request_data, partial=partial)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        module = validated_data.get('module', None) or instance.module
        platform = validated_data.get('platform', None) or instance.platform

        if module.project_id != project.id:
            return api_bad_request("模块不属于该项目")
        if platform.project_id != project.id:
            return api_bad_request("平台不属于该项目")

        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        self.send_bug_notification(request, instance, origin_bug=origin)
        BugOperationLog.build_log(instance, request.top_user, log_type='edit', new_assignee=instance.assignee,
                                  origin_assignee=origin.assignee)
        return Response(serializer.data)

    @action(methods=['get'], detail=True)
    def operation_logs(self, request, *args, **kwargs):
        instance = self.get_object()
        logs = instance.operation_logs.order_by('created_at')
        data = BugOperationLogSerializer(logs, many=True).data
        return Response(data)

    @action(methods=['post'], detail=True)
    def comment(self, request, *args, **kwargs):
        instance = self.get_object()
        content = request.data.get('content', None)
        content_text = request.data.get('content_text', None)
        parent_id = request.data.get('parent', None)
        parent = None
        if parent_id:
            parent = Comment.objects.filter(pk=parent_id).first()
            if not parent:
                return api_not_found("父级不存在")
            elif getattr(parent.content_object, 'bug') != instance:
                return api_bad_request("父级评论不属于同一个对象")
            elif parent.parent:
                return api_bad_request("不支持二级以上评论")
        BugOperationLog.build_comment_log(instance, request.top_user, content, content_text=content_text,
                                          parent=parent)
        return api_success()

    @action(methods=['patch'], detail=True, serializer_class=BugAssigneeSerializer)
    def assignee(self, request, *args, **kwargs):
        instance = self.get_object()
        comment = request.data.get('comment', None)
        assignee_id = request.data.get('assignee')
        assignee_obj = get_object_or_404(TopUser, pk=assignee_id)
        if not assignee_obj.is_active:
            return api_bad_request('请选择待在职的用户')
        if assignee_obj.id == instance.assignee_id:
            return api_success()

        origin = deepcopy(instance)
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        self.send_bug_notification(request, instance, origin_bug=origin)
        BugOperationLog.build_log(instance, request.top_user, log_type='assign', new_assignee=instance.assignee,
                                  origin_assignee=origin.assignee, comment=comment)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def batch_assign(self, request, *args, **kwargs):
        assignee_id = request.data.get('assignee')
        new_assignee = get_object_or_404(TopUser, pk=assignee_id)
        comment = request.data.get('comment', None)
        if not new_assignee.is_active:
            return api_bad_request('请选择待在职的用户')
        bugs_id = request.data.get('bugs')
        if bugs_id:
            bugs = Bug.objects.filter(pk__in=bugs_id)
            need_status = Bug.ACTIONS_FROM_STATUS['assign']
            bugs_status = bugs.values_list('status', flat=True)
            if not set(bugs_status).issubset(set(need_status)):
                status_displays = [Bug.get_status_value_display(i) for i in need_status]
                return api_bad_request('请选择 {} 的bug'.format('，'.join(status_displays)))

            for bug in bugs:
                if bug.assignee_id != new_assignee.id:
                    origin = deepcopy(bug)
                    bug.assignee_id = new_assignee.id
                    bug.save()
                    self.send_bug_notification(request, bug, origin_bug=origin)
                    BugOperationLog.build_log(bug, request.top_user, log_type='assign', new_assignee=bug.assignee,
                                              origin_assignee=origin.assignee, comment=comment)

        return api_success()

    @staticmethod
    def get_bug_result_status(origin_status, action):
        actions = Bug.STATUS_ACTIONS_CHOICES[origin_status]
        if action not in actions:
            return False, "当前状态不能进行该操作"
        result_status = Bug.ACTIONS_TO_STATUS[action]
        return True, result_status

    @action(methods=['patch'], detail=True)
    def status(self, request, *args, **kwargs):
        assignee_id = self.request.data.get('assignee', None)
        new_assignee = None
        if assignee_id:
            new_assignee = get_object_or_404(TopUser, pk=assignee_id)

        instance = self.get_object()
        origin = deepcopy(instance)
        status_action = request.data.get('action')
        # 获取result_status
        result, data = self.get_bug_result_status(instance.status, status_action)
        if not result:
            return api_bad_request(message=data)
        result_status = data

        self.change_bug_status(instance, result_status, new_assignee=new_assignee)
        self.send_bug_notification(self.request, instance, origin_bug=origin)
        comment = request.data.get('comment', None)
        BugOperationLog.build_log(instance, request.top_user, log_type=status_action, new_assignee=instance.assignee,
                                  origin_assignee=origin.assignee, comment=comment)

        data = BugStatusSerializer(instance).data
        return Response(data)

    @action(methods=['patch'], detail=False)
    def batch_status(self, request, *args, **kwargs):
        assignee_id = self.request.data.get('assignee', None)
        new_assignee = None
        if assignee_id:
            new_assignee = get_object_or_404(TopUser, pk=assignee_id)

        status_action = request.data.get('action')
        bugs_id = request.data.get('bugs')
        if bugs_id:
            bugs = Bug.objects.filter(pk__in=bugs_id)
            need_status = Bug.ACTIONS_FROM_STATUS[status_action]
            bugs_status = bugs.values_list('status', flat=True)
            if not set(bugs_status).issubset(set(need_status)):
                status_displays = [Bug.get_status_value_display(i) for i in need_status]
                return api_bad_request('请选择 {} 的bug'.format('，'.join(status_displays)))
            for bug in bugs:
                result_status = Bug.ACTIONS_TO_STATUS[status_action]
                origin = deepcopy(bug)
                self.change_bug_status(bug, result_status, new_assignee=new_assignee)
                self.send_bug_notification(self.request, bug, origin_bug=origin)
                comment = request.data.get('comment', None)
                BugOperationLog.build_log(bug, request.top_user, log_type=status_action, new_assignee=bug.assignee,
                                          origin_assignee=origin.assignee, comment=comment)
        return api_success()

    def change_bug_status(self, bug, result_status, new_assignee=None):
        bug.status = result_status
        if result_status in ['confirmed', 'closed']:
            bug.closed_by = self.request.top_user
            bug.closed_at = timezone.now()
        elif result_status == 'fixed':
            bug.assignee = bug.creator
            bug.fixed_by = self.request.top_user
            bug.fixed_at = timezone.now()
            bug.closed_at = None
        elif result_status == 'pending':
            if bug.fixed_by:
                bug.assignee = bug.fixed_by
            bug.fixed_at = None
            bug.closed_at = None
            bug.reopened_at = timezone.now()
            bug.reopened_by = self.request.top_user
        if new_assignee:
            bug.assignee = new_assignee
        bug.save()

    def destroy(self, request, *args, **kwargs):
        return api_bad_request('暂时删除功能不开放')

    def send_bug_notification(self, request, bug, origin_bug=None):
        # 暂时不推送
        return
        need_send = False
        if origin_bug:
            if origin_bug.assignee_id != bug.assignee_id and request.top_user.id != bug.assignee_id:
                need_send = True
        else:
            if request.top_user.id != bug.assignee_id:
                need_send = True
        if need_send:
            url = settings.GEAR_TEST_SITE_URL + '/projects/{}/bugs/{}/'.format(bug.project_id, bug.id)
            content = "{}把项目【{}】的Bug【{}】分配给你".format(request.top_user.username, bug.project.name, bug.title)
            create_top_user_notification(bug.assignee, content, url=url, is_important=True, app_id='gear_test')


@api_view(['GET'])
def data_migrate(request):
    from testing.tasks import rebuild_all_test_statistics
    rebuild_all_test_statistics.delay()
    return api_success()


@api_view(['GET'])
def download_case_template(request, template_type):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if template_type == 'project_test_case_template':
        file_path = os.path.join(current_dir, 'cases_templates/project_test_case_template.xlsx')
        filename = 'project_test_case_template.xls'
    elif template_type == 'test_case_template':
        file_path = os.path.join(current_dir, 'cases_templates/test_case_template.xls')
        filename = 'test_case_template.xls'
    else:
        return api_bad_request()
    wrapper = FileWrapper(open(file_path, 'rb'))
    response = FileResponse(wrapper, content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = "attachment; filename*=utf-8''{}".format(escape_uri_path(filename))
    response['Access-Control-Expose-Headers'] = 'Content-Disposition'
    return response


def cases_file_check_res(request, total, check_list):
    """
        用例批量上传
        :param request:
        :param total:
        :param check_list:
        :return:
        """
    f = request.FILES.get('file')
    if not f:
        return api_bad_request("请上传文件")
    excel_type = f.name.rsplit(".", 1)[1]
    if excel_type not in ['xlsx', 'xls']:
        return api_bad_request('上传文件类型错误，导入失败')
    # 开始解析上传的excel表格
    style_blue_bkg = xlwt.easyxf('pattern: pattern solid, fore_colour red;')  # 红色

    formatting_info = excel_type == 'xls'
    try:
        wb = xlrd.open_workbook(filename=None, file_contents=f.read(), formatting_info=formatting_info)
    except:
        wb = xlrd.open_workbook(filename=None, file_contents=f.read())
    table = wb.sheets()[0]
    # 总行数 列数
    rows_count = table.nrows
    # cols_count = table.ncols
    # print(rows_count, cols_count)

    rb = xlutils_copy(wb)
    ws = rb.get_sheet(0)
    flag = False
    # 第1行为表头
    for i in range(1, rows_count):
        # 取前5列
        row_values = table.row_values(i, start_colx=0, end_colx=total)
        if any(row_values):
            for required_index in check_list:
                row_value = row_values[required_index]
                if required_index == 0 and isinstance(row_value, float):
                    flag = True
                    ws.write(i, required_index, '模块名不支持纯数值', style_blue_bkg)
                elif not row_value:
                    flag = True
                    ws.write(i, required_index, '请填写', style_blue_bkg)

    file_name = gen_uuid() + '.xls'
    file_path = settings.MEDIA_ROOT + 'testing/cases/' + file_name
    dir_path = os.path.dirname(file_path)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    rb.save(file_path)
    if flag:
        data = {'message': '上传文件错误，请下载错误文件', 'file_path': file_path, 'check_pass': False}
        return api_success(data=data)

    data = {'message': '成功', 'file_path': file_path, 'check_pass': True}
    return data


@api_view(['POST'])
def cases_file_check(request):
    data = cases_file_check_res(request, total=5, check_list=[0, 2, 3])
    return api_success(data=data)


@api_view(['POST'])
def project_cases_file_check(request):
    data = cases_file_check_res(request, total=7, check_list=[0, 4, 5])
    return api_success(data=data)


@api_view(['GET'])
def download_error_template(request, template_type):
    file_path = request.query_params.get('file_path', '')
    if not os.path.exists(file_path):
        return api_bad_request('文件路径不存在')

    filename = 'test_case_template_error.xls'
    if template_type == 'project_test_case_template':
        filename = 'project_test_case_template_error.xls'
    wrapper = FileWrapper(open(file_path, 'rb'))
    response = FileResponse(wrapper, content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = "attachment; filename*=utf-8''{}".format(escape_uri_path(filename))
    response['Access-Control-Expose-Headers'] = 'Content-Disposition'
    return response


@api_view(['POST'])
@request_data_fields_required(['file_path', 'library_id'])
@transaction.atomic
def import_cases(request):
    """
    创建用例
    :param request:
    :return:
    """
    file_path = request.data.get('file_path', '')
    if not os.path.exists(file_path):
        return api_bad_request('文件路径不存在')
    library_id = request.data.get('library_id', '')
    library = get_object_or_404(TestCaseLibrary, pk=library_id)
    top_user = request.top_user

    wb = xlrd.open_workbook(filename=file_path)
    table = wb.sheets()[0]
    row_values = table.row_values(1, start_colx=0, end_colx=4)

    # 把 1111/333/444  读成float了 怎么处理

    rows = table.nrows  # 总行数
    sid = transaction.savepoint()
    try:
        for i in range(1, rows):
            row_values = table.row_values(i, start_colx=0, end_colx=4)
            if not any(row_values):
                continue
            if len(row_values) < 4:
                transaction.savepoint_rollback(sid)
                return api_bad_request("excel的前四列应该是：用例模块（必填）、用例描述（必填）、前置条件、预期结果（必填）")

            module_name, description, precondition, expected_result = row_values
            if not all([module_name, description, expected_result]):
                transaction.savepoint_rollback(sid)
                return api_bad_request("模块名、用例描述、预期结果必填")

            if isinstance(module_name, float):
                transaction.savepoint_rollback(sid)
                return api_bad_request("模块名不要输入纯数字")
            # 依次创建层级模块
            module_list = []
            module_name_list = module_name.split('/')
            if not module_name_list:
                continue
            for index, name in enumerate(module_name_list):
                if index == 0:
                    # 一级模块
                    first_module = TestCaseModule.objects.filter(library_id=library_id, parent_id=None,
                                                                 name=name).first()
                    if not first_module:
                        first_module = TestCaseModule.objects.create(library_id=library_id, parent_id=None,
                                                                     name=name,
                                                                     creator=top_user)
                    module_list.append(first_module)
                else:
                    # 子模块的父集模块是module_list中的上一个
                    parent_module = module_list[index - 1]
                    child_module = TestCaseModule.objects.filter(library_id=library_id,
                                                                 parent_id=parent_module.id, name=name).first()
                    if not child_module:
                        child_module = TestCaseModule.objects.create(library_id=library_id,
                                                                     parent_id=parent_module.id, name=name,
                                                                     creator=top_user
                                                                     )
                    module_list.append(child_module)
            # 创建模块后 用例属于最后一个模块
            if module_list:
                test_case_module = module_list[-1]
                # 去重规则：模块 前置条件 用例描述 预期结果
                case = TestCase.objects.filter(module=test_case_module, precondition=precondition,
                                               description=description,
                                               expected_result=expected_result).first()
                if not case:
                    case = TestCase.objects.create(module=test_case_module, precondition=precondition,
                                                   description=description,
                                                   expected_result=expected_result,
                                                   creator_id=top_user.id)
    except Exception as e:
        logger.error(e)
        transaction.savepoint_rollback(sid)
        return simple_responses.api_error('解析excel文件或者数据插入错误:{}'.format(e))
    transaction.savepoint_commit(sid)
    return api_success()


@api_view(['POST'])
@request_data_fields_required(['file_path', 'project_id', 'platform_id'])
@transaction.atomic
def import_project_cases(request):
    """
    创建用例
    :param request:
    :return:
    """
    file_path = request.data.get('file_path', '')
    if not os.path.exists(file_path):
        return api_bad_request('文件路径不存在')
    project_id = request.data.get('project_id', '')
    platform_id = request.data.get('platform_id', '')
    project = get_object_or_404(Project, pk=project_id)
    platform = get_object_or_404(ProjectPlatform, pk=platform_id)
    if platform.project != project:
        return api_bad_request("所选平台不属于该项目")

    top_user = request.top_user
    wb = xlrd.open_workbook(filename=file_path)
    table = wb.sheets()[0]
    rows = table.nrows  # 总行数
    sid = transaction.savepoint()

    try:
        for i in range(1, rows):
            row_values = table.row_values(i, start_colx=0, end_colx=7)
            if not any(row_values):
                continue
            if len(row_values) < 6:
                transaction.savepoint_rollback(sid)
                return api_bad_request("excel的前七列应该是：用例模块（必填）、用例类型（必填）、是否冒烟（必填）、用例描述（必填）、前置条件、预期结果（必填）、标签")
            if len(row_values) == 6:
                module_name, case_type, flow_type, description, precondition, expected_result = row_values
                tags_str = ''
            else:
                module_name, case_type, flow_type, description, precondition, expected_result, tags_str = row_values

            if not all([module_name, case_type, flow_type, description, expected_result]):
                transaction.savepoint_rollback(sid)
                return api_bad_request("模块名、用例类型、是否冒烟、用例描述、预期结果必填")

            # 用例标签处理
            tag_list = re.sub(r'[;；,，]', '卍', tags_str.strip()).split('卍') if tags_str.strip() else []
            new_tags_name = set([tag_name.strip() for tag_name in tag_list if tag_name.strip()])

            # 依次创建层级模块
            if isinstance(module_name, float):
                transaction.savepoint_rollback(sid)
                return api_bad_request("模块名不支持纯数值")

            module_list = []
            module_name_list = module_name.split('/')
            if not module_name_list:
                continue
            for index, name in enumerate(module_name_list):
                if index == 0:
                    # 一级模块
                    first_module = ProjectTestCaseModule.objects.filter(
                        project_id=project_id,
                        parent_id=None,
                        name=name
                    ).first()
                    if not first_module:
                        first_module = ProjectTestCaseModule.objects.create(
                            project_id=project_id,
                            parent_id=None,
                            name=name,
                            creator=top_user
                        )
                    # 多对多字段的处理add、remove、clear
                    # 添加平台
                    first_module.platforms.add(platform)
                    module_list.append(first_module)
                else:
                    # 子模块的父集模块是module_list中的上一个
                    parent_module = module_list[index - 1]
                    child_module = ProjectTestCaseModule.objects.filter(
                        project_id=project_id,
                        parent_id=parent_module.id,
                        name=name
                    ).first()
                    if not child_module:
                        child_module = ProjectTestCaseModule.objects.create(
                            project_id=project_id,
                            parent_id=parent_module.id,
                            name=name,
                            creator=top_user
                        )
                    child_module.platforms.add(platform)
                    module_list.append(child_module)
            # 创建模块后 用例属于最后一个模块
            if module_list:
                test_case_module = module_list[-1]
                # 创建用例标签
                new_tags = set()
                for tag_name in new_tags_name:
                    tag_name = tag_name.strip()
                    if tag_name:
                        tag = ProjectTag.objects.filter(project_id=project_id, name=tag_name).first()
                        if not tag:
                            tag = ProjectTag.objects.create(project_id=project_id, name=tag_name,
                                                            creator=top_user)
                        new_tags.add(tag)

                # 去重规则：模块 前置条件 用例描述 预期结果  + 标签
                case = ProjectTestCase.objects.filter(
                    project_id=project_id,
                    module=test_case_module,
                    precondition=precondition,
                    description=description,
                    expected_result=expected_result
                ).first()
                if not case:
                    case = ProjectTestCase.objects.create(
                        project_id=project_id,
                        module=test_case_module,
                        case_type=case_type,
                        flow_type=flow_type,
                        precondition=precondition,
                        description=description,
                        expected_result=expected_result,
                        creator_id=top_user.id
                    )
                else:
                    origin_tags_name = set()
                    origin_tags = case.tags.values_list('name', flat=True)
                    if origin_tags:
                        origin_tags_name = set(origin_tags)
                    if origin_tags_name != new_tags_name:
                        case = ProjectTestCase.objects.create(
                            project_id=project_id,
                            module=test_case_module,
                            case_type=case_type,
                            flow_type=flow_type,
                            precondition=precondition,
                            description=description,
                            expected_result=expected_result,
                            creator_id=top_user.id
                        )
                # 判断标签是否一致
                case.platforms.add(platform)
                if new_tags:
                    case.tags.add(*new_tags)
    except Exception as e:
        logger.error(e)
        transaction.savepoint_rollback(sid)
        return simple_responses.api_error('解析excel文件或者数据插入错误:{}'.format(e))
    transaction.savepoint_commit(sid)
    return api_success()


# 拖拽排序树结构中模块  项目用例库模块、用例库模块
def drag_sort_tree_obj(request, queryset, need_same_parent=False):
    origin_id = request.data.get('origin_id', None)
    target_parent_id = request.data.get('target_parent_id', None)
    target_previous_id = request.data.get('target_previous_id', None)
    target_next_id = request.data.get('target_next_id', None)

    if not all([origin_id, target_previous_id or target_next_id or target_parent_id]):
        return api_bad_request('拖拽对象、目标位置必填')

    if origin_id in [target_previous_id, target_next_id, target_parent_id]:
        return api_bad_request('拖拽对象 不应该与目标位置一致')

    tree_top_levels = set()
    parent_levels = set()

    origin_obj = queryset.filter(pk=origin_id).first()
    target_parent_obj = None
    target_previous_obj = None
    target_next_obj = None
    if target_parent_id:
        target_parent_obj = queryset.filter(pk=target_parent_id).first()
        if target_parent_obj:
            tree_top_levels.add(getattr(target_parent_obj, 'tree_top_level', None))
            parent_levels.add(getattr(target_parent_obj, 'parent_level', None))

    if target_previous_id:
        target_previous_obj = queryset.filter(pk=target_previous_id).first()
        if target_previous_obj:
            tree_top_levels.add(getattr(target_previous_obj, 'tree_top_level', None))
            parent_levels.add(getattr(target_previous_obj, 'parent_level', None))

    if target_next_id:
        target_next_obj = queryset.filter(pk=target_next_id).first()
        if target_next_obj:
            if target_previous_obj and target_previous_obj.parent_level != target_next_obj.parent_level:
                return api_bad_request("目标位置上下对象不属于一个父级")
            tree_top_levels.add(getattr(target_next_obj, 'tree_top_level', None))
            parent_levels.add(getattr(target_next_obj, 'parent_level', None))

    if not origin_obj:
        return api_not_found('拖拽对象不存在')

    if len(tree_top_levels) > 1:
        return api_not_found('拖拽对象 及位置不属于同一个树结构')

    if not all([origin_obj, target_parent_obj or target_previous_obj or target_next_obj]):
        return api_bad_request('拖拽对象、目标位置必填')

    if need_same_parent:
        if len(parent_levels) > 1:
            return api_not_found('拖拽对象 及位置不属于同一个父级')

    if target_parent_obj and getattr(target_parent_obj, 'tree_drag_sort_parent_verify_data'):
        if not set(origin_obj.tree_drag_sort_parent_verify_data).issubset(
                set(target_parent_obj.tree_drag_sort_parent_verify_data)):
            return api_bad_request(origin_obj.tree_drag_sort_error_message)

    origin_next_siblings = origin_obj.next_siblings
    # 移出 将被拖拽的元素的下方元素上移一位 index-1       移出
    for obj in origin_next_siblings:
        obj.index = obj.index - 1
        obj.save()
    # 插入
    # 如果目标位置没有上方元素    目标位置index为1    目标位置下方元素index+1

    target_index = 1
    # 目标位置有上方元素
    if target_previous_obj:
        target_previous_obj = queryset.filter(pk=target_previous_id).first()
        target_index = target_previous_obj.index + 1
    # 目标位置有下方元素
    if target_next_obj:
        target_next_obj = queryset.filter(pk=target_next_id).first()
        for obj in target_next_obj.next_siblings.exclude(pk=origin_obj.id):
            obj.index = obj.index + 1
            obj.save()
        target_next_obj.index = target_next_obj.index + 1
        target_next_obj.save()
    origin_obj.index = target_index
    origin_obj.parent = target_parent_obj
    origin_obj.save()

    return api_success()


# 拖拽同级对象 进行排序   用例库用例、项目用例库用例 同模块之间拖拽排序
def drag_same_level_obj(request, queryset):
    request.data.pop('target_parent_id', None)
    return drag_sort_tree_obj(request, queryset, need_same_parent=True)


@api_view(['GET'])
def get_project_bugs_trend_chart_data(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    params = request.GET
    today = timezone.now().date()
    start_date = today - timedelta(days=6)
    end_date = today
    try:
        if params.get('start_date'):
            start_date = datetime.strptime(params.get('start_date'), '%Y-%m-%d').date()
        if params.get('end_date'):
            end_date = datetime.strptime(params.get('end_date'), '%Y-%m-%d').date()
    except Exception as e:
        return api_bad_request(message=str(e))

    build_project_today_pending_bugs_statistics(project)
    day_pending_bugs = TestDayBugStatistic.objects.filter(date__gte=start_date, date__lte=end_date,
                                                          project_id=project_id)
    day_pending_bugs_data = TestDayBugStatisticSerializer(day_pending_bugs, many=True).data
    data_groups = {}
    date_list = get_date_str_list(start_date, end_date)

    project_template = {"total": 0}
    for k, v in Bug.PRIORITY_CHOICES:
        project_template[k] = 0
    for i in date_list:
        data_groups[i] = {'bugs_detail': deepcopy(project_template),
                          'project': {'id': project.id, 'name': project.name}, 'date': i}

    for bug_data in day_pending_bugs_data:
        date = bug_data['date']
        data_groups[date]['bugs_detail'] = bug_data['bugs_detail']
    data = sorted(data_groups.values(), key=lambda x: x['date'], reverse=False)
    return api_success(data=data)
