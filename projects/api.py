import logging
import math
import os
import shutil
import urllib.parse
from decimal import Decimal
from pprint import pprint
from itertools import chain
from copy import deepcopy
import re
import urllib.parse
from datetime import timedelta, datetime
import ast
import json
from collections import Counter
from wsgiref.util import FileWrapper

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Sum, IntegerField, When, Case, Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404, reverse
from django.utils import timezone
from django.utils.encoding import escape_uri_path
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.utils.cache import get_cache_key
from django.contrib.contenttypes.models import ContentType
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import HTTP_HEADER_ENCODING, exceptions
from pypinyin import lazy_pinyin
from xlwt import Workbook

from auth_top.models import TopToken
from auth_top.authentication import TokenAuthentication
from exports.utils import build_excel_response
from gearfarm.utils.farm_response import api_bad_request, api_success, api_permissions_required, api_error, \
    api_request_params_required, api_not_found, build_pagination_response, build_pagination_queryset_data
from farmbase.utils import gen_uuid, in_group, last_week_start, next_week_end, encrypt_string, this_week_end, \
    in_any_groups, get_protocol_host

from farmbase.user_utils import get_user_data
from gearfarm.utils.page_path_utils import build_page_path
from gearfarm.utils.decorators import request_params_required
from farmbase.permissions_utils import func_perm_required
from farmbase.templatetags.mytags import user_project_undone_work_count
from farmbase.serializers import UserSimpleSerializer, UserBasicSerializer, UserFilterSerializer
from farmbase.tasks import crawl_project_engineer_contact_folder_docs, update_quip_project_folder, \
    create_quip_project_folder, update_quip_project_engineer_folder, crawl_project_tpm_folder_docs, \
    crawl_quip_folder_children_folders_to_cache
from geargitlab.tasks import crawl_farm_projects_recent_half_hour_git_demo_commits, \
    crawl_farm_project_recent_half_hour_git_demo_commits
from logs.models import Log
from notifications.tasks import send_project_schedule_update_reminder, send_project_status_update_reminder
from notifications.utils import create_notification, create_notification_group, create_developer_notification, \
    create_notification_to_users
from developers.tasks import rebuild_ongoing_projects_dev_docs_checkpoints_status
from playbook.utils import initialize_project_playbook, update_project_playbook_for_schedule
from projects.models import (ProjectLinks, DeliveryDocument, ProjectPrototype,
                             DeliveryDocumentType, JobPosition,
                             Project, ProjectContract, PrototypeCommentPoint,
                             JobPositionNeed, JobPositionCandidate, ClientCalendar, TechnologyCheckpoint,
                             JobReferenceScore, JobStandardScore, ProjectTest, ProjectStage, Questionnaire, Question,
                             Choice, GradeQuestionnaire, AnswerSheet,
                             JobReferenceScore, JobStandardScore, ProjectTest, ProjectStage, ProjectWorkHourPlan,
                             ProjectWorkHourOperationLog, WorkHourRecord)
from projects.serializers import (ProjectCreateSerializer,
                                  ProjectSimpleSerializer,
                                  ProjectEditSerializer,
                                  DeliveryDocumentSerializer,
                                  DeliveryDocumentTypeSerializer, ProjectPrototypeDetailSerializer,
                                  JobCreateSerializer,
                                  JobSerializer, JobSimpleSerializer,
                                  JobWithPaymentsSerializer, ProjectPrototypeSerializer,
                                  ProjectDeploymentSerializer,
                                  ProjectsPageSerializer, ProjectDetailSerializer,
                                  ProjectWithContractSerializer,
                                  ProjectContractSerializer,
                                  ProjectPrototypeWithBrowsingHistorySerializer, PrototypeCommentPointSerializer,
                                  ProjectGanttChartRetrieveSerializer, GanttTaskTopicTimeSerializer,
                                  GanttRoleSerializer, GanttTaskCatalogueSerializer, GanttTaskTopicSerializer,
                                  PrototypeCommentPointWithCommentsSerializer, JobPositionNeedSerializer,
                                  JobPositionCandidateSerializer, GanttTaskTopicStartTimeSerializer,
                                  GanttTaskTopicWorkDateSerializer, ClientCalendarSerializer,
                                  ClientCalendarReadOnlySerializer, ClientCalendarSimpleSerializer,
                                  GanttTaskTopicCreateSerializer,
                                  ProjectGitlabCommittersSerializer, ProjectWithScheduleSerializer,
                                  ProjectMembersSerializer, PositionNeedEditSerializer,
                                  ProjectWithDeveloperListSerializer, TechnologyCheckpointSerializer,
                                  TechnologyCheckpointEditSerializer, ProjectsManageSerializer,
                                  ProjectVerySimpleSerializer, ProjectLinksSerializer, ProjectLinksDetailSerializer,
                                  ProjectPrototypeContentTypeSerializer, JobReferenceScoreSerializer,
                                  JobStandardScoreSerializer, JobReadOnlySerializer, ProjectStageCreateSerializer,
                                  ProjectStageSimpleSerializer, PositionNeedCreateSerializer,
                                  ProjectStageEditSerializer, ProjectWithStagesSerializer, ProjectSimpleEditSerializer,
                                  QuestionnaireCreateSerializer, QuestionCreateSerializer, ChoiceCreateSerializer,
                                  QuestionnaireSerializer, QuestionEditSerializer, ChoiceEditSerializer,
                                  JobPositionWithQuestionnaire, AnswerSheetSerializer,
                                  GradeQuestionnaireCreateSerializer, AnswerSheetCreateSerializer,
                                  JobStandardScoreWithGradeSerializer,
                                  ProjectStageEditSerializer, ProjectWithStagesSerializer, ProjectSimpleEditSerializer,
                                  ProjectWorkHourPlanCreateSerializer, ProjectWorkHourPlanEditSerializer,
                                  ProjectWorkHourPlanSerializer, WorkHourRecordCreateSerializer,
                                  WorkHourRecordEditSerializer, ProjectWorkHourOperationLogSerializer,
                                  ProjectWithWorkHourPlanSerializer)
from projects.build_projects_extra_data import projects_data_add_positions_gitlab_commits_data
from projects.utils.gantt_chart_utils import *
from projects.utils.gantt_chart_utils import init_project_gantt_roles
from logs.serializers import LogSerializer
from projects.tasks import create_project_delivery_documents, create_prototype_comment_point_cache_data, \
    create_prototype_client_comment_point_cache_data, create_prototype_developer_comment_point_cache_data, \
    unzip_prototype_and_upload_to_oss
from farmbase.user_utils import get_user_projects
from gearfarm.utils.datetime_utils import get_days_count_between_date, get_date_list
from projects.utils.common_utils import get_project_members_dict
from projects.utils.project_checkpoint_utils import PROJECT_SCHEDULE_FIELDS, TECHNOLOGY_CHECKPOINT_NAME_LIST, \
    init_project_technology_checkpoints, update_project_technology_checkpoints
from proposals.models import Proposal
from comments.models import Comment
from farmbase.permissions_utils import has_function_perm, has_any_function_perms
from tasks.models import Task
from developers.models import Role
from developers.tasks import update_developer_rate_cache_data, update_developer_cache_data, \
    update_developer_partners_cache_data
from notifications.tasks import send_project_job_position_update_reminder, send_project_data_update_reminder
from geargitlab.tasks import crawl_farm_project_recent_days_git_commits_issues
from testing.models import TestDayStatistic
from tasks.auto_task_utils import create_project_position_need_auto_task, create_project_position_candidate_auto_task
from testing.tasks import build_today_test_statistics

logger = logging.getLogger()
PROPOSAL_STATUS_DICT = Proposal.PROPOSAL_STATUS_DICT


@api_view(['GET'])
def project_simple_list(request):
    projects = Project.objects.order_by('-created_at')
    data = ProjectSimpleSerializer(projects, many=True).data
    return api_success(data)


# 进行中项目简单列表 移动端用
@api_view(['GET'])
def ongoing_project_simple_list(request):
    projects = Project.ongoing_projects().order_by('-created_at')
    search_value = request.GET.get('search_value', None)
    tpm = request.GET.get('tpm', None)
    if search_value:
        projects = projects.filter(
            Q(name__icontains=search_value) | Q(manager__username__icontains=search_value))
    if tpm == 'null':
        projects = projects.filter(tpm__isnull=True)
    data = ProjectSimpleSerializer(projects, many=True).data
    return Response({"result": True, 'data': data})


# 我的项目简单列表 移动端用
@api_view(['GET'])
def my_project_simple_list(request):
    user_id = request.user
    project_status = request.GET.get('project_status', None)
    if project_status == 'ongoing':
        projects = Project.ongoing_projects()
    elif project_status == 'closed':
        projects = Project.completion_projects()
    else:
        projects = Project.objects.all().order_by('-created_at')
    projects = get_user_projects(request.user, projects)
    # search_value = request.GET.get('search_value', None)
    # if search_value:
    #     ongoing_projects = ongoing_projects.filter(
    #     Q(name__icontains=search_value) | Q(manager__username__icontains=search_value))
    data = ProjectSimpleSerializer(projects, many=True).data
    return Response({"result": True, 'data': data})


class ProjectList(APIView):
    def get(self, request, proposal_id):
        params = request.GET
        project_status = params.get('project_status', None)
        search_value = params.get('search_value', None)
        page = params.get('page', None)
        page_size = params.get('page_size', None)
        manager_username = params.get('manager', None)
        manager_list = []
        total = 0
        data = []
        projects = []
        if project_status == 'ongoing':
            if has_any_function_perms(request.user, ['view_all_projects', 'view_ongoing_projects']):
                projects = Project.ongoing_projects().select_related('manager').order_by(
                    '-created_at')
        elif project_status == 'closed':
            completion_projects = Project.completion_projects().select_related('manager')
            if has_function_perm(request.user, 'view_all_projects'):
                projects = completion_projects
            elif has_function_perm(request.user, 'view_projects_finished_in_60_days'):
                user_projects = get_user_projects(request.user, completion_projects)
                projects_finished_in_60_days = completion_projects.filter(
                    done_at__gte=timezone.now() - timedelta(days=60))
                projects = projects_finished_in_60_days | user_projects
            else:
                projects = []
            if projects:
                projects = projects.distinct().order_by('-done_at')
        else:
            projects = Project.objects.order_by('-created_at')

        if len(projects):
            if search_value:
                projects = projects.filter(
                    Q(name__icontains=search_value) | Q(manager__username__icontains=search_value))
            manager_list = [{'id': user_id, 'username': username} for user_id, username in
                            set(projects.values_list('manager_id', 'manager__username')) if id]
            if manager_username and User.objects.filter(username=manager_username).exists():
                manager = User.objects.get(username=manager_username)
                projects = projects.filter(manager_id=manager.id)

        return build_pagination_response(request, projects, ProjectDetailSerializer)

    def post(self, request, proposal_id):
        proposal_id = proposal_id or request.GET.get('proposal', None)
        proposal = None
        if proposal_id:
            proposal = get_object_or_404(Proposal, pk=proposal_id)
            if proposal.bd:
                request.data['bd'] = proposal.bd.id
            if proposal.status >= PROPOSAL_STATUS_DICT['deal']['status']:
                return api_bad_request('该需求不处在进行中状态，不能创建项目,当前状态为{}'.format(proposal.get_status_display()))

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
            #             quip_proposals_folders = cache.get('quip_projects_folders', {})
            #             if quip_folder_id not in quip_proposals_folders:
            #                 return api_bad_request('所选择的Quip文件夹不存在')
            bound_project_link = ProjectLinks.objects.filter(quip_folder_id=quip_folder_id).first()
            if bound_project_link:
                return api_bad_request("所择Quip文件夹已绑定项目【{}】".format(bound_project_link.project.name))

        # Quip工程师沟通文件
        quip_engineer_folder_id = request_data.get('quip_engineer_folder_id', None)
        if quip_engineer_folder_id:
            # quip_projects_engineer_folders = cache.get('quip_projects_engineer_folders', {})
            # if quip_engineer_folder_id not in quip_projects_engineer_folders:
            #     return api_bad_request('所选择的Quip工程师沟通文件夹不存在')
            bound_project_link = ProjectLinks.objects.filter(quip_engineer_folder_id=quip_engineer_folder_id).first()
            if bound_project_link:
                return api_bad_request("所选择的Quip工程师沟通文件已绑定项目【{}】".format(bound_project_link.project.name))
        # quip_folder的处理结束
        if request_data['start_date'] > request_data['end_date']:
            return api_bad_request('项目开始时间不能大于结束时间')
        project_serializer = ProjectCreateSerializer(data=request_data)
        if project_serializer.is_valid():
            project = None
            project_links = None
            with transaction.atomic():
                savepoint = transaction.savepoint()
                try:
                    project = project_serializer.save()
                    request_data['project'] = project.id
                    # 日程表开始
                    stages_data = request_data['stages']
                    for index, stage in enumerate(stages_data):
                        stage['project'] = project.id
                        stage['index'] = index
                        schedule_serializer = ProjectStageCreateSerializer(data=stage)
                        if schedule_serializer.is_valid():
                            if stage['start_date'] < request_data['start_date'] or stage['end_date'] > request_data[
                                'end_date'] or stage['start_date'] > stage['end_date']:
                                transaction.savepoint_rollback(savepoint)
                                return api_bad_request('项目阶段的时间段不能超出项目的启动或者结束日期')
                            # 创建日程表
                            stage = schedule_serializer.save()
                            Log.build_create_object_log(request.user, stage)
                        else:
                            transaction.savepoint_rollback(savepoint)
                            return api_bad_request(message=schedule_serializer.errors)
                    # 日程表开始结束

                    # 项目playbook  技术检查点
                    if proposal:
                        origin = deepcopy(proposal)
                        proposal.close_and_create_project(project)
                        Log.build_update_object_log(request.user, origin, proposal)
                    initialize_project_playbook(project)
                    init_project_technology_checkpoints(project)
                    # 自动创建甘特图
                    gantt, created = ProjectGanttChart.objects.get_or_create(project_id=project.id)
                    if created:
                        init_project_gantt_roles(project)

                    # 项目链接处理开始
                    link_fields = ['gitlab_group_id', 'gitlab_project_id', 'api_document', 'ui_links',
                                   'quip_folder_type',
                                   'quip_engineer_folder_id']
                    links_data = {'project': project.id}
                    for link_field in link_fields:
                        if link_field == 'ui_links' and request_data.get('ui_links', None):
                            links_data['ui_links'] = json.dumps(request_data.get('ui_links'), ensure_ascii=False)
                        else:
                            links_data[link_field] = request_data.get(link_field, None)
                    if quip_folder_type == 'select':
                        links_data['quip_folder_id'] = quip_folder_id
                    project_links_origin = None
                    project_links, created = ProjectLinks.objects.get_or_create(project_id=project.id)
                    if not created:
                        project_links_origin = deepcopy(project_links)

                    project_links_serializer = ProjectLinksSerializer(project_links, data=links_data)
                    if not project_links_serializer.is_valid():
                        return api_bad_request(message=project_links_serializer.errors)
                    project_links = project_links_serializer.save()
                    Log.build_create_object_log(request.user, project)
                    create_project_members_change_notifications(request, project)

                    if project_links_origin:
                        Log.build_update_object_log(operator=request.user, original=project_links_origin,
                                                    updated=project_links,
                                                    related_object=project)
                    else:
                        Log.build_create_object_log(request.user, project_links, related_object=project)

                except Exception as e:
                    logger.error(e)
                    transaction.savepoint_rollback(savepoint)
                    raise
                transaction.savepoint_commit(savepoint)
            # celery异步任务
            # quip_folder的处理开始
            if project_links.quip_folder_type != 'no_need':
                if project_links.quip_folder_id:
                    update_quip_project_folder.delay(project.id)
                elif quip_folder_type == 'auto':
                    create_quip_project_folder.delay(project.id)

            if project_links.quip_engineer_folder_id:
                update_quip_project_engineer_folder.delay(project.id)
            # quip_folder的处理结束

            if project_links_origin:
                if project_links_origin.gitlab_group_id != project_links.gitlab_group_id or project_links_origin.gitlab_project_id != project_links.gitlab_project_id:
                    crawl_farm_project_recent_days_git_commits_issues.delay(project.id)
                    crawl_farm_project_recent_half_hour_git_demo_commits.delay(project.id)
            else:
                if project_links.gitlab_group_id or project_links.gitlab_project_id:
                    crawl_farm_project_recent_days_git_commits_issues.delay(project.id)
                    crawl_farm_project_recent_half_hour_git_demo_commits.delay(project.id)
            # 项目链接处理结束
            # celery异步结束
            return api_success(data=project_serializer.data)
        return api_bad_request(message=project_serializer.errors)


@api_view(['GET'])
def project_simple_detail(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    data = ProjectVerySimpleSerializer(project, many=False).data
    if 'with_last_email_record' in request.GET:
        email_record = project.email_records.filter(status='1').order_by('-created_at').first()
        if email_record:
            data['last_email_record'] = {'to': email_record.to, 'cc': email_record.cc}
    return api_success(data)


# 项目详情所需要有红点提示的选项
@api_view(['GET'])
def project_detail_reminders(request, project_id):
    from finance.models import ProjectPaymentStage
    project = get_object_or_404(Project, pk=project_id)
    tasks_count = project.tasks.filter(expected_at__lte=timezone.now().date()).filter(done_at=None).count()
    payment_count = project.project_payments.count()
    payments_due_count = 0
    stages = ProjectPaymentStage.objects.filter(project_payment__project_id=project.id)
    for obj in stages:
        if not obj.receipted_amount:
            if obj.expected_date and timezone.now().date() >= obj.expected_date:
                payments_due_count += 1

    job_positions_count = project.job_positions.count()
    data = {
        'tasks_count': tasks_count,  # 项目任务数量（今天或过期）   大于0显示红点
        'payments_count': payment_count,  # 项目收款数量  等于0显示红点
        'payments_due_count': payments_due_count,  # 逾期的项目收款数量  大于0显示红点
        'job_positions_count': job_positions_count,  # 开发职位数量  等于0显示红点
    }
    return api_success(data)


class ProjectDetail(APIView):
    def get(self, request, project_id, format=None):
        project = get_object_or_404(Project, pk=project_id)
        data = ProjectDetailSerializer(project).data
        return api_success(data)

    def post(self, request, project_id, format=None):
        project = get_object_or_404(Project, pk=project_id)
        request_data = deepcopy(request.data)
        origin = deepcopy(project)
        origin_test_ids = list(project.tests.values_list('id', flat=True))

        if request_data.get('deployment_servers') and request_data.get('deployment_servers') not in ['null', '[]']:
            request_data['deployment_servers'] = json.dumps(request_data.get('deployment_servers'), ensure_ascii=False)

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
            #             quip_proposals_folders = cache.get('quip_projects_folders', {})
            #             if quip_folder_id not in quip_proposals_folders:
            #                 return api_bad_request('所选择的Quip文件夹不存在')
            bound_project_link = ProjectLinks.objects.exclude(project_id=project.id).filter(
                quip_folder_id=quip_folder_id).first()
            if bound_project_link:
                return api_bad_request("所择Quip文件夹已绑定项目【{}】".format(bound_project_link.project.name))

        # Quip工程师沟通文件
        quip_engineer_folder_id = request_data.get('quip_engineer_folder_id', None)
        if quip_engineer_folder_id:
            # quip_projects_engineer_folders = cache.get('quip_projects_engineer_folders', {})
            # if quip_engineer_folder_id not in quip_projects_engineer_folders:
            #     return api_bad_request('所选择的Quip工程师沟通文件夹不存在')
            bound_project_link = ProjectLinks.objects.exclude(project_id=project.id).filter(
                quip_engineer_folder_id=quip_engineer_folder_id).first()
            if bound_project_link:
                return api_bad_request("所选择的Quip工程师沟通文件已绑定项目【{}】".format(bound_project_link.project.name))
        # quip_folder的处理结束

        serializer = ProjectEditSerializer(project, data=request_data)
        if serializer.is_valid():
            project = serializer.save()
            # 支持多个测试人员的修改
            build_projects_tests(project, request)
            # 项目链接处理开始
            link_fields = ['gitlab_group_id', 'gitlab_project_id', 'api_document', 'ui_links', 'quip_folder_type',
                           'quip_engineer_folder_id']
            links_data = {'project': project.id}
            for link_field in link_fields:
                if link_field == 'ui_links' and request_data.get('ui_links', None):
                    links_data['ui_links'] = json.dumps(request_data.get('ui_links'), ensure_ascii=False)
                else:
                    links_data[link_field] = request_data.get(link_field, None)

            if quip_folder_type == 'select':
                links_data['quip_folder_id'] = quip_folder_id
            project_links_origin = None
            project_links, created = ProjectLinks.objects.get_or_create(project_id=project.id)
            if not created:
                project_links_origin = deepcopy(project_links)

            project_links_serializer = ProjectLinksSerializer(project_links, data=links_data)
            if not project_links_serializer.is_valid():
                return api_bad_request(message=project_links_serializer.errors)
            project_links = project_links_serializer.save()

            Log.build_update_object_log(operator=request.user, original=origin, updated=project)

            create_project_members_change_notifications(request, project, origin=origin,
                                                        origin_test_ids=origin_test_ids)
            send_project_deployment_server_notification(request, origin, project)

            if project_links_origin:
                Log.build_update_object_log(operator=request.user, original=project_links_origin, updated=project_links,
                                            related_object=project)
            else:
                Log.build_create_object_log(request.user, project_links, related_object=project)
            # 项目链接处理结束

            # celery异步任务
            # quip_folder的处理开始
            if project_links.quip_folder_type != 'no_need':
                if project_links.quip_folder_id:
                    update_quip_project_folder.delay(project.id)
                elif quip_folder_type == 'auto':
                    create_quip_project_folder.delay(project.id)

            if project_links.quip_engineer_folder_id:
                update_quip_project_engineer_folder.delay(project.id)
            # quip_folder的处理结束

            if project_links_origin:
                if project_links_origin.gitlab_group_id != project_links.gitlab_group_id or project_links_origin.gitlab_project_id != project_links.gitlab_project_id:
                    crawl_farm_project_recent_days_git_commits_issues.delay(project.id)
                    crawl_farm_project_recent_half_hour_git_demo_commits.delay(project.id)
            else:
                if project_links.gitlab_group_id or project_links.gitlab_project_id:
                    crawl_farm_project_recent_days_git_commits_issues.delay(project.id)
                    crawl_farm_project_recent_half_hour_git_demo_commits.delay(project.id)
            return Response({'result': True, 'data': serializer.data})
        return Response({"result": False, "message": serializer.errors})


@api_view(['PUT'])
def edit_project_desc(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    request_data = request.data
    serializer = ProjectSimpleEditSerializer(project, data=request_data)
    if serializer.is_valid():
        project = serializer.save()
        return Response({'result': True, 'data': serializer.data})
    return Response({"result": False, "message": serializer.errors})


class ProjectLinksDetail(APIView):
    def get(self, request, project_id, format=None):
        project_link = get_object_or_404(ProjectLinks, project_id=project_id)
        data = ProjectLinksDetailSerializer(project_link).data
        return api_success(data)

    def post(self, request, project_id, format=None):
        project = get_object_or_404(Project, pk=project_id)

        project_links_origin = None
        origin_quip_folder_type = None
        project_links, created = ProjectLinks.objects.get_or_create(project_id=project.id)
        if not created:
            project_links_origin = deepcopy(project_links)
            origin_quip_folder_type = project_links.quip_folder_type

        origin = deepcopy(project)
        request_data = request.data
        quip_folder_type = request_data.get('quip_folder_type', None) or origin_quip_folder_type
        quip_folder_id = request_data.get('quip_folder_id', None)
        if quip_folder_type in ['auto', 'no_need']:
            request_data.pop('quip_folder_id', None)
        elif quip_folder_type == 'select':
            if not quip_folder_id:
                return api_bad_request('Quip文件夹必选')
        else:
            return api_bad_request('Quip文件夹类型必选、可选值为auto、no_need、select')

        if quip_folder_id:
            bound_project_link = ProjectLinks.objects.exclude(project_id=project.id).filter(
                quip_folder_id=quip_folder_id).first()
            if bound_project_link:
                return api_bad_request("所择Quip文件夹已绑定项目【{}】".format(bound_project_link.project.name))

        # Quip工程师沟通文件
        quip_engineer_folder_id = request_data.get('quip_engineer_folder_id', None)
        if quip_engineer_folder_id:
            bound_project_link = ProjectLinks.objects.exclude(project_id=project.id).filter(
                quip_engineer_folder_id=quip_engineer_folder_id).first()
            if bound_project_link:
                return api_bad_request("所选择的Quip工程师沟通文件已绑定项目【{}】".format(bound_project_link.project.name))

        link_fields = ['gitlab_group_id', 'gitlab_project_id', 'api_document', 'ui_links', 'quip_folder_type',
                       'quip_engineer_folder_id']
        links_data = {'project': project.id}
        for link_field in link_fields:
            if link_field == 'ui_links' and request_data.get('ui_links', None):
                links_data['ui_links'] = json.dumps(request_data.get('ui_links'), ensure_ascii=False)
            else:
                links_data[link_field] = request_data.get(link_field, None)

        if quip_folder_type == 'select':
            links_data['quip_folder_id'] = quip_folder_id

        project_links_serializer = ProjectLinksSerializer(project_links, data=links_data)
        if not project_links_serializer.is_valid():
            return api_bad_request(message=project_links_serializer.errors)
        project_links = project_links_serializer.save()

        Log.build_update_object_log(operator=request.user, original=origin, updated=project)
        send_project_deployment_server_notification(request, origin, project)

        if project_links_origin:
            Log.build_update_object_log(operator=request.user, original=project_links_origin, updated=project_links,
                                        related_object=project)
        else:
            Log.build_create_object_log(request.user, project_links, related_object=project)
        # 项目链接处理结束

        # celery异步任务
        # quip_folder的处理开始
        if project_links.quip_folder_type != 'no_need':
            if project_links.quip_folder_id:
                update_quip_project_folder.delay(project.id)
            elif quip_folder_type == 'auto':
                create_quip_project_folder.delay(project.id)

        if project_links.quip_engineer_folder_id:
            update_quip_project_engineer_folder.delay(project.id)
        # quip_folder的处理结束

        if project_links_origin:
            if project_links_origin.gitlab_group_id != project_links.gitlab_group_id or project_links_origin.gitlab_project_id != project_links.gitlab_project_id:
                crawl_farm_project_recent_days_git_commits_issues.delay(project.id)
                crawl_farm_project_recent_half_hour_git_demo_commits.delay(project.id)
        else:
            if project_links.gitlab_group_id or project_links.gitlab_project_id:
                crawl_farm_project_recent_days_git_commits_issues.delay(project.id)
                crawl_farm_project_recent_half_hour_git_demo_commits.delay(project.id)
        return Response({'result': True})


@api_view(['PUT'])
def edit_project_links(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    origin = deepcopy(project)
    request_data = request.data
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
        bound_project_link = ProjectLinks.objects.exclude(project_id=project.id).filter(
            quip_folder_id=quip_folder_id).first()
        if bound_project_link:
            return api_bad_request("所择Quip文件夹已绑定项目【{}】".format(bound_project_link.project.name))

    # Quip工程师沟通文件
    quip_engineer_folder_id = request_data.get('quip_engineer_folder_id', None)
    if quip_engineer_folder_id:
        bound_project_link = ProjectLinks.objects.exclude(project_id=project.id).filter(
            quip_engineer_folder_id=quip_engineer_folder_id).first()
        if bound_project_link:
            return api_bad_request("所选择的Quip工程师沟通文件已绑定项目【{}】".format(bound_project_link.project.name))

    link_fields = ['gitlab_group_id', 'gitlab_project_id', 'api_document', 'ui_links', 'quip_folder_type',
                   'quip_engineer_folder_id']
    links_data = {'project': project.id}
    for link_field in link_fields:
        if link_field == 'ui_links' and request_data.get('ui_links', None):
            links_data['ui_links'] = json.dumps(request_data.get('ui_links'), ensure_ascii=False)
        else:
            links_data[link_field] = request_data.get(link_field, None)

    if quip_folder_type == 'select':
        links_data['quip_folder_id'] = quip_folder_id
    project_links_origin = None
    project_links, created = ProjectLinks.objects.get_or_create(project_id=project.id)
    if not created:
        project_links_origin = deepcopy(project_links)

    project_links_serializer = ProjectLinksSerializer(project_links, data=links_data)
    if not project_links_serializer.is_valid():
        return api_bad_request(message=project_links_serializer.errors)
    project_links = project_links_serializer.save()

    Log.build_update_object_log(operator=request.user, original=origin, updated=project)
    send_project_deployment_server_notification(request, origin, project)

    if project_links_origin:
        Log.build_update_object_log(operator=request.user, original=project_links_origin, updated=project_links,
                                    related_object=project)
    else:
        Log.build_create_object_log(request.user, project_links, related_object=project)
    # 项目链接处理结束

    # celery异步任务
    # quip_folder的处理开始
    if project_links.quip_folder_type != 'no_need':
        if project_links.quip_folder_id:
            update_quip_project_folder.delay(project.id)
        elif quip_folder_type == 'auto':
            create_quip_project_folder.delay(project.id)

    if project_links.quip_engineer_folder_id:
        update_quip_project_engineer_folder.delay(project.id)
    # quip_folder的处理结束

    if project_links_origin:
        if project_links_origin.gitlab_group_id != project_links.gitlab_group_id or project_links_origin.gitlab_project_id != project_links.gitlab_project_id:
            crawl_farm_project_recent_days_git_commits_issues.delay(project.id)
            crawl_farm_project_recent_half_hour_git_demo_commits.delay(project.id)
    else:
        if project_links.gitlab_group_id or project_links.gitlab_project_id:
            crawl_farm_project_recent_days_git_commits_issues.delay(project.id)
            crawl_farm_project_recent_half_hour_git_demo_commits.delay(project.id)
    return Response({'result': True})


@api_view(['GET'])
def project_technology_checkpoints(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    technology_checkpoints = project.technology_checkpoints.order_by('expected_at')
    data = TechnologyCheckpointSerializer(technology_checkpoints, many=True).data
    return api_success(data=data)


@api_view(['POST'])
def project_name(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    origin = deepcopy(project)
    project.name = request.data['name']
    project.save()
    Log.build_update_object_log(request.user, origin, project)
    return api_success()


class ProjectDeploymentServer(APIView):
    def get(self, request, project_id, format=None):
        project = get_object_or_404(Project, pk=project_id)
        deployment_servers = []
        if project.deployment_servers:
            deployment_servers = json.loads(project.deployment_servers, encoding='utf-8')

        return api_success(data=deployment_servers)

    def post(self, request, project_id, format=None):
        project = get_object_or_404(Project, pk=project_id)
        if request.data.get('deployment_servers') and request.data.get('deployment_servers') not in ['null', '[]']:
            origin = deepcopy(project)
            project.deployment_servers = json.dumps(request.data.get('deployment_servers'), ensure_ascii=False)
            project.save()
            Log.build_update_object_log(request.user, origin, project)
            send_project_deployment_server_notification(request, origin, project)
            return api_success()
        return Response({"result": False, "message": "部署服务器信息为必填"})


def send_project_deployment_server_notification(request, origin, project):
    user = request.user
    if origin.deployment_servers != project.deployment_servers:
        principals = User.objects.filter(username__in=settings.RESPONSIBLE_TPM_FOR_DEVOPS,
                                         is_active=True)
        content = '{user}更新了项目【{project}】部署服务器信息'.format(user=user.username, project=project.name)
        url = get_protocol_host(request) + build_page_path("project_view", kwargs={"id": project.id})
        for principal in principals:
            if principal.id != user.id:
                create_notification(principal, content, url)
        if project.manager_id and project.manager_id != user.id:
            create_notification(project.manager, content, url)


@api_view(['GET'])
def my_projects(request):
    user = request.user
    params = request.GET
    project_status = params.get('project_status', None)
    if project_status == 'ongoing':
        projects = Project.ongoing_projects()
    elif project_status == 'closed':
        projects = Project.completion_projects()
    else:
        projects = Project.objects.all()
    base_projects = projects
    if request.GET.get('any_member') in ['1', 1, 'true', True]:
        result_projects = get_user_projects(request.user, base_projects)
    else:
        manage_projects = base_projects.filter(manager_id=user.id)
        result_projects = manage_projects
    result_projects = result_projects.distinct().order_by('created_at')
    data = ProjectSimpleSerializer(result_projects, many=True).data
    return api_success(data=data)


@api_view(['GET', ])
def projects_gitlab_committers(request):
    projects = Project.ongoing_projects().filter(job_positions__isnull=False).distinct().order_by('-created_at')
    data, headers = build_pagination_queryset_data(request, projects, ProjectGitlabCommittersSerializer)
    projects_data_add_positions_gitlab_commits_data(data)
    return api_success(data=data, headers=headers)


@api_view(['GET', ])
def project_gitlab_committers(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    data = ProjectGitlabCommittersSerializer(project).data
    projects_data_add_positions_gitlab_commits_data([data, ])
    return api_success(data=data)


@api_view(['GET', ])
def projects_test_statistics(request):
    '''
    :param request:
    :return:
       {
        'result': True,
        'data': [
            {
                "id": 1,
                "username": "李帆平",
                "avatar": "https://farm.s3.cn-north-1.amazonaws.com.cn/avatar-29-2017-12-14_155750.196112",
                "avatar_color": "#2161FD",
                "bugs_data":
                    {
                        "every_data":
                            [
                                {
                                    "date": "2019-10-01",
                                    "opened_bugs": 10,
                                    "closed_bugs": 15,
                                    "created_cases": 0,
                                    'executed_cases': 0
                                    "projects_detail":
                                        [
                                            {"id": 1, "name": "我是项目一", "opened_bugs": 9, "closed_bugs": 10,"created_cases": 0,'executed_cases': 0},
                                            {"id": 1, "name": "我是项目二", "opened_bugs": 1, "closed_bugs": 5, "created_cases": 0,'executed_cases': 0}
                                        ]
                                }
                            ],
                        "opened_bugs": 10,
                        "closed_bugs": 15,
                        "created_cases": 0,
                        'executed_cases': 0
                    }
            }
        ]
    }
    '''

    build_today_test_statistics.delay()
    params = request.GET
    start_date = None
    end_date = None
    try:
        if params.get('start_date'):
            start_date = datetime.strptime(params.get('start_date'), '%Y-%m-%d').date()
        if params.get('end_date'):
            end_date = datetime.strptime(params.get('end_date'), '%Y-%m-%d').date()
    except Exception as e:
        return api_bad_request(message=str(e))

    # 默认14天
    if not end_date:
        end_date = timezone.now().date()
    if not start_date:
        start_date = timezone.now().date() - timedelta(days=13)

    if end_date < start_date:
        return api_bad_request("起始日期 不能大于截止日期")

    # 构造一个用户每天bugs数据和测试用例的数据结构模板
    bugs_data_temp = {
        "every_data": {},
        "opened_bugs": 0,
        "closed_bugs": 0,
        "created_cases": 0,
        'executed_cases': 0,
    }
    # 每天的数据结构模板
    day_data_temp = {
        "date": '',
        "opened_bugs": 0,
        "closed_bugs": 0,
        "created_cases": 0,
        'executed_cases': 0,
        "projects_detail": []
    }
    # 将日期的数据构造进模版
    date_list = get_date_list(start_date, end_date)
    for date in date_list:
        date_str = date.strftime(settings.DATE_FORMAT)
        day_data = deepcopy(day_data_temp)
        day_data['date'] = date_str
        bugs_data_temp["every_data"][date_str] = day_data
    # 构造一个用户每天bugs数据和测试用例的数据结构模板  结束

    # 所有测试人员
    test_list = User.objects.filter(groups__name=settings.GROUP_NAME_DICT["test"], is_active=True).distinct()
    test_list_data = UserBasicSerializer(test_list, many=True).data

    # 构造所有测试人员的test统计数据的字典 开始
    test_bugs_dict = {}

    for test_data in test_list_data:
        test_id = test_data['id']
        test_bugs_dict[test_id] = deepcopy(test_data)
        test_bugs_dict[test_id]["test_statistics"] = deepcopy(bugs_data_temp)
        # 构造所有测试人员的test统计数据的字典 结束

    test_days_statistics = TestDayStatistic.objects.filter(date__gte=start_date, date__lte=end_date)
    for test_day_statistic in test_days_statistics:
        day_str = test_day_statistic.date.strftime(settings.DATE_FORMAT)
        operator = test_day_statistic.operator
        if not operator or not operator.is_employee:
            continue

        test_id = test_day_statistic.operator.user.id
        if test_id in test_bugs_dict:
            current_test_statistics = test_bugs_dict[test_id]["test_statistics"]
            current_test_every_data = current_test_statistics["every_data"]
            # 本天
            current_day_data = current_test_every_data[day_str]
            for field in ('opened_bugs', 'closed_bugs', 'created_cases', 'executed_cases'):
                field_value = getattr(test_day_statistic, field, 0)
                current_day_data[field] = field_value
                current_test_statistics[field] = current_test_statistics[field] + field_value
            projects_detail = test_day_statistic.projects_detail
            current_day_data['projects_detail'] = json.loads(projects_detail,
                                                             encoding='utf-8') if projects_detail else []

    # 字典构造成数组
    result_data = []
    for test_data in test_bugs_dict.values():
        new_test_data = deepcopy(test_data)
        test_statistics = test_data["test_statistics"]
        every_data = test_statistics["every_data"]
        every_data_list = []
        for day_data in every_data.values():
            day_new_data = deepcopy(day_data)
            every_data_list.append(day_new_data)
        new_test_data["test_statistics"]["every_data"] = sorted(every_data_list, key=lambda x: x['date'], reverse=False)
        result_data.append(deepcopy(new_test_data))
    result_data = sorted(result_data, key=lambda x: ''.join(lazy_pinyin(x)))
    # cache.set('farm_projects_git_bugs', cache_git_bugs, None)
    return api_success(result_data)


@api_view(['GET', ])
def my_ongoing_projects(request):
    from farmbase.templatetags.mytags import my_active_projects, mentor_active_projects
    user = request.user
    user_projects = my_active_projects(user)
    mentor_projects = mentor_active_projects(user)

    member_projects_data = []
    for project in user_projects:
        project_data = {}
        project_data['name'] = project.name
        project_data['id'] = project.id
        project_data['user_undone_work_count'] = user_project_undone_work_count(user, project)
        project_data['demo_status'] = project.demo_status
        member_projects_data.append(project_data)

    mentor_projects_data = []
    for project in mentor_projects:
        project_data = {}
        project_data['name'] = project.name
        project_data['id'] = project.id
        project_data['user_undone_work_count'] = user_project_undone_work_count(user, project)
        project_data['demo_status'] = project.demo_status
        mentor_projects_data.append(project_data)

    return api_success(data={'mentor_projects': mentor_projects_data, 'member_projects': member_projects_data})


@api_view(['POST', ])
def project_open(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    if not project.done_at:
        return api_success()
    origin = deepcopy(project)
    project.done_at = None
    project.save()
    Log.build_update_object_log(request.user, origin, project)
    return api_success()


@api_view(['POST', ])
def project_done(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    if project.done_at:
        return api_success()
    for job in project.job_positions.all():
        if not job.star_rating and job.is_have_questionnaires:
            return api_bad_request('还有工程师未全部评分 不能关闭')

    origin = deepcopy(project)
    project.done_at = timezone.now()
    project.save()
    Log.build_update_object_log(request.user, origin, project)
    return api_success()


@api_view(['get'])
def project_done_check(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    project_jobs_payments_completed = True
    project_jobs_star_rating_completed = True
    project_payments_completed = True
    for job in project.job_positions.all():
        if not job.is_paid_off_valid_payments:
            project_jobs_payments_completed = False
            break
    for job in project.job_positions.all():
        if not job.star_rating and job.is_have_questionnaires:
            project_jobs_star_rating_completed = False
            break
    for payment in project.project_payments.all():
        if not payment.status == 'completed':
            project_payments_completed = False
            break
    data = {
        'project_jobs_payments_completed': project_jobs_payments_completed,
        'project_jobs_star_rating_completed': project_jobs_star_rating_completed,
        'project_payments_completed': project_payments_completed
    }
    return api_success(data)


@api_view(['POST', ])
def read_project_comments(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    user_id = request.user.id
    project_id = project.id
    job_positions = project.job_positions.all()
    for job_position in job_positions:
        if not job_position.star_rating:
            return Response({'result': False, 'message': '有工程师未评分，请项目经理评分'})
    comments_dict = cache.get('projects_users_read_comments_dict', {})
    last_view_at = timezone.now()
    if user_id not in comments_dict:
        comments_dict[user_id] = {}
    comments_dict[user_id][project_id] = {'last_view_at': last_view_at}
    cache.set('projects_users_read_comments_dict', comments_dict, None)
    return api_success()


@api_view(['GET', ])
def mobile_project_list(request):
    user_id = request.user.id
    project_status = request.GET.get('project_status', None)
    search_value = request.GET.get('search_value', None)
    page = request.GET.get('page', None)
    page_size = request.GET.get('page_size', None)
    if project_status == 'ongoing':
        projects = Project.ongoing_projects()
        if not has_any_function_perms(request.user, ['view_all_projects', 'view_ongoing_projects']):
            return Response({"result": False, "message": "你没有权限查看项目列表"})
    elif project_status == 'closed':
        projects = Project.completion_projects()
        if has_function_perm(request.user, 'view_all_projects'):
            pass
        elif has_function_perm(request.user, 'view_projects_finished_in_60_days'):
            user_projects = get_user_projects(request.user, projects)
            projects_finished_in_60_days = projects.filter(done_at__gte=timezone.now() - timedelta(days=60))
            projects = projects_finished_in_60_days | user_projects
            projects = projects.distinct()
        else:
            return Response({"result": False, "message": "你没有权限查看项目列表"})
    else:
        projects = Project.objects.order_by('-created_at')
        if not has_function_perm(request.user, 'view_all_projects'):
            return Response({"result": False, "message": "你没有权限查看项目列表"})

    if search_value:
        projects = projects.filter(
            Q(name__icontains=search_value) | Q(manager__username__icontains=search_value))

    return build_pagination_response(request, projects, ProjectsPageSerializer)


@api_view(['GET', ])
def project_filter_data(request):
    if not has_any_function_perms(request.user, ['view_all_projects', 'view_ongoing_projects']):
        undone_projects = []
    else:
        undone_projects = Project.ongoing_projects()

    if has_function_perm(request.user, 'view_all_projects'):
        closed_projects = Project.completion_projects()
    elif has_function_perm(request.user, 'view_projects_finished_in_60_days'):
        closed_projects = Project.completion_projects()
        user_projects = closed_projects.filter(manager=request.user)
        projects_finished_in_60_days = closed_projects.filter(done_at__gte=timezone.now() - timedelta(days=60))
        closed_projects = projects_finished_in_60_days | user_projects
    else:
        closed_projects = []

    ongoing = get_projects_filter_data(undone_projects, status='ongoing')
    closed = get_projects_filter_data(closed_projects, status='closed')
    return api_success(data={'ongoing': ongoing, 'closed': closed})


def get_projects_filter_data(projects, status=None):
    project_status_list = Project.PROJECT_STATUS
    if projects:
        manager_id_list = [manager for manager in set(projects.values_list('manager_id', flat=True)) if manager]
        tpm_id_list = [tpm for tpm in set(projects.values_list('tpm_id', flat=True)) if tpm]
        managers = User.objects.filter(id__in=manager_id_list).order_by('-is_active', 'date_joined')
        tpms = User.objects.filter(id__in=tpm_id_list).order_by('-is_active', 'date_joined')
        managers_data = UserFilterSerializer(managers, many=True).data
        tpms_data = UserFilterSerializer(tpms, many=True).data
    else:
        managers_data = []
        tpms_data = []
    if status == 'closed':
        status_data = [{"code": code, "name": name, "codename": code} for code, name in project_status_list if
                       code == 'completion']
    elif status == 'ongoing':
        status_data = [{"code": code, "name": name, "codename": code} for code, name in project_status_list if
                       code != 'completion']
    else:
        status_data = [{"code": code, "name": name, "codename": code} for code, name in project_status_list]
    data = {'managers': managers_data, 'tpms': tpms_data, 'status': status_data}
    return data


@api_view(['GET'])
def ongoing_projects(request):
    result_data = {"total": 0, "count": 0, "data": []}
    if has_any_function_perms(request.user, ['view_all_projects', 'view_ongoing_projects']):
        projects = Project.ongoing_projects().select_related('tpm', 'manager')
        result_data, headers = get_project_table_data(request, projects, project_status='ongoing')
        projects_data = result_data
        farm_projects_demo_status = cache.get('farm_projects_demo_status', {})
        if not farm_projects_demo_status:
            farm_projects_demo_status = crawl_farm_projects_recent_half_hour_git_demo_commits()

        for project_data in projects_data:
            project_id = project_data['id']
            if project_id in farm_projects_demo_status:
                project_data['demo_status'] = farm_projects_demo_status[project_id]

    return api_success(data=result_data, headers=headers)


@api_view(['GET'])
def get_closed_projects(request):
    closed_projects = Project.objects.none()
    if has_function_perm(request.user, 'view_all_projects'):
        closed_projects = Project.completion_projects().select_related('tpm', 'manager')
    elif has_function_perm(request.user, 'view_projects_finished_in_60_days'):
        closed_projects = Project.completion_projects().select_related('tpm', 'manager')
        user_projects = get_user_projects(request.user, closed_projects)
        projects_finished_in_60_days = closed_projects.filter(done_at__gte=timezone.now() - timedelta(days=60))
        closed_projects = projects_finished_in_60_days | user_projects
        closed_projects = closed_projects.distinct()

    data, headers = get_project_table_data(request, closed_projects, project_status='closed')
    return api_success(data=data, headers=headers)


def get_project_table_data(request, projects, project_status=None):
    params = request.GET
    manager_list = re.sub(r'[;；,，]', ' ', params.get('managers', '')).split()
    tpm_list = re.sub(r'[;；,，]', ' ', params.get('tpms', '')).split()
    status_list = re.sub(r'[;；,，]', ' ', params.get('status', '')).split()
    search_value = request.GET.get('search_value', None)
    if manager_list:
        projects = projects.filter(manager_id__in=manager_list)
    if tpm_list:
        projects = projects.filter(tpm_id__in=tpm_list)
    if status_list:
        project_id_list = []
        for project in projects:
            project_stages = project.current_stages
            for stage in project_stages:
                if stage.stage_type in status_list:
                    project_id_list.append(project.id)
        projects = projects.filter(pk__in=project_id_list)

    # 对关键字模糊检索
    if search_value:
        projects = projects.filter(
            Q(manager__username__icontains=search_value) | Q(tpm__username__icontains=search_value) | Q(
                name__icontains=search_value) | Q(
                product_manager__username__icontains=search_value))

    order_by = params.get('order_by', '')
    order_dir = params.get('order_dir', 'desc')
    if not order_by:
        order_by = 'created_at'
        if project_status == 'ongoing':
            order_by = 'created_at'
        if project_status == 'closed':
            order_by = 'done_at'
        order_dir = 'desc'
    # 判断 排序列表中是否存在对未完成任务数量进行排序
    if order_by == 'undone_tasks':
        projects = projects.annotate(undone_task_num=Sum(
            Case(When(tasks__is_done=False, then=1), default=0, output_field=IntegerField())))
        order_by = order_by.replace('undone_tasks', 'undone_task_num')
    if order_by == 'status':
        projects = sorted(projects, key=lambda x: sorted([Project.PROJECT_STATUS_DICT[i]['index'] for i in x.status],
                                                         reverse=False), reverse=(order_dir == 'desc'))
    else:
        if order_dir == 'desc':
            order_by = '-' + order_by
        projects = projects.order_by(order_by)

    return build_pagination_queryset_data(request, projects, ProjectsPageSerializer)


# 获取项目部署信息列表
@api_view(['GET'])
def projects_deployment_servers(request, project_status):
    projects = Project.objects.none()
    if project_status == 'ongoing':
        if has_any_function_perms(request.user, ['view_all_projects', 'view_ongoing_projects']):
            projects = Project.ongoing_projects().select_related('tpm', 'manager')
    elif project_status == 'closed':
        if has_function_perm(request.user, 'view_all_projects'):
            projects = Project.completion_projects().filter(deployment_servers__isnull=False).select_related('tpm',
                                                                                                             'manager').order_by(
                '-done_at')
        elif has_function_perm(request.user, 'view_projects_finished_in_60_days'):
            projects = Project.completion_projects().filter(deployment_servers__isnull=False).select_related('tpm',
                                                                                                             'manager')
            user_projects = get_user_projects(request.user, projects)
            projects_finished_in_60_days = projects.filter(done_at__gte=timezone.now() - timedelta(days=60))
            projects = projects_finished_in_60_days | user_projects
            projects = projects.distinct().order_by('-done_at')
    result_response = get_project_deployment_server_table_data_response(request, projects)
    return result_response


def get_project_deployment_server_table_data_response(request, projects):
    if projects:
        params = request.GET
        manager_list = re.sub(r'[;；,，]', ' ', params.get('managers', '')).split()
        tpm_list = re.sub(r'[;；,，]', ' ', params.get('tpms', '')).split()
        search_value = request.GET.get('search_value', None)
        if manager_list:
            projects = projects.filter(manager_id__in=manager_list)
        if tpm_list:
            projects = projects.filter(tpm_id__in=tpm_list)
        # 对关键字模糊检索
        if search_value:
            projects = projects.filter(
                Q(manager__username__icontains=search_value) | Q(tpm__username__icontains=search_value) | Q(
                    name__icontains=search_value))
    return build_pagination_response(request, projects, ProjectDeploymentSerializer)


def create_project_members_change_notifications(request, project, origin=None, origin_test_ids=[]):
    for field_data in Project.PROJECT_MEMBERS_FIELDS:
        field_name = field_data['field_name']
        if field_name == 'test':
            continue
        field_verbose_name = field_data['name']
        member = getattr(project, field_name)
        origin_member = getattr(origin, field_name) if origin else None
        if member and member != origin_member and member.id != request.user.id:
            notification_content = '你被分配为项目【{}】的{}'.format(project.name, field_verbose_name)
            notification_url = get_protocol_host(request) + '/projects/detail/?projectId={}'.format(project.id)
            create_notification(member, notification_content, notification_url)
    project_tests = project.tests.all()
    for project_test in project_tests:
        member = project_test
        if member.id not in origin_test_ids and member.id != request.user.id:
            notification_content = '你被分配为项目【{}】的测试'.format(project.name)
            notification_url = get_protocol_host(request) + '/projects/detail/?projectId={}'.format(project.id)
            create_notification(member, notification_content, notification_url)


def build_projects_tests(project, request):
    test_ids = request.data.get('tests', None)
    origin_ids = set(project.project_tests.values_list('id', flat=True))
    new_ids = set()
    deleted_ids = set()
    if test_ids is not None:
        for test_id in test_ids:
            project_test, created = ProjectTest.objects.get_or_create(project_id=project.id, test_id=test_id)
            new_ids.add(project_test.id)
        deleted_ids = list(origin_ids - new_ids)
    if deleted_ids:
        ProjectTest.objects.filter(id__in=list(deleted_ids)).delete()
    first_project_test = project.project_tests.order_by('created_at').first()
    if first_project_test:
        project.test = first_project_test.test
        project.save()


class ProjectMemberList(APIView):
    def get(self, request, project_id, format=None):
        project = get_object_or_404(Project, pk=project_id)
        data = get_project_members_dict(project)
        data['id'] = project.id
        data['name'] = project.name
        return api_success(data)

    def post(self, request, project_id, format=None):
        project = get_object_or_404(Project, pk=project_id)
        origin = deepcopy(project)
        origin_test_ids = list(project.tests.values_list('id', flat=True))
        serializer = ProjectMembersSerializer(project, data=request.data, partial=True)
        if serializer.is_valid():
            project = serializer.save()
            build_projects_tests(project, request)
            create_project_members_change_notifications(request, project, origin=origin,
                                                        origin_test_ids=origin_test_ids)
            send_project_data_update_reminder.delay(project_id)
            Log.build_update_object_log(operator=request.user, original=origin, updated=project)
            return api_success()
        return Response({"result": False, 'message': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def project_gantt_chart_members(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    project_data = ProjectMembersSerializer(project).data

    # 甘特图角色的选项
    member_list = []
    for field_dict in Project.PROJECT_MEMBERS_FIELDS:
        role_type = field_dict['field_name']
        if role_type == 'test':
            name = field_dict['name']
            project_tests = project.tests.all()
            for test in project_tests:
                member = {}
                member['role_type'] = role_type
                member['name'] = '{name}-{username}'.format(name=name, username=test.username)
                member['user'] = get_user_data(test)
                member_list.append(member)
        else:
            project_member = project_data.get(role_type, None)
            name = field_dict['name']
            if project_member:
                member = {}
                member['role_type'] = role_type
                member['name'] = '{name}-{username}'.format(name=name, username=project_member['username'])
                member['user'] = project_member
                member_list.append(member)

    # 项目工程师的选项
    job_positions = project.job_positions.all()
    position_set = set()
    if job_positions.exists():
        positions = JobSimpleSerializer(job_positions, many=True).data
        for position in positions:
            member = {}
            if position['role']:
                member['role_type'] = position['role']['name']
                member['name'] = position['role']['name']
                if position['developer']:
                    member['developer'] = position['developer']
                    member['name'] = position['role']['name'] + '-' + position['developer']['name']
                    member_key = member['role_type'] + str(member['developer']['id'])
                    if member_key in position_set:
                        continue
                    member_list.append(member)
                    position_set.add(member_key)

    return Response({"result": True, 'data': member_list})


@api_view(['GET'])
def project_job_positions_simple_list(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    job_positions = project.job_positions.order_by('created_at')
    serializer = JobSimpleSerializer(job_positions, many=True)
    return api_success(serializer.data)


class ProjectJobPositionsList(APIView):
    def get(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        job_positions = project.job_positions.order_by('created_at')
        serializer_class = JobWithPaymentsSerializer
        if request.GET.get("read_only", False) in ['true', True, '1', 1]:
            serializer_class = JobReadOnlySerializer
        data = serializer_class(job_positions, many=True).data
        return api_success(data)

    def post(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        request_data = deepcopy(request.data)
        request_data['project'] = project.id
        role_id = request_data.pop('role', None)
        developer_id = request_data.pop('developer', None)

        if not role_id or not Role.objects.filter(pk=role_id).exists():
            return Response({"result": False, 'message': '职位不存在'})
        role = Role.objects.get(pk=role_id)
        if not developer_id or not role.developers.filter(pk=developer_id).exists():
            return Response({"result": False, 'message': '职位:{} 中不包含该工程师'.format(role.name)})
        request_data['role'] = role_id
        request_data['developer'] = developer_id
        serializer = JobCreateSerializer(data=request_data)
        if serializer.is_valid():
            job = serializer.save()
            update_developer_partners_cache_data.delay(job.developer.id)
            Log.build_create_object_log(request.user, job, related_object=job.project)
            return Response({"result": True, "data": JobSerializer(job).data})
        return Response({"result": False, "message": str(serializer.errors)})


@api_view(['GET'])
def project_jobs_payments_statistic(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    jobs = project.job_positions.all()
    '''【code review】增加无合同打款项20000元'''
    # statistic_data = {
    #     'total_amount': 0,
    #     'no_contract_amount': 0,
    #     'paid_payment_amount': 0,
    #     'ongoing_payment_amount': 0,
    #     'recorded_payment_amount': 0,
    #     'remaining_payment_amount': 0
    # # }
    counter_sum = Counter()
    for job in jobs:
        counter_sum += Counter(job.payments_statistics)
    return api_success(dict(counter_sum))


class MyProjectJobPositionsPayments(APIView):
    def get(self, request):
        job_positions = JobPosition.objects.all()
        project_status = request.GET.get('project_status', None)
        search = request.GET.get('search', None)
        if project_status and project_status == 'ongoing':
            job_positions = job_positions.filter(project__done_at__isnull=True)
        elif project_status and project_status == 'closed':
            job_positions = job_positions.filter(project__done_at__isnull=False)
        if search:
            job_positions = job_positions.filter(project__name__icontains=search)
        job_positions = job_positions.filter(Q(payments__isnull=False) | Q(job_contracts__isnull=False),
                                             project__manager=request.user).distinct()
        jobs_data = JobWithPaymentsSerializer(job_positions, many=True).data
        data = {}
        for job_position in jobs_data:
            project_id = job_position['project']['id']
            if project_id not in data:
                data[project_id] = deepcopy(job_position['project'])
                project = Project.objects.get(pk=project_id)
                data[project_id]['members_dict'] = get_project_members_dict(project)
                data[project_id]['job_positions'] = []
                project = Project.objects.get(pk=project_id)
                data[project_id]['members_dict'] = get_project_members_dict(project)
            data[project_id]['job_positions'].append(job_position)
        data = sorted(data.values(), key=lambda x: x['created_at'], reverse=True)
        return api_success(data=data)


class JobPositionDetail(APIView):
    def get(self, request, position_id):
        job_position = get_object_or_404(JobPosition, pk=position_id)
        serializer = JobWithPaymentsSerializer(job_position)
        return Response({"result": True, "data": serializer.data})

    # def post(self, request, position_id):
    #     position = get_object_or_404(JobPosition, pk=position_id)
    #     origin = deepcopy(position)
    #     serializer = JobPositionEditSerializer(position, data=request.data)
    #     if serializer.is_valid():
    #         pay = request.data['pay']
    #         normal_payment_amount = position.normal_payment_amount
    #         if normal_payment_amount:
    #             if not pay or float(pay) < normal_payment_amount:
    #                 return Response({"result": False, "message": "报酬不能小于已打款记录总和:{}元".format(normal_payment_amount)})
    #         position = serializer.save()
    #         Log.build_update_object_log(request.user, origin, position, comment=request.data.get('comment'))
    #         Log.build_update_object_log(request.user, origin, position, related_object=position.project,
    #                                     comment=request.data.get('comment'))
    #         return Response({"result": True, "data": serializer.data})
    #     return Response({"result": False, "message": str(serializer.errors)})

    def delete(self, request, position_id):
        position = get_object_or_404(JobPosition, id=position_id)
        project = position.project
        '''【code review】
            1、工程师无正常的打款记录 且 无处在待签约、已签约状态的合同时，可以删除工程师
        '''
        if not position.can_be_deleted:
            return api_bad_request('工程师无正常的打款记录 且 无处在待签约、已签约状态的合同时，可以删除工程师')

        origin = deepcopy(position)
        position.delete()
        Log.build_delete_object_log(request.user, origin, project)
        if origin.developer:
            update_developer_cache_data.delay(origin.developer.id)
        return api_success()


@api_view(['GET'])
@cache_page(60 * 30)
def all_positions_star_ratings(request):
    queryset = JobPosition.objects.filter(job_standard_score__isnull=False).order_by(
        '-job_standard_score__created_at')
    return build_pagination_response(request, queryset, JobReadOnlySerializer)


class JobPositionStandardScore(APIView):
    def get(self, request, position_id):
        job_score = JobStandardScore.objects.filter(job_position_id=position_id).first()
        serializer = JobStandardScoreSerializer(job_score)
        return Response(serializer.data)

    def post(self, request, position_id):
        job = get_object_or_404(JobPosition, pk=position_id)
        project = job.project
        # 职位已经有标准评分 不能再评分
        # 只有该项目的项目经理可以进行标准评分
        # TPM、设计、测试、产品经理、项目经理中  除去项目经理后 还有人没有对该职位填写参考评分，则不能评分（以人为准，不以项目中角色为准，比如其他角色都和项目经理是同一个人，项目经理可以直接进行标准评分）
        # 各项评分必填 且为1-5
        job_score = JobStandardScore.objects.filter(job_position_id=position_id).first()
        if job_score:
            return api_bad_request("职位已经有标准评分 不能再评分")
        if request.user.id != project.manager_id and not request.user.is_superuser:
            return api_bad_request("只有该项目的项目经理可以进行标准评分")
        for member in project.need_star_rating_members:
            if member and member.is_active and member.id != project.manager_id:
                if not member.job_reference_scores.filter(job_position_id=position_id).exists():
                    return Response({"result": False, "message": "有未评分成员:{}， 项目经理不能进行最终评分".format(member.username)})
        if not job.developer:
            return Response({"result": False, "message": "该岗位无工程师，不能评分"})
        request.data['score_person'] = request.user.id
        request.data['job_position'] = position_id
        serializer = JobStandardScoreSerializer(data=request.data)
        if serializer.is_valid():
            review = serializer.save()
            update_developer_rate_cache_data.delay(job.developer.id)
            Log.build_create_object_log(request.user, review, related_object=review.job_position)
            return Response({"result": True, "data": serializer.data})
        return Response({"result": False, "message": str(serializer.errors)})


class JobPositionReferenceScore(APIView):
    def get(self, request, position_id):
        score_person = request.user
        job_score = JobReferenceScore.objects.filter(job_position_id=position_id, score_person=score_person).first()
        serializer = JobReferenceScoreSerializer(job_score)
        return Response({"result": True, "data": serializer.data})

    def post(self, request, position_id):
        job = get_object_or_404(JobPosition, pk=position_id)
        project = job.project
        if request.user not in project.need_star_rating_members:
            return Response({"result": False, "message": "不属于该项目的成员，不能参考评分"})
        if not job.developer:
            return Response({"result": False, "message": "该岗位无工程师，不能评分"})
        request.data['score_person'] = request.user.id
        request.data['job_position'] = position_id
        serializer = JobReferenceScoreSerializer(data=request.data)
        review = JobReferenceScore.objects.filter(job_position_id=position_id, score_person_id=request.user.id).first()
        origin = None
        if review:
            origin = deepcopy(review)
            serializer = JobReferenceScoreSerializer(review, data=request.data)
        if serializer.is_valid():
            review = serializer.save()
            if origin:
                Log.build_update_object_log(request.user, origin, review, related_object=job)
            else:
                Log.build_create_object_log(request.user, review, related_object=job)
            return Response({"result": True, "data": serializer.data})
        return Response({"result": False, "message": str(serializer.errors)})


@api_view(['GET'])
def all_role_job_score(request, position_id):
    job = get_object_or_404(JobPosition, pk=position_id)
    project = job.project
    reference_score_data = JobReferenceScoreSerializer(job.job_reference_scores, many=True).data
    manager_score = JobStandardScore.objects.filter(job_position_id=position_id).first()
    manager_score_data = JobStandardScoreSerializer(manager_score).data if manager_score else None

    data = {"reference_score_data": reference_score_data, "standard_score_data": manager_score_data,
            "project_bugs_statistics": job.project_bugs_statistics}
    return api_success(data)


class QuestionnaireList(APIView):
    def get(self, request):
        params = request.GET
        written_by = params.get('written_by', '')
        engineer_type = params.get('engineer_type', '')
        status = params.get('status', '')
        written_by_list = re.sub(r'[;；,，]', ' ', written_by).split()
        engineer_type_list = re.sub(r'[;；,，]', ' ', engineer_type).split()
        questionnaires = Questionnaire.objects.filter(status=status).order_by('-created_at')
        if written_by_list:
            questionnaires = questionnaires.filter(written_by__in=written_by_list)
        if engineer_type_list:
            questionnaires = questionnaires.filter(engineer_type__in=engineer_type_list)
        questionnaires_data = QuestionnaireSerializer(questionnaires, many=True).data
        return api_success(data=questionnaires_data)

    @transaction.atomic
    def post(self, request):
        request_data = deepcopy(request.data)
        savepoint = transaction.savepoint()
        written_by = request_data.get('written_by', '')
        engineer_type = request_data.get('engineer_type', '')
        question_list = request_data.get('questions', '')
        questionnaire_request_data = {'written_by': written_by, 'engineer_type': engineer_type,
                                      'version': Questionnaire.get_new_version(written_by, engineer_type)}
        serializer = QuestionnaireCreateSerializer(data=questionnaire_request_data)
        try:
            serializer.is_valid(raise_exception=True)
            questionnaire = serializer.save()
            for question in question_list:
                question_data = {'type': question['type'], 'title': question['question'],
                                 'questionnaire': questionnaire.id, 'index': Question.get_new_index(questionnaire)}
                question_serializer = QuestionCreateSerializer(data=question_data)
                question_serializer.is_valid(raise_exception=True)
                question_obj = question_serializer.save()
                answers = question['answer']
                for answer in answers:
                    answer['question'] = question_obj.id
                    answer['index'] = Choice.get_new_index(question_obj)
                    answer_serializer = ChoiceCreateSerializer(data=answer)
                    answer_serializer.is_valid(raise_exception=True)
                    answer_serializer.save()
        except Exception as e:
            transaction.savepoint_rollback(savepoint)
            return api_bad_request(str(e))
        return api_success()


@api_view(['GET'])
def get_questionnaires_online_history(request):
    request_data = request.GET
    written_by = request_data.get('written_by', '')
    engineer_type = request_data.get('engineer_type', '')
    questionnaires = Questionnaire.objects.filter(written_by=written_by,
                                                  engineer_type=engineer_type,
                                                  status__in=['online', 'history'])

    questionnaires_data = QuestionnaireSerializer(questionnaires, many=True).data
    return api_success(data=questionnaires_data)


class QuestionnaireDetail(APIView):
    @transaction.atomic
    def put(self, request, questionnaire_id):
        questionnaire = get_object_or_404(Questionnaire, pk=questionnaire_id)
        request_data = deepcopy(request.data)
        savepoint = transaction.savepoint()
        question_list = request_data.get('questions', '')
        try:
            question_origin_ids = set(questionnaire.questions.values_list('id', flat=True))
            question_new_ids = set()
            for question in question_list:
                question_data = {'type': question['type'], 'title': question['question'],
                                 'questionnaire': questionnaire.id, 'index': Question.get_new_index(questionnaire)}
                question_serializer = QuestionCreateSerializer(data=question_data)
                if 'id' in question:
                    old_question = get_object_or_404(Question, pk=question['id'])
                    question_serializer = QuestionEditSerializer(old_question, data=question_data)
                question_serializer.is_valid(raise_exception=True)
                question_obj = question_serializer.save()
                question_new_ids.add(question_obj.id)
                answers = question['answer']
                answer_origin_ids = set(question_obj.choices.values_list('id', flat=True))
                answer_new_ids = set()
                for answer in answers:
                    answer['question'] = question_obj.id
                    answer['index'] = Choice.get_new_index(question_obj)
                    answer_serializer = ChoiceCreateSerializer(data=answer)
                    if 'id' in answer:
                        old_answer = get_object_or_404(Choice, pk=answer['id'])
                        answer_serializer = ChoiceEditSerializer(old_answer, data=answer)
                    answer_serializer.is_valid(raise_exception=True)
                    answer_obj = answer_serializer.save()
                    answer_new_ids.add(answer_obj.id)
                answer_deleted_ids = list(answer_origin_ids - answer_new_ids)
                deleted_answers = question_obj.choices.filter(pk__in=answer_deleted_ids).delete()
        except Exception as e:
            transaction.savepoint_rollback(savepoint)
            return api_bad_request(str(e))
        question_deleted_ids = list(question_origin_ids - question_new_ids)
        deleted_questions = questionnaire.questions.filter(pk__in=question_deleted_ids).delete()
        return api_success()

    def delete(self, request, questionnaire_id):
        questionnaire = get_object_or_404(Questionnaire, pk=questionnaire_id)
        questionnaire.delete()
        return api_success()


@api_view(['POST'])
def issue_questionnaire(request, questionnaire_id):
    questionnaire = get_object_or_404(Questionnaire, pk=questionnaire_id)
    online_questionnaire = Questionnaire.objects.filter(written_by=questionnaire.written_by,
                                                        engineer_type=questionnaire.engineer_type,
                                                        status='online').first()
    if online_questionnaire:
        online_questionnaire.status = 'history'
        old_version = online_questionnaire.version
        online_questionnaire.save()
        questionnaire.version = old_version + 1
    questionnaire.status = 'online'
    questionnaire.publish_at = timezone.now()
    questionnaire.save()
    return api_success()


@api_view(['GET'])
def get_grade_staffs(request, position_id):
    job_position = get_object_or_404(JobPosition, pk=position_id)
    job_position_questionnaire = JobPositionWithQuestionnaire(job_position).data
    return api_success(job_position_questionnaire)


@api_view(['GET'])
def get_staff_questionnaire(request, position_id):
    job_position = get_object_or_404(JobPosition, pk=position_id)
    user_id = request.GET.get('user', '')
    if user_id:
        user_id = int(user_id)
    role = None
    if job_position.project.tests:
        for test in job_position.project.tests.all():
            if user_id == test.id:
                role = 'test'
    if job_position.project.designer:
        if user_id == job_position.project.designer.id:
            role = 'designer'
    if job_position.project.tpm:
        if user_id == job_position.project.tpm.id:
            role = 'tpm'
    if job_position.project.manager:
        if user_id == job_position.project.manager.id:
            role = 'manager'
    if job_position.project.product_manager:
        if user_id == job_position.project.product_manager.id:
            role = 'manager'
    job_position_role = 'developer'
    if job_position.role.name in '测试工程师':
        job_position_role = 'test'
    elif job_position.role.name in '设计师':
        job_position_role = 'designer'
    questionnaire = Questionnaire.objects.filter(written_by=role, engineer_type=job_position_role,
                                                 status='online').first()
    serializer_data = QuestionnaireSerializer(questionnaire).data
    serializer_data['remarks'] = None
    grade_questionnaire = GradeQuestionnaire.objects.filter(job_position=job_position, questionnaire=questionnaire,
                                                            score_person_id=user_id).first()
    if grade_questionnaire:
        serializer_data['remarks'] = grade_questionnaire.remarks
        for question in serializer_data['questions']:
            answer_sheet = grade_questionnaire.answer_sheets.filter(question=question['id']).first()
            answer_sheet_data = AnswerSheetSerializer(answer_sheet).data
            question['answer'] = answer_sheet_data
    return api_success(serializer_data)


@api_view(['POST'])
def submit_questionnaire(request, position_id):
    job_position = get_object_or_404(JobPosition, pk=position_id)
    questionnaire = request.data.get('questionnaire', '')
    answers = request.data.get('answers', '')
    remarks = request.data.get('remarks', '')
    grade_questionnaire_data = {"questionnaire": questionnaire, "score_person": request.user.id,
                                "job_position": position_id, "remarks": remarks}
    grade_questionnaire_serializer = GradeQuestionnaireCreateSerializer(data=grade_questionnaire_data)
    with transaction.atomic():
        sid = transaction.savepoint()
        try:
            grade_questionnaire_serializer.is_valid(raise_exception=True)
            grade_questionnaire = grade_questionnaire_serializer.save()
            job_reference_score_data = {"communication": 0, "efficiency": 0, "quality": 0,
                                        "execute": 0, "score_person": request.user.id, "job_position": position_id}
            question_count = {"communication": 0, "efficiency": 0, "quality": 0, "execute": 0, }
            for answer in answers:
                answer['grade_questionnaire'] = grade_questionnaire.id
                answer_serializer = AnswerSheetCreateSerializer(data=answer)
                answer_serializer.is_valid(raise_exception=True)
                answer_obj = answer_serializer.save()
                question_type = answer_obj.question.type
                if question_type != 'others':
                    choice_score = answer_obj.choice.score if answer_obj.choice else 0
                    job_reference_score_data[question_type] += choice_score
                    if choice_score:
                        question_count[question_type] += 1
            job_reference_score_data['communication'] = round(
                job_reference_score_data['communication'] / question_count[
                    'communication'], 1) if question_count['communication'] else 0
            job_reference_score_data['efficiency'] = round(job_reference_score_data['efficiency'] / question_count[
                'efficiency'], 1) if question_count['efficiency'] else 0
            job_reference_score_data['quality'] = round(job_reference_score_data['quality'] / question_count[
                'quality'], 1) if question_count['quality'] else 0
            job_reference_score_data['execute'] = round(job_reference_score_data['execute'] / question_count[
                'execute'], 1) if question_count['execute'] else 0
            job_reference_score_serializer = JobReferenceScoreSerializer(data=job_reference_score_data)
            job_reference_score_serializer.is_valid(raise_exception=True)
            job_reference_score_serializer.save()
        except Exception as e:
            transaction.savepoint_rollback(sid)
            return api_bad_request(str(e))
        else:
            transaction.savepoint_commit(sid)
    return api_success()


@api_view(['POST'])
def skip_questionnaire(request, position_id):
    job_position = get_object_or_404(JobPosition, pk=position_id)
    questionnaire = request.data.get('questionnaire', '')
    remarks = request.data.get('remarks', '')
    grade_questionnaire_data = {"questionnaire": questionnaire, "score_person": request.user.id,
                                "job_position": position_id, "is_skip_grade": True, "remarks": remarks}
    grade_questionnaire_serializer = GradeQuestionnaireCreateSerializer(data=grade_questionnaire_data)
    if grade_questionnaire_serializer.is_valid():
        grade_questionnaire = grade_questionnaire_serializer.save()
        return api_success()
    return api_bad_request(grade_questionnaire_serializer.errors)


@api_view(['GET'])
def get_final_score(request, position_id):
    job_position = get_object_or_404(JobPosition, pk=position_id)
    job_reference_scores = job_position.job_reference_scores.all()
    if not job_reference_scores:
        return api_bad_request('还未有人评分，无法获取最终评分')
    score = cache.get('job_position_score_{}'.format(position_id), None)
    if score:
        return api_success(score)
    score = {
        "communication": {"score": 0, "count": 0},
        "efficiency": {"score": 0, "count": 0},
        "quality": {"score": 0, "count": 0},
        "execute": {"score": 0, "count": 0},
    }
    for job_reference_score in job_reference_scores:
        if job_reference_score.communication != 0:
            score['communication']['score'] += job_reference_score.communication
            score['communication']['count'] += 1
        if job_reference_score.efficiency != 0:
            score['efficiency']['score'] += job_reference_score.efficiency
            score['efficiency']['count'] += 1
        if job_reference_score.quality != 0:
            score['quality']['score'] += job_reference_score.quality
            score['quality']['count'] += 1
        if job_reference_score.execute != 0:
            score['execute']['score'] += job_reference_score.execute
            score['execute']['count'] += 1
    score['communication'] = round(score[
                                       'communication']['score'] / score['communication']['count'], 1) if \
        score['communication']['count'] else 0
    score['efficiency'] = round(score['efficiency']['score'] / score['efficiency']['count'], 1) if score['efficiency'][
        'count'] else 0
    score['quality'] = round(score['quality']['score'] / score['quality']['count'], 1) if score['quality'][
        'count'] else 0
    score['execute'] = round(score['execute']['score'] / score['execute']['count'], 1) if score['execute'][
        'count'] else 0
    total_score = sum(score.values())
    total_count = 0
    for i in score.values():
        if i != 0:
            total_count += 1
    score['average'] = round(total_score / total_count, 1) if total_count else ''
    cache.set('job_position_score_{}'.format(position_id), score)
    return api_success(score)


@api_view(['POST'])
def submit_final_score(request, position_id):
    job_position = get_object_or_404(JobPosition, pk=position_id)
    evaluate = request.data.get('evaluate', '')
    score = cache.get('job_position_score_{}'.format(position_id), None)
    if not score:
        return api_bad_request('评分未完成无法发布最终评分')
    del score['average']
    score['evaluate'] = evaluate
    score['score_person'] = request.user.id
    score['job_position'] = position_id
    serializer = JobStandardScoreSerializer(data=score)
    if serializer.is_valid():
        job_standard_score = serializer.save()
        return api_success()
    return api_bad_request(serializer.errors)


@api_view(['GET'])
def get_position_score(request, position_id):
    job_position = get_object_or_404(JobPosition, pk=position_id)
    job_standard_score = JobStandardScore.objects.filter(job_position=job_position).first()
    if not job_standard_score:
        return api_bad_request('还未发布最终评分，没有相关数据')
    score_data = JobStandardScoreWithGradeSerializer(job_standard_score).data
    return api_success(score_data)


class ProjectStageDetail(APIView):
    def get(self, request, project_id, format=None):
        project = get_object_or_404(Project, pk=project_id)
        serializer = ProjectWithStagesSerializer(project)
        return Response({"result": True, "data": serializer.data})

    @transaction.atomic
    def post(self, request, project_id, format=None):
        project = get_object_or_404(Project, pk=project_id)
        comment = request.data.get('comment', None)
        savepoint = transaction.savepoint()
        request_data = request.data
        stages_data = request.data.get('stages')
        today = timezone.now().date()

        if request_data['start_date'] > request_data['end_date']:
            return api_bad_request('项目开始时间不能大于结束时间')
        project_serializer = ProjectSimpleEditSerializer(project, data=request.data)
        if not project_serializer.is_valid():
            return api_bad_request(str(project_serializer.errors))
        project = project_serializer.save()

        origin_stages = project.project_stages.all()
        # 用来对比 判断 甘特图模板是否需要更新
        origin_stage_data = {
            (stage.id, stage.start_date, stage.end_date) for stage in origin_stages
        }
        # 存下来原来的id集合
        origin_ids = set(project.project_stages.values_list('id', flat=True))
        # 新的阶段的id集合
        new_ids = set()
        for index, stage_data in enumerate(stages_data):
            stage_data['index'] = index
            stage_data['project'] = project_id
            serializer = ProjectStageCreateSerializer(data=stage_data)
            origin_stage = None
            if 'id' in stage_data:
                project_stage_old = ProjectStage.objects.filter(id=stage_data['id']).first()
                if not project_stage_old:
                    transaction.savepoint_rollback(savepoint)
                    return api_bad_request('项目阶段不存在')
                if project_stage_old.stage_type != stage_data['stage_type']:
                    transaction.savepoint_rollback(savepoint)
                    return api_bad_request('不能修改已创建的项目阶段的类型')
                origin_stage = deepcopy(project_stage_old)
                serializer = ProjectStageEditSerializer(project_stage_old, data=stage_data)
            if serializer.is_valid():
                if stage_data['start_date'] < request_data['start_date'] or stage_data['end_date'] > request_data[
                    'end_date']:
                    transaction.savepoint_rollback(savepoint)
                    return api_bad_request('项目阶段的时间段不能超出项目的启动或者结束日期')
                if stage_data['start_date'] > stage_data['end_date']:
                    transaction.savepoint_rollback(savepoint)
                    return api_bad_request('项目阶段的起始日期不能小于结束日期')
                project_stage = serializer.save()
                new_ids.add(project_stage.id)
            else:
                transaction.savepoint_rollback(savepoint)
                return api_bad_request(str(serializer.errors))
            # 项目阶段操作记录
            if origin_stage:
                Log.build_update_object_log(request.user, origin_stage, project_stage, related_object=project,
                                            codename='schedule')
            else:
                Log.build_create_object_log(request.user, project_stage, related_object=project, codename='schedule')
        if comment:
            Comment.objects.create(author=request.user, content=comment, content_object=project)
        # 需要删除的stage_ids是差集
        deleted_ids = list(origin_ids - new_ids)
        deleted_stages = project.project_stages.filter(pk__in=deleted_ids)
        for deleted_stage in deleted_stages:
            Log.build_delete_object_log(request.user, deleted_stage, related_object=project, codename='schedule')
            deleted_stage.delete()

        # 项目未完成更新  甘特图、项目技术检查点、playbook
        if not project.done_at and not project.end_date <= today:
            # 一键更新甘特图模板缓存数据
            new_stage_data = {(stage.id, stage.start_date, stage.end_date) for stage in project.project_stages.all()}
            update_cache_of_need_update_gantt_template_projects(project, new_stage_data, origin_stage_data)
            # 更新项目技术检查点
            update_project_technology_checkpoints(project)
            #  根据新的时刻表 更新playbook
            update_project_playbook_for_schedule(project)
        else:
            remove_project_need_update_gantt_template_cache_data(project)

        content = '{}修改了项目【{}】的日程表 修改备注：{}'.format(request.user.username, project.name, comment)

        url = get_protocol_host(request) + build_page_path("project_view", kwargs={"id": project.id})

        member_types = ['manager', 'product_manager', 'tpm', 'test']
        notification_users = []
        for member_type in member_types:
            member = getattr(project, member_type, None)
            if member and member.is_active and member.id != request.user.id:
                notification_users.append(member)
        if notification_users:
            create_notification_to_users(notification_users, content, url=url)

        send_project_schedule_update_reminder.delay('project', project.id)
        return Response({"result": True, "message": "项目关键点更新成功"})


@api_view(['GET'])
def get_project_stages_groups(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    stages = project.project_stages.all()
    data = {}
    for stage in stages:
        stage_data = ProjectStageSimpleSerializer(stage, many=False).data
        if stage.get_stage_type_display() not in data:
            data[stage.get_stage_type_display()] = []
        data[stage.get_stage_type_display()].append(stage_data)
    return api_success(data)


@api_view(['POST'])
def hide_schedule_remarks(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    project_schedule_remarks_hidden_set = cache.get('project_schedule_remarks_hidden_set', set())
    project_schedule_remarks_hidden_set.add(project.id)

    cache.set('project_schedule_remarks_hidden_set', project_schedule_remarks_hidden_set, None)

    return Response({"result": True, "message": "", "data": None})


class TechnologyCheckpointDetail(APIView):
    def get(self, request, checkpoint_id):
        checkpoint = get_object_or_404(TechnologyCheckpoint, pk=checkpoint_id)
        if checkpoint.name == TechnologyCheckpoint.DEV_DOCS_CHECKPOINT:
            checkpoint.project.rebuild_dev_docs_checkpoint_status()

        data = TechnologyCheckpointSerializer(checkpoint).data
        if checkpoint.name == "开发测试环境部署":
            deployment_servers = []
            project = checkpoint.project
            if project.deployment_servers:
                deployment_servers = json.loads(project.deployment_servers, encoding='utf-8')
            data['project']["deployment_servers"] = deployment_servers
        return api_success(data=data)

    def post(self, request, checkpoint_id, format=None):
        checkpoint = get_object_or_404(TechnologyCheckpoint, pk=checkpoint_id)
        project = checkpoint.project
        # 完成自动部署任务时 部署服务器信息为必填
        if checkpoint.name == '开发测试环境部署' and request.data.get('status') == "done":
            deployment_servers = request.data.get('deployment_servers')
            # if deployment_servers:
            #     return api_bad_request(message="部署服务器信息为必填")

            if deployment_servers:
                origin_project = deepcopy(project)
                project.deployment_servers = json.dumps(request.data.get('deployment_servers'), ensure_ascii=False)
                project.save()
                Log.build_update_object_log(request.user, origin_project, project)

        origin = deepcopy(checkpoint)

        if 'quip_document_ids' in request.data:
            if request.data['quip_document_ids']:
                request.data['quip_document_ids'] = json.dumps(request.data['quip_document_ids'], ensure_ascii=False)
        if checkpoint.name == TechnologyCheckpoint.DEV_DOCS_CHECKPOINT:
            request.data.pop('status', None)
        serializer = TechnologyCheckpointEditSerializer(checkpoint, data=request.data, partial=True)
        if serializer.is_valid():
            checkpoint = serializer.save()
            Log.build_update_object_log(request.user, origin, checkpoint)
            return api_success(data=TechnologyCheckpointSerializer(checkpoint).data)
        return api_bad_request(message=serializer.errors)


def update_cache_of_need_update_gantt_template_projects(project, new_schedule_data, origin_schedule_data):
    gantt_chart = ProjectGanttChart.objects.filter(project_id=project.id)
    if not gantt_chart.exists() or gantt_chart.first().template_init_status == 'uninitialized':
        return
    # 判断是否需要提示根据新的日程表一键更新甘特图模板
    # 上次一键更新甘特图模板时的日程表数据
    origin_projects_schedules_for_gantt = cache.get('origin_projects_schedules_for_gantt', {})
    old_schedule_data = origin_projects_schedules_for_gantt.get(project.id, None)

    if not old_schedule_data:
        old_schedule_data = origin_schedule_data
        origin_projects_schedules_for_gantt[project.id] = old_schedule_data
        cache.set('origin_projects_schedules_for_gantt', origin_projects_schedules_for_gantt, None)

    need_update = old_schedule_data != new_schedule_data
    if need_update:
        need_update_gantt_template_projects = cache.get('need_update_gantt_template_projects', set())
        need_update_gantt_template_projects.add(project.id)
        cache.set('need_update_gantt_template_projects', need_update_gantt_template_projects, None)
    else:
        remove_project_need_update_gantt_template_cache_data(project)


@api_view(['GET'])
def ongoing_projects_schedules(request):
    params = request.GET
    projects = Project.ongoing_projects()

    group_bys = {'manager', 'product_manager', 'tpm', 'designer', 'test'}
    group_by = params.get('group_by', 'manager')
    if group_by not in group_bys:
        return api_bad_request("分组可用字段：".format(','.join(group_bys)))

    project_group_dict = {}
    role_null_data = {'user': None, 'projects': []}

    start_dates = set(projects.values_list('start_date', flat=True))
    end_dates = set(projects.values_list('end_date', flat=True))
    min_start_date = min(start_dates).strftime(settings.DATE_FORMAT) if start_dates else None
    max_end_date = max(end_dates).strftime(settings.DATE_FORMAT) if end_dates else None

    projects_data = ProjectWithScheduleSerializer(projects, many=True).data
    group_by_test = group_by == 'test'
    for project_data in projects_data:
        if group_by_test:
            tests = project_data['members_dict'].get("tests", None)
            if not tests:
                role_null_data['projects'].append(project_data)
                continue
            for test in tests:
                group_role_username = test['username']
                if group_role_username not in project_group_dict:
                    project_group_dict[group_role_username] = {'user': test, 'projects': []}
                project_group_dict[group_role_username]['projects'].append(project_data)
        else:
            group_role = project_data['members_dict'].get(group_by, None)
            if not group_role:
                role_null_data['projects'].append(project_data)
                continue
            group_role_username = group_role['username']
            if group_role_username not in project_group_dict:
                project_group_dict[group_role_username] = {'user': group_role, 'projects': []}
            project_group_dict[group_role_username]['projects'].append(project_data)
    result_data = {
        'start_date': min_start_date,
        'end_date': max_end_date,
        'group_projects': []
    }
    sorted_username = sorted(project_group_dict.keys(), key=lambda x: ''.join(lazy_pinyin(x)))
    for username in sorted_username:
        data = deepcopy(project_group_dict[username])
        data['projects'] = sorted(data['projects'], key=lambda x: (x['start_date'], x['created_at']))
        result_data['group_projects'].append(data)

    if role_null_data['projects']:
        data = deepcopy(role_null_data)
        data['projects'] = sorted(data['projects'], key=lambda x: (x['start_date'], x['created_at']))
        result_data['group_projects'].append(data)
    return api_success(result_data)


@api_view(['GET'])
@func_perm_required('track_project_development')
def projects_manage_filter_data(request):
    projects = Project.ongoing_projects()
    manager_ids = set(projects.values_list('manager_id', flat=True))
    managers = User.objects.filter(id__in=manager_ids).order_by('-is_active', 'date_joined')
    managers_data = UserFilterSerializer(managers, many=True).data
    return api_success(data={"managers": managers_data})


@api_view(['GET'])
@func_perm_required('track_project_development')
@cache_page(60 * 10)
def projects_manage_ongoing_projects(request):
    projects = Project.ongoing_projects().order_by('-created_at')
    params = request.GET
    managers = re.sub(r'[;；,，]', ' ', params.get('managers', '')).split()
    if managers:
        projects = projects.filter(manager_id__in=managers)
    order_by = params.get('order_by', 'created_at')
    order_dir = params.get('order_dir', 'asc')
    if not order_by:
        order_by = 'created_at'
        order_dir = 'asc'
    if order_dir == 'desc':
        order_by = '-' + order_by
    projects = projects.order_by(order_by)
    return build_pagination_response(request, projects, ProjectsManageSerializer)


@api_view(['GET'])
@request_params_required('tpm')
def projects_tpm_checkpoints(request):
    rebuild_ongoing_projects_dev_docs_checkpoints_status()

    tpm_id = request.GET.get('tpm', None)
    # this_week = request.GET.get('this_week', None) in ['1', 'True', 'true', True, 1]

    tpm = get_object_or_404(User, pk=tpm_id)
    checkpoints = TechnologyCheckpoint.objects.filter(project__tpm_id=tpm.id)
    # 只展示进行中项目的未完成检查点
    pending_checkpoints = checkpoints.filter(status='pending', project__done_at__isnull=True).order_by("expected_at")

    after_seven_days = timezone.now().date() + timedelta(days=7)
    # if this_week:
    pending_checkpoints = pending_checkpoints.filter(expected_at__lte=after_seven_days)
    recent_done_checkpoints = checkpoints.exclude(status='pending').filter(
        done_at__gte=timezone.now() + timedelta(days=-14)).order_by("-done_at")

    tpm_checkpoints = []
    tpm_checkpoints.extend(list(pending_checkpoints))
    tpm_checkpoints.extend(list(recent_done_checkpoints))

    tpm_checkpoints_data = TechnologyCheckpointSerializer(tpm_checkpoints, many=True).data

    total = len(tpm_checkpoints)
    tpm_checkpoint_dict = {}
    for checkpoint in tpm_checkpoints_data:
        name = checkpoint['name']
        if name not in tpm_checkpoint_dict:
            tpm_checkpoint_dict[name] = []
        tpm_checkpoint_dict[name].append(checkpoint)
        total += 1

    checkpoints_data = []
    for name in TECHNOLOGY_CHECKPOINT_NAME_LIST:
        group_data = {'name': name, 'checkpoints': tpm_checkpoint_dict.get(name, [])}
        checkpoints_data.append(group_data)

    return api_success(data={"total": total, "checkpoint_groups": checkpoints_data})


@api_view(['GET'])
def my_tpm_checkpoints(request):
    rebuild_ongoing_projects_dev_docs_checkpoints_status()

    # this_week = request.GET.get('this_week', None) in ['1', 'True', 'true', True, 1]
    tpm = request.user
    checkpoints = TechnologyCheckpoint.objects.filter(project__tpm_id=tpm.id)
    pending_checkpoints = checkpoints.filter(status='pending', project__done_at__isnull=True).order_by("expected_at")

    after_seven_days = timezone.now().date() + timedelta(days=7)
    # if this_week:
    pending_checkpoints = pending_checkpoints.filter(expected_at__lte=after_seven_days)
    recent_done_checkpoints = checkpoints.exclude(status='pending').filter(
        done_at__gte=timezone.now() + timedelta(days=-14)).order_by("-done_at")

    tpm_checkpoints = []
    tpm_checkpoints.extend(list(pending_checkpoints))
    tpm_checkpoints.extend(list(recent_done_checkpoints))

    tpm_checkpoints_data = TechnologyCheckpointSerializer(tpm_checkpoints, many=True).data

    total = len(tpm_checkpoints)
    tpm_checkpoint_dict = {}
    for checkpoint in tpm_checkpoints_data:
        name = checkpoint['name']
        if name not in tpm_checkpoint_dict:
            tpm_checkpoint_dict[name] = []
        tpm_checkpoint_dict[name].append(checkpoint)
        total += 1

    checkpoints_data = []
    for name in TECHNOLOGY_CHECKPOINT_NAME_LIST:
        group_data = {'name': name, 'checkpoints': tpm_checkpoint_dict.get(name, [])}
        checkpoints_data.append(group_data)

    return api_success(data={"total": total, "checkpoint_groups": checkpoints_data})


class ProjectDeliveryDocumentList(APIView):
    def get(self, request, project_id, format=None):
        project = get_object_or_404(Project, pk=project_id)
        result_data = {
            "compress_zip": None,
            "delivery_documents": {},
            "other_documents": [],
        }
        for document_type_data in DeliveryDocumentType.INIT_DATA:
            type_name = document_type_data['name']
            if type_name == '交付文档':
                result_data['compress_zip'] = {
                    "document_type": document_type_data,
                    "document": None
                }
            elif type_name != '其他文档':
                result_data['delivery_documents'][type_name] = {
                    "document_type": document_type_data,
                    "document": None
                }
        delivery_documents = project.delivery_documents.filter(is_deleted=False)
        documents_data = DeliveryDocumentSerializer(delivery_documents, many=True).data
        has_operation_permission = has_function_perm(request.user,
                                                     'manage_my_project_delivery_documents') and request.user in project.members
        for document in documents_data:
            type_name = document['document_type']['name']
            if type_name == '交付文档':
                result_data['compress_zip']['document'] = document
            elif type_name == '其他文档':
                new_document = {
                    "document_type": {'name': '其他文档', 'suffix': '', 'number': 13},
                    "document": deepcopy(document)
                }
                result_data['other_documents'].append(new_document)
            elif type_name in result_data['delivery_documents']:
                result_data['delivery_documents'][type_name]['document'] = document
        result_data['delivery_documents'] = sorted(result_data['delivery_documents'].values(),
                                                   key=lambda x: x['document_type']['number'])
        result_data['has_operation_permission'] = has_operation_permission
        return api_success(result_data)

    def post(self, request, project_id, format=None):
        project = get_object_or_404(Project, pk=project_id)
        document_type_name = request.data.get('document_type_name', None)
        if not document_type_name:
            return Response({"result": False, "message": {"document_type_name": ["参数中没有提交文档类型名称。"]}})
        document_type = get_object_or_404(DeliveryDocumentType, name=document_type_name)
        if document_type.number == DeliveryDocumentType.DELIVERY_DOCUMENT_NUMBER:
            return api_bad_request("最终交付文档需要Farm压缩生成")
        request.data['uid'] = gen_uuid()
        request.data['project'] = project.id
        request.data['document_type'] = document_type.id

        serializer = DeliveryDocumentSerializer(data=request.data)
        if serializer.is_valid():
            file = request.data["file"]
            if document_type.suffix and not file.name.endswith('.' + document_type.suffix):
                message = "{document_type_name}上传失败 请上传{suffix}格式的文件".format(document_type_name=document_type.name,
                                                                             suffix=document_type.suffix)
                return api_bad_request(message)
            if document_type.number == DeliveryDocumentType.UNCLASSIFIED_DOCUMENT_NUMBER:
                documents = project.delivery_documents.filter(is_deleted=False, filename=file.name,
                                                              document_type__number=DeliveryDocumentType.UNCLASSIFIED_DOCUMENT_NUMBER)
                if documents.exists():
                    return Response({"result": False, "message": "已存在名字为:{} 的{}".format(file.name, document_type.name)})
            delivery_document = serializer.save()
            delivery_document.filename = file.name
            delivery_document.save()
            Log.build_create_object_log(request.user, delivery_document, related_object=project)
            if document_type.number != DeliveryDocumentType.UNCLASSIFIED_DOCUMENT_NUMBER:
                project.delivery_documents.filter(document_type__number=document_type.number).exclude(
                    pk=delivery_document.id).delete()
            serializer = DeliveryDocumentSerializer(delivery_document)
            project.delivery_documents.filter(
                document_type__number=DeliveryDocumentType.DELIVERY_DOCUMENT_NUMBER).update(is_behind=True)
            return Response(serializer.data)
        return api_bad_request(message=serializer.errors)


class DeliveryDocumentTypeList(APIView):
    def get(self, request, format=None):
        types = DeliveryDocumentType.objects.all()
        data = DeliveryDocumentTypeSerializer(types, many=True).data
        return Response(data)


class DeliveryDocumentList(APIView):
    def get(self, request, project_id, format=None):
        project = get_object_or_404(Project, pk=project_id)
        delivery_documents = project.delivery_documents.filter(is_deleted=False)
        document_data = DeliveryDocumentSerializer(delivery_documents, many=True).data
        has_operation_permission = has_function_perm(request.user,
                                                     'manage_my_project_delivery_documents') and request.user in project.members
        data = {"document_data": document_data, 'has_operation_permission': has_operation_permission}
        return api_success(data)

    def post(self, request, project_id, format=None):
        project = get_object_or_404(Project, pk=project_id)
        document_type_number = request.data.get('document_type_number', None)
        if document_type_number == None:
            return Response({"result": False, "message": {"document_type_number": ["参数中没有提交文档类型编号。"]}})
        document_type = get_object_or_404(DeliveryDocumentType, number=document_type_number)

        request.data['uid'] = gen_uuid()
        request.data['project'] = project.id
        request.data['document_type'] = document_type.id
        serializer = DeliveryDocumentSerializer(data=request.data)
        if serializer.is_valid():
            file = request.data["file"]
            if document_type.suffix and not file.name.endswith('.' + document_type.suffix):
                message = "{document_type_name}上传失败 请上传{suffix}格式的文件".format(document_type_name=document_type.name,
                                                                             suffix=document_type.suffix)
                return Response({"result": False, "message": message})
            if document_type.number == DeliveryDocumentType.UNCLASSIFIED_DOCUMENT_NUMBER:
                documents = project.delivery_documents.filter(is_deleted=False, filename=file.name,
                                                              document_type__number=DeliveryDocumentType.UNCLASSIFIED_DOCUMENT_NUMBER)
                if documents.exists():
                    return Response({"result": False, "message": "已存在名字为:{filename} 的未分类文档".format(filename=file.name)})
            delivery_document = serializer.save()
            delivery_document.filename = file.name
            delivery_document.save()
            Log.build_create_object_log(request.user, delivery_document, related_object=project)
            if document_type.number != DeliveryDocumentType.UNCLASSIFIED_DOCUMENT_NUMBER:
                project.delivery_documents.filter(document_type__number=document_type.number).exclude(
                    pk=delivery_document.id).delete()
            if request.data.get("document_id", None):
                project.delivery_documents.filter(pk=request.data['document_id']).delete()

            serializer = DeliveryDocumentSerializer(delivery_document)
            message = "项目:{project_name} {document_type_name}上传成功".format(project_name=project.name,
                                                                          document_type_name=document_type.name)
            project.delivery_documents.filter(
                document_type__number=DeliveryDocumentType.DELIVERY_DOCUMENT_NUMBER).update(is_behind=True)

            result_data = {"result": True, "message": message, "document_data": serializer.data,
                           "document_number": request.data['document_number']}

            return api_success(result_data)
        return api_bad_request(serializer.errors)


class DeliveryDocumentDetail(APIView):
    def get(self, request, project_id, document_id):
        project = get_object_or_404(Project, pk=project_id)
        delivery_document = get_object_or_404(DeliveryDocument, pk=document_id, project=project)
        serializer = DeliveryDocumentSerializer(delivery_document)
        return Response(serializer.data)

    def delete(self, request, project_id, document_id):
        project = get_object_or_404(Project, pk=project_id)
        is_mine = has_function_perm(request.user,
                                    'manage_my_project_delivery_documents') and request.user in project.members
        has_perm = is_mine or has_function_perm(request.user, 'manage_all_project_delivery_documents')
        if not has_perm:
            return Response({"result": False, "message": "你没有权限删除该项目文档，只有负责项目的项目经理、导师与管理员有权限删除"})
        delivery_document = get_object_or_404(DeliveryDocument, pk=document_id)
        origin = deepcopy(delivery_document)
        delivery_document.delete()
        Log.build_delete_object_log(request.user, origin, related_object=project)
        project.delivery_documents.filter(document_type__number=DeliveryDocumentType.DELIVERY_DOCUMENT_NUMBER).update(
            is_behind=True)
        return Response({"result": True})


@api_view(['POST'])
def compress_documents(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    # 压缩文件
    documents = project.delivery_documents.filter(is_deleted=False).exclude(
        document_type__number=DeliveryDocumentType.DELIVERY_DOCUMENT_NUMBER)
    if not documents.exists():
        return Response({"result": False, "message": "该项目没有可压缩交付文件"})
    if not documents.filter(document_type__number=DeliveryDocumentType.DELIVERY_DOCUMENT_README_NUMBER).exists():
        return Response({"result": False, "message": "该项目缺失交付文档说明 请上传后再生成交付文档"})
    if settings.DEVELOPMENT:
        create_project_delivery_documents(project_id, request.user.id)
    else:
        create_project_delivery_documents.delay(project_id, request.user.id)
    return api_success(message="正在后台压缩 请等待或操作其他页面")


@api_view(['GET'])
def download_delivery_document(request, uid):
    document = DeliveryDocument.objects.filter(uid=uid, is_deleted=False).first()
    if not document:
        return api_not_found("文档不存在")
    wrapper = FileWrapper(document.file.file)
    response = FileResponse(wrapper, content_type='application/{}'.format(document.document_type.suffix))
    response['Content-Disposition'] = "attachment; filename*=utf-8''{}".format(escape_uri_path(document.filename))
    response['Access-Control-Expose-Headers'] = 'Content-Disposition'
    return response


@api_view(['POST', "GET"])
def download_document_zip(request, uid):
    document = DeliveryDocument.objects.filter(uid=uid, is_deleted=False, document_type__name="交付文档").first()
    if not document:
        return api_bad_request("链接失效，您所下载的交付文档不存在或已更新至最新链接")
    if request.method == 'POST':
        cipher = request.data.get("cipher", None)
    else:
        cipher = request.GET.get("cipher", None)
    if cipher != document.cipher:
        return api_bad_request("请输入正确密码")
    wrapper = FileWrapper(document.file.file)
    response = FileResponse(wrapper, content_type='application/{}'.format(document.document_type.suffix))
    response['Content-Disposition'] = "attachment; filename*=utf-8''{}".format(escape_uri_path(document.filename))
    response['Access-Control-Expose-Headers'] = 'Content-Disposition'
    return response


class ALLProjectWithContract(APIView):
    def get(self, request):
        project_status = request.GET.get('project_status', None)
        search_value = request.GET.get('search_value', None)
        page = request.GET.get('page', None)
        page_size = request.GET.get('page_size', None)
        projects = Project.objects.all()
        if project_status == 'ongoing':
            projects = Project.ongoing_projects()
        elif project_status == 'closed':
            projects = Project.completion_projects()

        projects = projects.filter(contracts__isnull=False).distinct().order_by('-created_at')
        if search_value:
            projects = projects.filter(
                Q(name__icontains=search_value) | Q(manager__username__icontains=search_value))
        return build_pagination_response(request, projects, ProjectWithContractSerializer)


class ProjectContractList(APIView):
    def get(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        serializer = ProjectWithContractSerializer(project)
        return Response({"result": True, 'data': serializer.data})

    def post(self, request, project_id):
        username = request.user.username
        user_id = request.user.id
        project = get_object_or_404(Project, pk=project_id)
        request.data["project"] = project.id
        file = request.data.get('file', None)
        serializer = ProjectContractSerializer(data=request.data)
        if serializer.is_valid():
            contract = serializer.save()
            if file:
                contract.filename = file.name
                contract.save()
            Log.build_create_object_log(request.user, contract, contract.project)
            content = '{username}为【{project}】新添加了一个合同文件'.format(project=contract.project,
                                                                username=username)
            url = get_protocol_host(request) + build_page_path("project_view", kwargs={"id": project.id})
            mentor_id = contract.project.mentor_id
            manager_id = contract.project.manager_id
            if mentor_id and user_id != mentor_id:
                create_notification(contract.project.mentor, content, url)
            if manager_id and manager_id != mentor_id and manager_id != user_id:
                create_notification(contract.project.manager, content, url)
            return Response({"result": True, 'data': serializer.data})
        return Response({"result": False, 'data': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class ProjectContractDetail(APIView):
    def get(self, request, contract_id):
        contract = get_object_or_404(ProjectContract, pk=contract_id)
        serializer = ProjectContractSerializer(contract)
        return Response({"result": True, 'data': serializer.data})

    def post(self, request, contract_id):
        username = request.user.username
        user_id = request.user.id
        contract = get_object_or_404(ProjectContract, pk=contract_id)
        project = contract.project
        origin = deepcopy(contract)
        request.data['project'] = contract.project.id
        if 'file' in request.data and request.data['file'] == None:
            request.data.pop('file')
            contract.file = None
            contract.filename = None
            contract.save()
        serializer = ProjectContractSerializer(contract, data=request.data)
        if serializer.is_valid():
            contract = serializer.save()
            file = request.data.get('file', None)
            if file:
                contract.filename = file.name
                contract.save()
                content = '{username}为【{project}】新添加了一个合同文件'.format(project=contract.project,
                                                                    username=username)
                url = get_protocol_host(request) + build_page_path("project_view", kwargs={"id": project.id})
                mentor_id = contract.project.mentor_id
                manager_id = contract.project.manager_id
                if mentor_id and user_id != mentor_id:
                    create_notification(contract.project.mentor, content, url)
                if manager_id and manager_id != mentor_id and manager_id != user_id:
                    create_notification(contract.project.manager, content, url)
            Log.build_update_object_log(request.user, origin, contract)
            return Response({"result": True, 'data': serializer.data})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, contract_id):
        contract = get_object_or_404(ProjectContract, pk=contract_id)
        project = contract.project
        origin = deepcopy(contract)
        contract.delete()
        Log.build_delete_object_log(request.user, origin, related_object=project)
        return Response({"result": True})


@api_view(['GET'])
def project_last_prototype(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    prototype = project.prototypes.filter(is_deleted=False).order_by('-created_at').first()
    if prototype:
        data = ProjectPrototypeSerializer(prototype).data
        return api_success(data)
    return api_not_found()


class ProjectPrototypeList(APIView):
    def get(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        prototypes = project.prototypes.filter(is_deleted=False).order_by('-created_at', 'title')
        return build_pagination_response(request, prototypes, ProjectPrototypeSerializer)

    @transaction.atomic
    def post(self, request, project_id):
        username = request.user.username
        file = request.data.get('file')
        if not file:
            return api_bad_request("请上传文件")
        if not (file.name and file.name.endswith('.zip')):
            return api_bad_request('上传文件类型错误,只支持.zip压缩包')

        request_data = request.data
        project = get_object_or_404(Project, pk=project_id)
        request_data['uid'] = gen_uuid()
        request_data['project'] = project.id
        request_data['cipher'] = gen_uuid()[:6]
        request_data['submitter'] = request.user.id
        filename = request_data.get('filename', '')
        title = request_data.get('title', None)
        version = request.data.get('version', None)
        comment = request_data.get('remarks', '')
        if not filename:
            request_data['filename'] = file.name
        if not title:
            request_data['title'] = re.sub(r'[~#^/=$@%&?？]', ' ', file.name.split('.zip')[0])
        if not version:
            version_set = set(project.prototypes.values_list('version', flat=True))
            if version_set:
                new_version_set = [float(version) for version in version_set if version.replace('.', '').isdigit()]
                request_data['version'] = str(round(max(new_version_set) + 0.1, 1))
        savepoint = transaction.savepoint()
        serializer = ProjectPrototypeSerializer(data=request_data)
        if serializer.is_valid():
            try:
                prototype = serializer.save()
                Log.build_create_object_log(request.user, prototype, project, comment=comment)
                if comment:
                    Comment.objects.create(author=request.user, content=comment, content_object=prototype)
                if not prototype.is_deleted:
                    unzip_prototype_and_upload_to_oss(prototype.id)
            except Exception as e:
                transaction.savepoint_rollback(savepoint)
                logger.error(e)
                return api_error("初始化过程出错 请联系管理员")

            if not project.current_stages.filter(stage_type__in=['prd', 'completion']).exists():
                content = '{username}为【{project}】添加了一个原型文件'.format(project=project, username=username)
                url = prototype.prototype_url
                notification_users = set(project.members)
                for notification_user in notification_users:
                    if notification_user and notification_user != request.user:
                        create_notification(notification_user, content, url)
            return api_success(serializer.data)
        return api_bad_request(serializer.errors)


class ProjectPrototypeDetail(APIView):
    def get(self, request, prototype_id):
        prototype = get_object_or_404(ProjectPrototype, pk=prototype_id)
        serializer = ProjectPrototypeDetailSerializer(prototype)
        return Response({"result": True, 'data': serializer.data})

    def post(self, request, prototype_id):
        prototype = get_object_or_404(ProjectPrototype, pk=prototype_id)
        origin = deepcopy(prototype)
        request_data = deepcopy(request.data)
        title = request_data.get('title', None)
        version = request_data.get('version', None)
        if not all([title, version]):
            return Response({"result": False, "message": "请填写原型名称、版本"})
        if prototype.project.prototypes.filter(title=title, version=version, is_deleted=False).exclude(
                pk=prototype.id).exists():
            return Response({"result": False, "message": "该项目存在相同名字、版本的原型文件"})

        request_data['title'] = re.sub(r'[~#^/=$@%&?？]', ' ', title)
        comment = request_data.get('comment', '')
        serializer = ProjectPrototypeDetailSerializer(prototype, data=request_data)
        if serializer.is_valid():
            prototype = serializer.save()
            if comment:
                Comment.objects.create(author=request.user, content=comment, content_object=prototype)
            return Response({"result": True, 'data': serializer.data})
        return Response({"result": False, "message": str(serializer.errors)})

    def delete(self, request, prototype_id):
        return api_bad_request('暂不开放删除功能')
        prototype = get_object_or_404(ProjectPrototype, pk=prototype_id)
        project = prototype.project
        origin = deepcopy(prototype)
        prototype.delete()
        Log.build_delete_object_log(request.user, origin, related_object=project)
        return Response({"result": True})


class PrototypeCommentPointList(APIView):
    def get(self, request, uid):
        prototype = get_object_or_404(ProjectPrototype, uid=uid)

        # 客户只能看到客户的评论点、 开发者看不到客户的评论点、内部员工可以看到所有评论点
        if request.top_user and request.top_user.is_client:
            statistical_data = cache.get('prototype-{}-client-comments'.format(prototype.uid))
            if not statistical_data:
                create_prototype_client_comment_point_cache_data(prototype.id)
                statistical_data = cache.get('prototype-{}-client-comments'.format(prototype.uid))
        elif request.top_user and request.top_user.is_developer:
            statistical_data = cache.get('prototype-{}-developer-comments'.format(prototype.uid))
            if not statistical_data:
                create_prototype_developer_comment_point_cache_data(prototype.id)
                statistical_data = cache.get('prototype-{}-developer-comments'.format(prototype.uid))
        else:
            statistical_data = cache.get('prototype-{}-comments'.format(prototype.uid))
            if not statistical_data:
                create_prototype_comment_point_cache_data(prototype.id)
                statistical_data = cache.get('prototype-{}-comments'.format(prototype.uid))

        return Response({"result": True, 'data': statistical_data})

    def post(self, request, uid):
        prototype = get_object_or_404(ProjectPrototype, uid=uid)
        request_data = deepcopy(request.data)
        request_data['prototype'] = prototype.id
        if not all([request_data.get('comment_content'), request_data.get('page_name')]):
            return Response({"result": False, "message": "缺少评论内容或页面信息"})
        if request_data.get('url_hash'):
            request_data['url_hash'] = urllib.parse.unquote(request_data['url_hash'])
        request_data['page_name'] = urllib.parse.unquote(request_data['page_name'])
        request_data['position_left'] = int(request_data['position_left'])
        request_data['position_top'] = int(request_data['position_top'])

        if request.top_user:
            request_data['creator'] = request.top_user.id
        top_user = request.top_user

        serializer = PrototypeCommentPointSerializer(data=request_data)
        if serializer.is_valid():
            comment_point = serializer.save()
            comment = Comment(content_object=comment_point, content=request.data['comment_content'],
                              creator=top_user)
            if top_user.is_employee:
                comment.author = top_user.user
            elif top_user.is_developer:
                comment.developer = top_user.developer
            comment.save()
            return Response({"result": True, 'data': serializer.data})
        return Response({"result": False, "message": str(serializer.errors)})


class PrototypeCommentPointDetail(APIView):
    def get(self, request, id):
        comment_point = PrototypeCommentPoint.objects.filter(pk=id)
        if comment_point.exists():
            serializer = PrototypeCommentPointWithCommentsSerializer(comment_point.first())
            return Response({"result": True, 'data': serializer.data})
        else:
            return Response({"result": False, 'message': '评论点不存在', 'is_exist': False})

    def post(self, request, id):
        comment_point = get_object_or_404(PrototypeCommentPoint, pk=id)
        if not request.data.get('comment_content', None):
            return Response({"result": False, "message": "缺少评论内容"})
        top_user = request.top_user
        comment = Comment(content_object=comment_point, content=request.data['comment_content'],
                          creator=top_user)
        if top_user.is_employee:
            comment.author = top_user.user
        elif top_user.is_developer:
            comment.developer = top_user.developer
        comment.save()
        serializer = PrototypeCommentPointWithCommentsSerializer(comment_point)
        return Response({"result": True, 'data': serializer.data})

    def delete(self, request, id):
        comment_point = get_object_or_404(PrototypeCommentPoint, pk=id)
        if comment_point.comments.exists():
            return api_bad_request("存在评论 不允许删除")
        prototype = comment_point.prototype
        origin = deepcopy(comment_point)
        comment_point.delete()
        Log.build_delete_object_log(request.user, origin, related_object=prototype)
        return Response({"result": True})


@api_view(['GET'])
def project_last_email_record(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    email_record = project.email_records.filter(status='1').order_by('-created_at').first()
    if email_record:
        data = {'to': email_record.to, 'cc': email_record.cc}
        return api_success(data)
    return api_success()


@api_view(['GET'])
def project_quip_tpm_docs(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    quip_projects_tpm_docs = cache.get('quip_projects_tpm_docs', {})
    tpm_docs = quip_projects_tpm_docs.get(project.id, {})
    if not tpm_docs:
        crawl_project_tpm_folder_docs(project_id, rebuild=True)
    else:
        crawl_project_tpm_folder_docs.delay(project_id)

    quip_projects_tpm_docs = cache.get('quip_projects_tpm_docs', {})
    tpm_docs = quip_projects_tpm_docs.get(project_id, {})
    docs = tpm_docs.get('docs', [])
    return api_success(data=docs)


@api_view(['GET'])
def prototypes_with_browsing_histories(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    prototypes = project.prototypes.filter(browsing_histories__isnull=False).distinct()
    order_prototypes = sorted(prototypes, key=lambda prototype: prototype.last_browsing_history.created_at,
                              reverse=True)
    return build_pagination_response(request, order_prototypes, ProjectPrototypeWithBrowsingHistorySerializer)


@api_view(['POST'])
def current_page_comment_points(request):
    if 'pro_uid' not in request.data:
        return Response({"result": False, "message": '缺少原型uid参数'})
    if request.data.get('page_name'):
        prototype = get_object_or_404(ProjectPrototype, uid=request.data['pro_uid'])
        page_name = urllib.parse.unquote(request.data['page_name'])
        comment_points = prototype.comment_points.filter(page_name=page_name, comments__isnull=False).distinct()
        if request.top_user and request.top_user.is_client:
            comment_points = comment_points.filter(creator__client_id__isnull=False)
        elif request.top_user and request.top_user.is_developer:
            comment_points = comment_points.exclude(creator__client_id__isnull=False)

        serializer = PrototypeCommentPointWithCommentsSerializer(comment_points, many=True)
        return Response({"result": True, 'data': serializer.data})
    else:
        return Response({"result": True, 'data': []})


@api_view(['GET'])
def current_prototype_all_comment_points(request, uid):
    prototype = get_object_or_404(ProjectPrototype, uid=uid)

    comment_points = prototype.comment_points.filter(comments__isnull=False).distinct()
    if request.top_user and request.top_user.is_client:
        comment_points = comment_points.filter(creator__client_id__isnull=False)
    elif request.top_user and request.top_user.is_developer:
        comment_points = comment_points.exclude(creator__client_id__isnull=False)

    serializer = PrototypeCommentPointWithCommentsSerializer(comment_points, many=True)
    return Response({"result": True, 'data': serializer.data})


def get_user_by_authorization(request):
    token_key = None
    top_user = None
    token_authentication = TokenAuthentication()
    try:
        token_key = token_authentication.authenticate_key(request)
    except:
        pass
    if token_key:
        # 临时登录 ONE_TIME_AUTH 找到真实的Token
        if token_key.startswith(settings.ONE_TIME_AUTH_PREFIX):
            # real_token_data = {"token": real_token.key, 'user_type': real_token.user_type, 'editable': False}
            real_token_data = cache.get(token_key)
            if real_token_data:
                token_key = real_token_data['token']
        try:
            token = TopToken.objects.filter(key=token_key).first()
            if token:
                auth = token.top_user
                if auth.is_active:
                    top_user = auth
        except Exception as e:
            pass
    return top_user


@api_view(['GET'])
def prototype_content_type(request, uid):
    prototype = get_object_or_404(ProjectPrototype, uid=uid)
    serializer = ProjectPrototypeContentTypeSerializer(prototype)
    return api_success(data=serializer.data)


@api_view(['GET'])
def prototype_access_data(request, uid):
    prototype = get_object_or_404(ProjectPrototype, uid=uid)
    prototype_token = request.GET.get('access_token', None)
    has_cipher = prototype_token == prototype.access_token
    is_logged = False
    if request.top_user:
        is_logged = True
    return api_success({'is_logged': is_logged, 'has_cipher': has_cipher, 'uid': uid})


@api_view(['GET'])
@request_params_required('cipher')
def prototype_access_token(request, uid):
    prototype = get_object_or_404(ProjectPrototype, uid=uid)
    cipher = request.GET.get('cipher')
    if cipher != prototype.cipher:
        return api_bad_request("密码错误")
    prototype_token = prototype.access_token
    return api_success({"access_token": prototype_token})


@api_view(['POST'])
def reset_prototype_cipher(request, prototype_id):
    prototype = get_object_or_404(ProjectPrototype, pk=prototype_id)
    prototype.cipher = gen_uuid()[:6]
    origin = deepcopy(prototype)
    prototype.save()
    Log.build_update_object_log(request.user, origin, prototype, prototype.project)
    return api_success()


class PrototypePublicStatus(APIView):
    def get(self, request, prototype_id):
        prototype = get_object_or_404(ProjectPrototype, pk=prototype_id)
        data = {"id": prototype.id, "public_status": prototype.public_status,
                "public_status_display": prototype.public_status}
        return api_success(data)

    def patch(self, request, prototype_id):
        prototype = get_object_or_404(ProjectPrototype, pk=prototype_id)
        public_status = request.data.get('public_status', None)
        if not public_status:
            return api_bad_request("公开状态字段必填")
        if public_status != prototype.public_status:
            prototype.public_status = public_status
            prototype.save()
            if prototype.public_status in ['developer_public', 'public']:
                project = prototype.project
                content = '{username}为【{project}】添加了一个原型文件'.format(username=request.user.username, project=project.name)
                url = prototype.prototype_url
                developers = set(project.get_active_developers())
                for developer in developers:
                    create_developer_notification(developer, content, url=url)
        data = {"id": prototype.id, "public_status": prototype.public_status,
                "public_status_display": prototype.public_status}
        return api_success(data)


@api_view(['POST'])
def reset_calendar_public_status(request, uid):
    calendar = get_object_or_404(ClientCalendar, uid=uid)
    calendar.is_public = not calendar.is_public
    calendar.save()
    return api_success()


class ProjectGanttDetail(APIView):
    def get(self, request, project_id=None, uid=None):
        project_gantt = None
        if project_id:
            get_object_or_404(Project, pk=project_id)
            project_gantt = get_object_or_404(ProjectGanttChart, project_id=project_id)
        if uid:
            project_gantt = get_object_or_404(ProjectGanttChart, uid=uid)
        if not project_gantt:
            return Response({'result': False, 'message': "需要参数gantt_chart_id或uid"})

        data = ProjectGanttChartRetrieveSerializer(project_gantt).data
        last_week_data = cache.get('gantt-{}-data'.format(project_gantt.id))
        if request.GET.get('diff_last_week') and last_week_data:
            last_start_time = last_week_data.get('start_time')
            if last_start_time and data['start_time']:
                if isinstance(last_start_time, str):
                    last_start_time = datetime.strptime(last_start_time, settings.DATE_FORMAT).date()
                if last_start_time < data['start_time']:
                    data['start_time'] = last_start_time

            last_finish_time = last_week_data.get('finish_time')
            if last_finish_time and data['finish_time']:
                if isinstance(last_finish_time, str):
                    last_finish_time = datetime.strptime(last_finish_time, settings.DATE_FORMAT).date()
                if last_finish_time > data['finish_time']:
                    data['finish_time'] = last_finish_time
        return Response({'result': True, 'data': data})

    def post(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        if not ProjectGanttChart.objects.filter(project_id=project_id).exists():
            project_gantt = ProjectGanttChart.objects.create(project=project)
            if project.manager_id and User.objects.filter(pk=project.manager_id).exists():
                GanttRole.objects.create(gantt_chart=project_gantt, name='产品-' + project.manager.username,
                                         role_type='pm', user=project.manager)
            data = ProjectGanttChartRetrieveSerializer(project_gantt).data
            return Response({'result': True, 'data': data})
        else:
            return Response({'result': False, 'message': '项目已经生成甘特图'})


@api_view(['POST'])
@transaction.atomic
def gantt_chart_init_template(request, gantt_chart_id):
    gantt_chart = get_object_or_404(ProjectGanttChart, pk=gantt_chart_id)
    origin = deepcopy(gantt_chart)
    project = gantt_chart.project
    if project.is_done or project.end_date <= timezone.now().date():
        return api_bad_request("项目已结束 ，不需要初始化甘特图模板")

    if request.user.id != project.manager_id:
        return Response({'result': False, 'message': '只有项目的项目经理可以导入甘特图模板'})
    if gantt_chart.template_init_status == 'initialized':
        return Response({'result': False, 'message': '项目已导入甘特图模板，不需要重新'})
    flag = request.data.get('flag')
    if flag not in ['init', 'skip']:
        return Response({'result': False, 'message': "flag参数必选，可选值为['init', 'skip']"})

    if flag == 'init':
        savepoint = transaction.savepoint()
        try:
            init_project_gantt_template(project)
        except Exception as e:
            transaction.savepoint_rollback(savepoint)
            logger.error(e)
            return Response({'result': False, 'message': "初始化过程出错 请联系管理员"})

        gantt_chart.template_init_status = 'initialized'
        gantt_chart.save()
        Log.build_update_object_log(request.user, origin, gantt_chart, comment="导入甘特图模板")
        Log.build_update_object_log(request.user, project, project, comment="导入甘特图模板")
        update_project_stages_cache_data(project)
    else:
        gantt_chart.template_init_status = 'skipped'
        gantt_chart.save()
    remove_project_need_update_gantt_template_cache_data(project)
    return Response({'result': True, 'data': None})


@api_view(['POST'])
@transaction.atomic
def gantt_chart_update_template(request, gantt_chart_id):
    gantt_chart = get_object_or_404(ProjectGanttChart, pk=gantt_chart_id)
    origin = deepcopy(gantt_chart)
    project = gantt_chart.project
    if project.is_done or project.end_date <= timezone.now().date():
        return api_bad_request("项目已结束 ，不需要初始化甘特图模板")
    if request.user.id != project.manager_id:
        return api_bad_request("只有项目的项目经理可以更新甘特图模板")
    if gantt_chart.template_init_status != 'initialized':
        return api_bad_request("项目未导入甘特图模板，不需要更新")
    flag = request.data.get('flag')
    if flag not in ['update', 'skip']:
        return Response({'result': False, 'message': "flag参数必选，可选值为['update', 'skip']"})

    if flag == 'update':
        if not gantt_chart.need_update_template:
            return api_bad_request("无需更新")
        savepoint = transaction.savepoint()
        try:
            update_project_gantt_template(project)
        except Exception as e:
            transaction.savepoint_rollback(savepoint)
            logger.error(e)
            return Response({'result': False, 'message': "更新过程出错 请联系管理员"})
        Log.build_update_object_log(request.user, origin, gantt_chart, comment="更新最新日程表更新甘特图模板")
        Log.build_update_object_log(request.user, project, project, comment="更新最新日程表更新甘特图模板")
    update_project_stages_cache_data(project)
    remove_project_need_update_gantt_template_cache_data(project)
    return Response({'result': True, 'data': None})


def update_project_stages_cache_data(project):
    origin_projects_schedules_for_gantt = cache.get('origin_projects_schedules_for_gantt', {})
    new_stage_data = {(stage.id, stage.start_date, stage.end_date) for stage in project.project_stages.all()}
    origin_projects_schedules_for_gantt[project.id] = new_stage_data
    cache.set('origin_projects_schedules_for_gantt', origin_projects_schedules_for_gantt, None)


def remove_project_need_update_gantt_template_cache_data(project):
    need_update_gantt_template_projects = cache.get('need_update_gantt_template_projects', set())
    if project.id in need_update_gantt_template_projects:
        need_update_gantt_template_projects.remove(project.id)
        cache.set('need_update_gantt_template_projects', need_update_gantt_template_projects, None)


@api_view(['GET'])
def project_gantt_tasks(request, gantt_chart_id=None, uid=None):
    project_gantt = None
    if gantt_chart_id:
        project_gantt = get_object_or_404(ProjectGanttChart, pk=gantt_chart_id)
    if uid:
        project_gantt = get_object_or_404(ProjectGanttChart, uid=uid)
    if not project_gantt:
        return Response({'result': False, 'message': "需要参数gantt_chart_id或uid"})

    params = request.GET
    start_date = None
    end_date = None
    try:
        if params.get('start_date'):
            start_date = datetime.strptime(params.get('start_date'), '%Y-%m-%d').date()
        if params.get('end_date'):
            end_date = datetime.strptime(params.get('end_date'), '%Y-%m-%d').date()
    except Exception as e:
        return api_bad_request(message=str(e))
    stages = params.get('stages', '')
    roles = params.get('roles', None)
    diff_last_week = True if params.get('diff_last_week', False) in {'true', '1', 'True'} else False
    task_status = params.get('task_status', 'all')

    gantt_tasks = project_gantt.task_topics.all()
    topic_total = gantt_tasks.count()
    project_gantt_catalogues = project_gantt.task_catalogues.all()

    # 没有筛选
    if not roles and task_status == 'all' and not any([start_date, end_date, stages]):
        task_catalogues = project_gantt_catalogues
        catalogues_data = GanttTaskCatalogueSerializer(task_catalogues, many=True).data
    else:
        task_topics = gantt_tasks
        if task_status == 'undone':
            task_topics = task_topics.filter(is_done=False)
        elif task_status == 'expired':
            task_topics = task_topics.filter(expected_finish_time__lt=timezone.now().date(), is_done=False)

        if roles:
            role_id_list = re.sub(r'[;；,，]', ' ', roles).split()
            if role_id_list:
                task_topics = task_topics.filter(role_id__in=role_id_list)

        if start_date and end_date:
            task_topics = task_topics.filter(start_time__lte=end_date, expected_finish_time__gte=start_date)

        if stages:
            stage_id_list = re.sub(r'[;；,，]', ' ', stages).split()
            if stage_id_list:
                task_topics_tem = task_topics
                task_topics = GanttTaskTopic.objects.none()
                for stage_id in stage_id_list:
                    stage = get_object_or_404(ProjectStage, pk=stage_id)
                    task_topics_ob = task_topics_tem.filter(
                        start_time__lte=stage.end_date, expected_finish_time__gte=stage.start_date)
                    task_topics = task_topics | task_topics_ob

        has_catalogue_topics = task_topics.order_by('number', 'id')
        catalogue_list = set([topic.catalogue for topic in has_catalogue_topics])
        catalogues_data = GanttTaskCatalogueSerializer(catalogue_list, many=True).data
        has_catalogue_topics_data = GanttTaskTopicSerializer(has_catalogue_topics, many=True).data
        catalogue_topics_dict = {}
        for topic_data in has_catalogue_topics_data:
            if topic_data['catalogue']['id'] not in catalogue_topics_dict:
                catalogue_topics_dict[topic_data['catalogue']['id']] = []
            catalogue_topics_dict[topic_data['catalogue']['id']].append(topic_data)
        for catalogue_data in catalogues_data:
            catalogue_data['task_topics'] = catalogue_topics_dict[catalogue_data['id']]
    if diff_last_week:
        add_deleted_data = False
        # 查看过期任务时 或角色筛选时 不展示已删除的任务
        if not roles and task_status != 'expired':
            add_deleted_data = True
        catalogues_data = get_gantt_tasks_data_with_last_week_data(project_gantt, catalogues_data,
                                                                   add_deleted_data=add_deleted_data)
    catalogue_list = sorted(catalogues_data, key=lambda task: (task['is_deleted'], task['number'], task['id']))
    result_data = {'result': True, 'data': catalogue_list, 'topic_total': topic_total}
    return Response(result_data)


class GanttRoleList(APIView):
    def post(self, request, gantt_chart_id):
        project_gantt = get_object_or_404(ProjectGanttChart, pk=gantt_chart_id)
        request_data = deepcopy(request.data)
        request_data['gantt_chart'] = project_gantt.id

        serializer = GanttRoleSerializer(data=request_data)
        if serializer.is_valid():
            if project_gantt.roles.filter(name=request_data['name']).exists():
                return Response({"result": False, "message": '该甘特图已经存在相同名字的角色'})
            gantt_role = serializer.save()
            Log.build_create_object_log(request.user, gantt_role, project_gantt)
            return Response({"result": True, 'data': serializer.data})
        return Response({"result": False, "message": str(serializer.errors)})


class GanttRoleDetail(APIView):
    def post(self, request, role_id):
        gantt_role = get_object_or_404(GanttRole, pk=role_id)
        project_gantt = gantt_role.gantt_chart
        origin = deepcopy(gantt_role)
        request_data = deepcopy(request.data)
        request_data['gantt_chart'] = gantt_role.gantt_chart.id
        serializer = GanttRoleSerializer(gantt_role, data=request_data)
        if serializer.is_valid():
            if project_gantt.roles.exclude(pk=gantt_role.id).filter(name=request_data['name']).exists():
                return Response({"result": False, "message": '该甘特图已经存在相同名字的角色'})
            gantt_role = serializer.save()
            Log.build_update_object_log(request.user, origin, gantt_role, gantt_role.gantt_chart)
            return Response({"result": True, 'data': serializer.data})
        return Response({"result": False, "message": str(serializer.errors)})

    def delete(self, request, role_id):
        gantt_role = get_object_or_404(GanttRole, pk=role_id)
        origin = deepcopy(gantt_role)
        if gantt_role.task_topics.all().count() > 0:
            return Response({"result": False, "message": "该角色还有任务，不能删除"})
        gantt_role.delete()
        Log.build_delete_object_log(request.user, origin, origin.gantt_chart)
        return Response({"result": True, "message": "删除成功"})


class GanttTaskCatalogueList(APIView):
    def post(self, request, gantt_chart_id):
        project_gantt = get_object_or_404(ProjectGanttChart, pk=gantt_chart_id)
        request_data = deepcopy(request.data)
        previous_catalogue_id = request_data.pop('previous_catalogue', None)
        next_siblings = []
        if previous_catalogue_id:
            previous_task = get_object_or_404(GanttTaskCatalogue, pk=previous_catalogue_id)
            next_siblings = list(get_current_gantt_task_or_catalogue_next_siblings(previous_task))
            request_data['number'] = previous_task.number + 1
        else:
            request_data['number'] = get_current_gantt_catalogue_max_number(project_gantt=project_gantt) + 1

        request_data['gantt_chart'] = project_gantt.id
        serializer = GanttTaskCatalogueSerializer(data=request_data)
        if serializer.is_valid():
            if project_gantt.task_catalogues.filter(name=request_data['name']).exists():
                return Response({"result": False, "message": '该甘特图已经存在相同名字的分类'})
            gantt_task_catalogue = serializer.save()
            if next_siblings:
                for sibling in next_siblings:
                    sibling.number = sibling.number + 1
                    sibling.save()
            Log.build_create_object_log(request.user, gantt_task_catalogue, project_gantt)
            return Response({"result": True, 'data': serializer.data})
        return Response({"result": False, "message": str(serializer.errors)})


class GanttTaskCatalogueDetail(APIView):
    def post(self, request, catalogue_id):
        gantt_task_catalogue = get_object_or_404(GanttTaskCatalogue, pk=catalogue_id)
        project_gantt = gantt_task_catalogue.gantt_chart
        origin = deepcopy(gantt_task_catalogue)
        request_data = deepcopy(request.data)
        request_data['gantt_chart'] = gantt_task_catalogue.gantt_chart.id
        serializer = GanttTaskCatalogueSerializer(gantt_task_catalogue, data=request_data)
        if serializer.is_valid():
            if project_gantt.task_catalogues.exclude(pk=gantt_task_catalogue.id).filter(
                    name=request_data['name']).exists():
                return Response({"result": False, "message": '该甘特图已经存在相同名字的分类'})
            gantt_task_catalogue = serializer.save()
            Log.build_update_object_log(request.user, origin, gantt_task_catalogue, gantt_task_catalogue.gantt_chart)
            return Response({"result": True, 'data': serializer.data})
        return Response({"result": False, "message": str(serializer.errors)})

    def delete(self, request, catalogue_id):
        gantt_task_catalogue = get_object_or_404(GanttTaskCatalogue, pk=catalogue_id)
        if gantt_task_catalogue.task_topics.all().count() > 0:
            return Response({"result": False, "message": "该分类下还有任务，不能删除"})
        origin = deepcopy(gantt_task_catalogue)
        move_up_current_gantt_task_or_catalogue_next_siblings(origin)
        gantt_task_catalogue.delete()
        Log.build_delete_object_log(request.user, origin, origin.gantt_chart)
        return Response({"result": True, "message": "删除成功"})


@api_view(['POST'])
def change_catalogue_name(request, catalogue_id):
    gantt_task_catalogue = get_object_or_404(GanttTaskCatalogue, pk=catalogue_id)
    name = request.data.get('name', None)
    if name:
        gantt_task_catalogue.name = name
        gantt_task_catalogue.save()
    return Response({"result": True, "message": "成功"})


def clean_gantt_role_and_catalogue_data(project_gantt, request_data):
    role_id = request_data.pop('role_id', None)
    role_name = request_data.pop('role_name', None)
    catalogue_id = request_data.pop('catalogue_id', None)
    catalogue_name = request_data.pop('catalogue_name', None)
    if catalogue_id:
        if project_gantt.task_catalogues.filter(pk=catalogue_id).exists():
            request_data['catalogue'] = catalogue_id
    else:
        if project_gantt.task_catalogues.filter(name=catalogue_name).exists():
            gantt_task_catalogue = project_gantt.task_catalogues.filter(name=catalogue_name).first()
        else:
            catalogue_data = {}
            catalogue_data['number'] = get_current_gantt_catalogue_max_number(project_gantt) + 1
            catalogue_data['gantt_chart'] = project_gantt.id
            catalogue_data['name'] = catalogue_name
            catalogue_serializer = GanttTaskCatalogueSerializer(data=catalogue_data)
            if catalogue_serializer.is_valid():
                gantt_task_catalogue = catalogue_serializer.save()
            else:
                return {"result": False, "message": str(catalogue_serializer.errors)}
        request_data['catalogue'] = gantt_task_catalogue.id
    if role_id:
        request_data['role'] = role_id
    elif role_name:
        if project_gantt.roles.filter(name=role_name).exists():
            request_data['role'] = project_gantt.roles.filter(name=role_name).first().id
        else:
            role_data = {}
            role_data['gantt_chart'] = project_gantt.id
            role_data['name'] = role_name
            role_serializer = GanttRoleSerializer(data=role_data)
            if role_serializer.is_valid():
                gantt_role = role_serializer.save()
                request_data['role'] = gantt_role.id
            else:
                return {"result": False, "message": str(role_serializer.errors)}
    return {"result": True, "message": ''}


class GanttTaskTopicList(APIView):
    def post(self, request, gantt_chart_id):
        project_gantt = get_object_or_404(ProjectGanttChart, pk=gantt_chart_id)
        request_data = deepcopy(request.data)
        request_data['gantt_chart'] = project_gantt.id
        request_data['only_workday'] = True if request_data.pop('only_workday', True) else False
        timedelta_days = request_data.get('timedelta_days', None)
        if not timedelta_days:
            return api_request_params_required("timedelta_days")
        if float(timedelta_days) <= 0 or float(timedelta_days) > 365:
            return Response({"result": False, "message": '任务持续天数必须在0-365之间'})
        previous_topic_id = request_data.pop('previous_topic', None)
        previous_task = None

        if previous_topic_id:
            previous_task = get_object_or_404(GanttTaskTopic, pk=previous_topic_id)
            request_data['catalogue_id'] = previous_task.catalogue.id
            request_data['catalogue_name'] = previous_task.catalogue.name
        result_data = clean_gantt_role_and_catalogue_data(project_gantt, request_data)
        if not result_data['result']:
            return Response({"result": False, "message": result_data['message']})
        next_siblings = []
        if previous_task:
            next_siblings = list(get_current_gantt_task_or_catalogue_next_siblings(previous_task))
            request_data['number'] = previous_task.number + 1
        else:
            gantt_task_catalogue = get_object_or_404(GanttTaskCatalogue, pk=request_data['catalogue'])
            request_data['number'] = get_current_gantt_catalogue_task_max_number(gantt_task_catalogue) + 1

        request_data['gantt_chart'] = project_gantt.id
        serializer = GanttTaskTopicCreateSerializer(data=request_data)
        if serializer.is_valid():
            task = serializer.save()
            if not task.expected_finish_time:
                task.expected_finish_time = task.start_time + timedelta(days=math.ceil(task.timedelta_days) - 1)
            if next_siblings:
                for next_task in next_siblings:
                    next_task.number = next_task.number + 1
                    next_task.save()
            Log.build_create_object_log(request.user, task, project_gantt)
            return Response({"result": True, 'data': serializer.data})
        return Response({"result": False, "message": str(serializer.errors)})


@api_view(['GET'])
def project_gantt_chart_last_task_topic(request, gantt_chart_id):
    project_gantt = get_object_or_404(ProjectGanttChart, pk=gantt_chart_id)
    gantt_tasks = project_gantt.task_topics.order_by('-modified_at', '-id')
    if gantt_tasks.exists():
        gantt_task = gantt_tasks.first()
        topic_data = GanttTaskTopicSerializer(gantt_task).data
        return Response({"result": True, 'data': topic_data})
    return Response({"result": False, 'data': None})


class GanttTaskTopicDetail(APIView):
    def post(self, request, topic_id):
        gantt_task_topic = get_object_or_404(GanttTaskTopic, pk=topic_id)
        project_gantt = gantt_task_topic.gantt_chart
        origin = deepcopy(gantt_task_topic)
        request_data = deepcopy(request.data)
        request_data['gantt_chart'] = gantt_task_topic.gantt_chart.id
        request_data['only_workday'] = True if request_data.pop('only_workday', True) else False
        if request_data.get('timedelta_days', None) != None and (
                float(request_data['timedelta_days']) <= 0 or float(request_data['timedelta_days']) > 365):
            return Response({"result": False, "message": '任务持续天数必须在0-365之间'})
        result_data = clean_gantt_role_and_catalogue_data(project_gantt, request_data)
        if not result_data['result']:
            return Response({"result": False, "message": result_data['message']})
        move_up_list = []

        # 分类变了
        if gantt_task_topic.catalogue.id != int(request_data['catalogue']):
            gantt_task_catalogue = get_object_or_404(GanttTaskCatalogue, pk=request_data['catalogue'])
            request_data['number'] = get_current_gantt_catalogue_task_max_number(gantt_task_catalogue) + 1
            move_up_list = list(get_current_gantt_task_or_catalogue_next_siblings(gantt_task_topic))

        serializer = GanttTaskTopicCreateSerializer(gantt_task_topic, data=request_data)
        if serializer.is_valid():
            gantt_task_topic = serializer.save()
            if not request_data.get('catalogue', None):
                gantt_task_topic.catalogue = None
                gantt_task_topic.save()
            for task in move_up_list:
                task.number = task.number - 1
                task.save()
            Log.build_update_object_log(request.user, origin, gantt_task_topic, gantt_task_topic.gantt_chart)
            return Response({"result": True, 'data': serializer.data})
        return Response({"result": False, "message": str(serializer.errors)})

    def delete(self, request, topic_id):
        gantt_task_topic = get_object_or_404(GanttTaskTopic, pk=topic_id)
        origin = deepcopy(gantt_task_topic)
        move_up_current_gantt_task_or_catalogue_next_siblings(origin)
        gantt_task_topic.delete()
        Log.build_delete_object_log(request.user, origin, origin.gantt_chart)
        return Response({"result": True, "message": "删除成功"})


@api_view(['POST'])
def move_current_gantt_task(request, obj_id, obj_type, move_type):
    if obj_type == 'catalogue':
        current_obj = get_object_or_404(GanttTaskCatalogue, pk=obj_id)
    elif obj_type == 'topic':
        current_obj = get_object_or_404(GanttTaskTopic, pk=obj_id)
    else:
        return Response({"result": False, "message": "obj_type参数为无效值"})

    origin = deepcopy(current_obj)
    if move_type == 'move_up':
        previous_sibling = get_current_gantt_task_or_catalogue_previous_sibling(current_obj)
        if previous_sibling:
            if current_obj.number == previous_sibling.number:
                previous_sibling.number, current_obj.number = current_obj.number, previous_sibling.number - 1
            else:
                previous_sibling.number, current_obj.number = current_obj.number, previous_sibling.number
            previous_sibling.save()
            current_obj.save()
    if move_type == 'move_down':
        next_sibling = get_current_gantt_task_or_catalogue_next_sibling(current_obj)
        if next_sibling:
            if current_obj.number == next_sibling.number:
                next_sibling.number, current_obj.number = current_obj.number, next_sibling.number + 1
            else:
                next_sibling.number, current_obj.number = current_obj.number, next_sibling.number
            next_sibling.save()
            current_obj.save()

    if obj_type == 'catalogue':
        data = GanttTaskCatalogueSerializer(current_obj).data
    else:
        data = GanttTaskTopicSerializer(current_obj).data

    Log.build_update_object_log(request.user, origin, current_obj, current_obj.gantt_chart)
    return Response({"result": True, "message": "", 'data': data})


@api_view(['POST'])
def drag_gantt_task_catalogue(request):
    origin_id = request.data.get('origin', None)
    target_id = request.data.get('target', None)

    if not all([origin_id, target_id]):
        return Response({"result": False, "message": "拖拽对象的id参数origin、目标对象的id参数target为必填", 'data': None})

    origin_catalogue = GanttTaskCatalogue.objects.filter(pk=origin_id)
    target_catalogue = GanttTaskCatalogue.objects.filter(pk=target_id)
    if not origin_catalogue.exists():
        return Response({"result": False, "message": "拖拽对象不存在", 'data': None})

    if not target_catalogue.exists():
        return Response({"result": False, "message": "目标对象不存在", 'data': None})

    origin_catalogue = origin_catalogue.first()
    target_catalogue = target_catalogue.first()

    if origin_catalogue.gantt_chart_id != target_catalogue.gantt_chart_id:
        return Response({"result": False, "message": "拖拽对象、目标对象不属于同一个甘特图", 'data': None})
    gantt_chart = origin_catalogue.gantt_chart

    # 目标对象的位置 比拖拽对象小      拖拽对象占距目标对象的位置   目标对象(包含)与拖拽对象之间的元素都下移一位 number+1

    target_number = target_catalogue.number
    origin_number = origin_catalogue.number
    if target_number < origin_number:
        middle_siblings = gantt_chart.task_catalogues.filter(number__gte=target_number, number__lt=origin_number)
        for sibling in middle_siblings:
            sibling.number = sibling.number + 1
            sibling.save()
        origin_catalogue.number = target_number
        origin_catalogue.save()

    # 目标对象的位置 比拖拽对象大      拖拽对象占距目标对象的位置   目标对象(包含)与拖拽对象之间的元素都上移一位 number-1
    if target_number > origin_number:
        middle_siblings = gantt_chart.task_catalogues.filter(number__gt=origin_number, number__lte=target_number)
        for sibling in middle_siblings:
            sibling.number = sibling.number - 1
            sibling.save()
        origin_catalogue.number = target_number
        origin_catalogue.save()
    return Response({"result": True, "message": "", 'data': None})


@api_view(['POST'])
def drag_gantt_task_topic(request):
    origin_id = request.data.get('origin', None)
    target_id = request.data.get('target', None)

    if not all([origin_id, target_id]):
        return Response({"result": False, "message": "拖拽对象的id参数origin、目标对象的id参数target为必填", 'data': None})

    origin_topic = GanttTaskTopic.objects.filter(pk=origin_id)
    target_topic = GanttTaskTopic.objects.filter(pk=target_id)
    if not origin_topic.exists():
        return Response({"result": False, "message": "拖拽对象不存在", 'data': None})

    if not target_topic.exists():
        return Response({"result": False, "message": "目标对象不存在", 'data': None})

    origin_topic = origin_topic.first()
    target_topic = target_topic.first()

    if origin_topic.catalogue_id != target_topic.catalogue_id:
        return Response({"result": False, "message": "拖拽对象、目标对象不属于同一个甘特图分类", 'data': None})
    catalogue = origin_topic.catalogue

    # 目标对象的位置 比拖拽对象小      拖拽对象占距目标对象的位置   目标对象(包含)与拖拽对象之间的元素都下移一位 number+1

    target_number = target_topic.number
    origin_number = origin_topic.number
    if target_number < origin_number:
        middle_siblings = catalogue.task_topics.filter(number__gte=target_number, number__lt=origin_number)
        for sibling in middle_siblings:
            sibling.number = sibling.number + 1
            sibling.save()
        origin_topic.number = target_number
        origin_topic.save()

    # 目标对象的位置 比拖拽对象大      拖拽对象占距目标对象的位置   目标对象(包含)与拖拽对象之间的元素都上移一位 number-1
    if target_number > origin_number:
        middle_siblings = catalogue.task_topics.filter(number__gt=origin_number, number__lte=target_number)
        for sibling in middle_siblings:
            sibling.number = sibling.number - 1
            sibling.save()
        origin_topic.number = target_number
        origin_topic.save()
    return Response({"result": True, "message": "", 'data': None})


@api_view(['POST'])
def change_current_gantt_task_work_date(request, obj_id):
    gantt_task = get_object_or_404(GanttTaskTopic, pk=obj_id)
    origin = deepcopy(gantt_task)
    origin_data = deepcopy(GanttTaskTopicSerializer(gantt_task).data)
    start_time = request.data.get('start_time', None)
    expected_finish_time = request.data.get('expected_finish_time', None)
    if not any([start_time, expected_finish_time]):
        return Response({"result": False, "message": "请填写有效的起始时间、预计结束时间"})

    # 甘特图整体平移 只改变起始时间
    if start_time and not expected_finish_time:
        serializer = GanttTaskTopicStartTimeSerializer(gantt_task, data=request.data)
        if serializer.is_valid():
            start_time = serializer.validated_data['start_time']
            if gantt_task.only_workday and start_time.weekday() >= 5:
                if start_time.weekday() == 6:
                    start_time = start_time + timedelta(days=1)
                elif start_time.weekday() == 5:
                    start_time = start_time + timedelta(days=2)
                serializer.validated_data['start_time'] = start_time
            gantt_task_topic = serializer.save()
            Log.build_update_object_log(request.user, origin, gantt_task_topic, gantt_task_topic.gantt_chart)
            data = GanttTaskTopicSerializer(gantt_task_topic).data
            return Response({"result": True, 'data': data})
        return Response({"result": False, "message": str(serializer.errors), 'data': origin_data})
    # 甘特图拖拽左侧起始时间、 拖拽右侧结束时间
    elif expected_finish_time and start_time:
        serializer = GanttTaskTopicWorkDateSerializer(gantt_task, data=request.data)
        if serializer.is_valid():
            finish_time = serializer.validated_data['expected_finish_time']
            start_time = serializer.validated_data['start_time']
            if start_time > finish_time:
                return Response({"result": False, "message": "起始时间不能大于结束时间", 'data': origin_data})
            if gantt_task.only_workday:
                if finish_time.weekday() >= 5 and start_time.weekday() >= 5:
                    return Response({"result": False, "message": "起始时间和结束时间不能都在周末", 'data': origin_data})
                # 如果起始时间在周末
                if gantt_task.only_workday and start_time.weekday() >= 5:
                    if start_time.weekday() == 6:
                        start_time = start_time + timedelta(days=1)
                    elif start_time.weekday() == 5:
                        start_time = start_time + timedelta(days=2)
                # 如果结束时间在周末
                if finish_time.weekday() >= 5:
                    # 如果是周日
                    if finish_time.weekday() == 6:
                        finish_time = finish_time - timedelta(days=2)
                    # 如果是周六
                    elif finish_time.weekday() == 5:
                        finish_time = finish_time - timedelta(days=1)
                timedelta_days = get_days_count_between_date(start_time, finish_time, only_workday=True)
            else:
                timedelta_days = get_days_count_between_date(start_time, finish_time, only_workday=False)

            if gantt_task.half_day_position:
                timedelta_days = timedelta_days - 0.5
            gantt_task.start_time = start_time
            gantt_task.timedelta_days = timedelta_days
            gantt_task.save()
            data = GanttTaskTopicSerializer(gantt_task).data
            Log.build_update_object_log(request.user, origin, gantt_task, gantt_task.gantt_chart)
            return Response({"result": True, 'data': data, 'message': ''})
        return Response({"result": False, "message": str(serializer.errors), 'data': origin_data})


class ProjectPositionNeedList(APIView):
    def get(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        position_needs = project.position_needs.all()
        need_status = request.GET.get('status', None)
        closed_needs = position_needs.filter(done_at__isnull=False)
        ongoing_needs = position_needs.filter(done_at__isnull=True)
        if need_status == 'closed':
            position_needs = closed_needs.order_by('-created_at')
        if need_status == 'ongoing':
            position_needs = ongoing_needs.order_by('created_at')
        return build_pagination_response(request, position_needs, JobPositionNeedSerializer)

    def post(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        request_data = deepcopy(request.data)
        request_data['project'] = project.id
        request_data['submitter'] = request.user.id
        role_id = request_data.pop('role', None)
        if role_id:
            request_data['role'] = get_object_or_404(Role, pk=role_id).id
        serializer = PositionNeedCreateSerializer(data=request_data)
        if serializer.is_valid():
            position_need = serializer.save()
            Log.build_create_object_log(request.user, position_need, project)
            Log.build_create_object_log(request.user, position_need, position_need)
            # 消息推送 自动创建任务
            return api_success(serializer.data)
        return api_bad_request(str(serializer.errors))


@api_view(['GET'])
def all_project_job_position_needs_statistic(request):
    position_needs = JobPositionNeed.objects.all()
    closed_needs = position_needs.filter(done_at__isnull=False)
    ongoing_needs = position_needs.filter(done_at__isnull=True)
    closed_needs_total = closed_needs.count()
    ongoing_needs_total = ongoing_needs.count()
    data = {'closed_needs_total': closed_needs_total, 'ongoing_needs_total': ongoing_needs_total}
    return api_success(data)


@api_view(['GET'])
@func_perm_required('view_all_project_job_position_needs')
def all_project_job_position_needs(request):
    position_needs = JobPositionNeed.objects.all()
    need_status = request.GET.get('status', None)
    closed_needs = position_needs.filter(done_at__isnull=False)
    ongoing_needs = position_needs.filter(done_at__isnull=True)
    if need_status == 'closed':
        position_needs = closed_needs.order_by('-created_at')
    if need_status == 'ongoing':
        position_needs = ongoing_needs.order_by('created_at')
    return build_pagination_response(request, position_needs, JobPositionNeedSerializer)


@api_view(['GET'])
def my_project_job_position_needs_statistic(request):
    projects = get_user_projects(request.user)
    projects_ids = projects.values_list('id', flat=True)
    position_needs = JobPositionNeed.objects.filter(project_id__in=projects_ids)

    closed_needs = position_needs.filter(done_at__isnull=False)
    ongoing_needs = position_needs.filter(done_at__isnull=True)
    closed_needs_total = closed_needs.count()
    ongoing_needs_total = ongoing_needs.count()
    data = {'closed_needs_total': closed_needs_total, 'ongoing_needs_total': ongoing_needs_total}
    return api_success(data)


@api_view(['GET'])
@func_perm_required('view_my_project_job_position_needs')
def my_project_job_position_needs(request):
    projects = get_user_projects(request.user)
    projects_ids = projects.values_list('id', flat=True)
    position_needs = JobPositionNeed.objects.filter(project_id__in=projects_ids)

    page = request.GET.get('page', None)
    page_size = request.GET.get('page_size', None)
    need_status = request.GET.get('status', None)

    closed_needs = position_needs.filter(done_at__isnull=False)
    ongoing_needs = position_needs.filter(done_at__isnull=True)
    closed_needs_total = closed_needs.count()
    ongoing_needs_total = ongoing_needs.count()

    if need_status == 'closed':
        position_needs = closed_needs.order_by('-created_at')
    if need_status == 'ongoing':
        position_needs = ongoing_needs.order_by('created_at')

    return build_pagination_response(request, position_needs, JobPositionNeedSerializer)


@api_view(['GET'])
def position_needs_logs(request, is_mine):
    if is_mine:
        my_submitted_position_needs = request.user.submitted_position_needs.all()
        my_project_position_needs = JobPositionNeed.objects.filter(project__manager_id=request.user.id)
        position_needs = (my_submitted_position_needs | my_project_position_needs).distinct()
    else:
        position_needs = JobPositionNeed.objects.all()

    logs = []

    start_time = datetime.now() - timedelta(days=45)

    if position_needs.exists():
        logs = position_needs.first().logs.filter(created_at__gte=start_time)
        for position_need in position_needs[1:]:
            logs = logs | position_need.logs.filter(created_at__gte=start_time)
        logs = logs.order_by('-created_at')

    result = []
    date = datetime.now().date()
    if logs:
        while logs.exists():
            next_day = date + timedelta(days=1)
            previous_day = date + timedelta(days=-1)
            date_logs = logs.filter(created_at__range=(date, next_day))
            data = LogSerializer(date_logs, many=True).data
            if data:
                result.append({"date": str(date), 'data': data})
            logs = logs.exclude(created_at__range=(date, next_day))
            date = previous_day
    return Response({"result": True, 'data': result})


class JobPositionNeedDetail(APIView):
    def get(self, request, position_need_id):
        position_need = get_object_or_404(JobPositionNeed, pk=position_need_id)
        serializer = JobPositionNeedSerializer(position_need)
        return Response({"result": True, 'data': serializer.data})

    def post(self, request, position_need_id):
        user_id = request.user.id
        position_need = get_object_or_404(JobPositionNeed, pk=position_need_id)
        project = position_need.project
        origin = deepcopy(position_need)
        request_data = deepcopy(request.data)
        serializer = PositionNeedEditSerializer(position_need, data=request_data)
        if serializer.is_valid():
            position_need = serializer.save()
            Log.build_update_object_log(request.user, origin, position_need, position_need)

            content = '{user}修改了项目【{project}】{role}工程师需求，预计预计确认日期：{expected_at}'.format(user=request.user.username,
                                                                                        role=position_need.role.name,
                                                                                        project=project.name,
                                                                                        expected_at=position_need.expected_date)
            tpm_url = get_protocol_host(request) + build_page_path("projects_position_needs")
            pm_url = get_protocol_host(request) + build_page_path("my_position_needs")
            principals = User.objects.filter(username__in=settings.RESPONSIBLE_TPM_FOR_PROJECT_JOB_NEEDS,
                                             is_active=True)
            for principal in principals:
                if user_id != principal.id:
                    create_notification(principal, content, tpm_url)
            if project.manager_id and project.manager_id != user_id:
                create_notification(project.manager, content, pm_url)

            detail_serializer = JobPositionNeedSerializer(position_need)
            return Response({"result": True, 'message': '', 'data': detail_serializer.data})
        return Response({"result": False, 'message': str(serializer.errors)})

    def delete(self, request, position_need_id):
        position_need = get_object_or_404(JobPositionNeed, pk=position_need_id)
        project = position_need.project
        user_id = request.user.id
        if user_id not in [position_need.submitter_id, project.mentor_id,
                           project.manager_id] and not request.user.is_superuser:
            return Response({"result": False, 'message': '只有项目管理员、项目经理、导师、工程师需求提交人可以取消工程师需求'})
        if position_need.status != 0:
            return Response({"result": False, 'message': '工程师需求当前状态为{status_display}，不能取消'.format(
                status_display=position_need.get_status_display())})
        origin = deepcopy(position_need)
        position_need.candidates.filter(status=0).update(status=3, confirmed_at=timezone.now(),
                                                         refuse_reason="工程师需求被取消，自动设置为未选择", handler=request.user)
        position_need.status = 2
        position_need.canceled_at = timezone.now()
        # 全部联系了才算最终完成
        if not position_need.need_feedback:
            if not position_need.done_at:
                position_need.done_at = timezone.now()
        else:
            position_need.done_at = None
        position_need.save()

        # 消息推送
        content = '{}取消了项目【{}】的【{}】分配需求'.format(request.user.username, position_need.project.name,
                                                position_need.role.name)
        principals = User.objects.filter(username__in=settings.RESPONSIBLE_TPM_FOR_PROJECT_JOB_NEEDS,
                                         is_active=True)
        for principal in principals:
            if principal.id != request.user.id:
                create_notification(principal, content, is_important=True)
        if project.manager and project.manager_id != request.user.id:
            create_notification(project.manager, content, is_important=True)

        Log.build_update_object_log(request.user, origin, position_need, position_need)
        return Response({"result": True})


class JobPositionCandidateList(APIView):
    def get(self, request, position_need_id):
        position_need = get_object_or_404(JobPositionNeed, pk=position_need_id)
        candidates = position_need.candidates.all()
        serializer = JobPositionCandidateSerializer(candidates, many=True)
        return Response({"result": True, 'data': serializer.data})

    def post(self, request, position_need_id):
        request_data = deepcopy(request.data)
        position_need = get_object_or_404(JobPositionNeed, pk=position_need_id)
        request_data['position_need'] = position_need.id
        request_data['submitter'] = request.user.id
        developer_id = request_data.pop('developer_id', None)
        if developer_id:
            developer = position_need.role.developers.filter(pk=developer_id)
            if developer.exists():
                developer = developer.first()
                if position_need.candidates.filter(status=0, developer_id=developer.id).exists():
                    return api_bad_request(message="该职位需求中已存在该候选人")
                request_data['developer'] = developer.id
            else:
                return Response({"result": False, 'message': '职位:{} 中不包含该工程师'.format(position_need.role.name)})

        serializer = JobPositionCandidateSerializer(data=request_data)
        if serializer.is_valid():
            position_candidate = serializer.save()
            Log.build_create_object_log(request.user, position_candidate, position_need)
            create_project_position_candidate_auto_task(position_candidate)
            return Response({"result": True, 'data': serializer.data})
        return Response({"result": False, 'message': str(serializer.errors)})


class JobPositionCandidateDetail(APIView):
    def get(self, request, candidate_id):
        position_candidate = get_object_or_404(JobPositionCandidate, pk=candidate_id)
        serializer = JobPositionCandidateSerializer(position_candidate)
        return Response({"result": True, 'data': serializer.data})

    def post(self, request, candidate_id):
        position_candidate = get_object_or_404(JobPositionCandidate, pk=candidate_id)
        origin = deepcopy(position_candidate)
        position_need = position_candidate.position_need
        request_data = deepcopy(request.data)
        request_data['position_need'] = position_need.id
        developer_id = request_data.pop('developer_id', None)
        if developer_id:
            if position_need.role.developers.filter(pk=developer_id).exists():
                request_data['developer'] = developer_id
            else:
                return Response({"result": False, 'message': '职位:{} 中不包含该工程师'.format(position_need.role.name)})
        serializer = JobPositionCandidateSerializer(position_candidate, data=request_data)
        if serializer.is_valid():
            position_candidate = serializer.save()
            Log.build_update_object_log(request.user, origin, position_candidate, position_need)
            return Response({"result": True, 'data': serializer.data})
        return Response({"result": False, 'message': str(serializer.errors)})


@api_view(['POST'])
@transaction.atomic
def position_candidate_status(request, candidate_id, type):
    position_candidate = get_object_or_404(JobPositionCandidate, pk=candidate_id)
    project = position_candidate.position_need.project
    origin_candidate = deepcopy(position_candidate)
    position_need = position_candidate.position_need
    origin_position_need = deepcopy(position_need)
    if type == 'initial_contact':
        if not position_candidate.initial_contact_at:
            position_candidate.initial_contact_at = timezone.now()
            position_candidate.save()
    elif type == 'confirm':
        if position_candidate.status != 0:
            return Response({"result": False, 'message': '该工程师不处在待确认状态，当前状态为{},不能进行确认操作'.format(
                position_candidate.get_status_display())})
        if position_need.status != 0:
            return Response({"result": False, 'message': '工程师需求当前状态为{status_display}，不能对其他候选人进行确认操作'.format(
                status_display=position_need.get_status_display())})

        # 设置事物保存点（可设多个）
        t1 = transaction.savepoint()
        try:
            # 候选人确认
            position_candidate.status = 1
            position_candidate.confirmed_at = timezone.now()
            position_candidate.handler = request.user
            if not position_candidate.contact_at:
                position_candidate.contact_at = timezone.now()
            position_candidate.save()

            # 未处理候选人默认设置为未选择、 根据全都拒绝工程师列表处理不行的工程师
            refusing_candidates = request.data.get('refusing_candidates', None)
            refusing_candidate_dict = {}
            for refusing_candidate in refusing_candidates:
                candidate_id = refusing_candidate['id']
                refusing_candidate_dict[candidate_id] = refusing_candidate
            pending_candidates = position_need.candidates.filter(status=0)
            for pending_candidate in pending_candidates:
                candidate_id = pending_candidate.id
                # 未选择
                next_status = 3
                refuse_reason = "已确认其他工程师，自动设置为未选择"
                refuse_remarks = None
                # 拒绝的
                if candidate_id in refusing_candidate_dict:
                    next_status = 2
                    refuse_reason = refusing_candidate_dict[candidate_id].get('refuse_reason', None)
                    refuse_remarks = refusing_candidate_dict[candidate_id].get('refuse_remarks', None)
                    pending_candidate.initial_contact_at = pending_candidate.initial_contact_at or timezone.now()

                pending_candidate.refuse_reason = refuse_reason or None
                pending_candidate.refuse_remarks = refuse_remarks or None
                pending_candidate.status = next_status
                pending_candidate.confirmed_at = timezone.now()
                pending_candidate.handler = request.user
                pending_candidate.save()

            # 职位需求确认
            position_need.confirmed_at = timezone.now()
            position_need.status = 1
            position_need.save()

            # 创建项目开发职位
            job_position = JobPosition.objects.create(role=position_need.role, developer=position_candidate.developer,
                                                      project=position_need.project)
            if position_need.role_remarks:
                job_position.role_remarks = position_need.role_remarks

            # 【code review】#
            #  确认工程师 不需要填写报酬 和 周期
            if position_need.period:
                job_position.period = position_need.period
            send_project_job_position_update_reminder.delay(position_need.project.id)
            if request.data.get('pay', None):
                job_position.pay = float(request.data['pay'])
            if request.data.get('period', None):
                job_position.period = float(request.data['period'])
            # 【code review】#
            #  确认工程师 不需要填写报酬 和 周期

            job_position.save()
            transaction.savepoint_commit(t1)
            Log.build_create_object_log(request.user, job_position, related_object=position_need.project,
                                        comment='项目工程师需求候选人确认后自动创建')
        except Exception as e:
            transaction.savepoint_rollback(t1)
            logger.error(e)
            return Response({'result': False, 'message': "初始化过程出错 请联系管理员"})
    elif type == 'refuse':
        if position_candidate.status != 0:
            return Response({"result": False, 'message': '该工程师不处在待确认状态，当前状态为{},不能进行拒绝操作'.format(
                position_candidate.get_status_display())})
        if position_need.status != 0:
            return Response({"result": False, 'message': '工程师需求当前状态为{status_display}，无需对其他候选人进行拒绝操作'.format(
                status_display=position_need.get_status_display())})
        position_candidate.status = 2
        position_candidate.confirmed_at = timezone.now()
        position_candidate.refuse_reason = request.data.get('refuse_reason', '')
        position_candidate.refuse_remarks = request.data.get('refuse_remarks', '')

        position_candidate.handler = request.user
        position_candidate.save()

        # 消息推送 自动创建任务
        if position_need.need_new_candidate:
            create_project_position_need_auto_task(position_need)
    elif type == 'contact':
        if not position_candidate.contact_at:
            position_candidate.contact_at = timezone.now()
            position_candidate.save()
        else:
            return Response({"result": False, 'message': '该候选人已确认联系'})
    else:
        return Response({"result": False, 'message': '请传入有效的type参数值：contact、refuse、confirm'})

    if position_need.status != 0 and not position_need.need_feedback:
        if not position_need.done_at:
            position_need.done_at = timezone.now()
    else:
        position_need.done_at = None
    position_need.save()
    Log.build_update_object_log(request.user, origin_candidate, position_candidate, position_need)
    Log.build_update_object_log(request.user, origin_position_need, position_need, position_need)
    return Response({"result": True, 'message': ''})


@api_view(['POST'])
def gantt_task_toggle_done(request, topic_id):
    gantt_task = get_object_or_404(GanttTaskTopic, pk=topic_id)
    project = gantt_task.gantt_chart.project
    if request.user.id != project.manager_id and not request.user.is_superuser:
        return api_permissions_required('项目经理确认甘特图任务')

    origin = deepcopy(gantt_task)
    message_temp = ''
    if gantt_task.is_done:
        gantt_task.done_at = None
        gantt_task.is_done = False
        if gantt_task.is_dev_done and gantt_task.dev_done_type != 'self':
            gantt_task.dev_done_at = None
            gantt_task.is_dev_done = False
            gantt_task.dev_done_type = None
    else:
        gantt_task.done_at = timezone.now()
        gantt_task.is_done = True
        if not gantt_task.is_dev_done:
            gantt_task.dev_done_at = timezone.now()
            gantt_task.is_dev_done = True
            gantt_task.dev_done_type = 'auto'
        gantt_task.save()
    gantt_task.save()
    Log.build_update_object_log(request.user, origin, gantt_task, related_object=gantt_task.gantt_chart)
    data = GanttTaskTopicSerializer(gantt_task).data
    return Response({'result': True, 'message': '', 'data': data})


@api_view(['POST'])
def gantt_task_dev_toggle_done(request, topic_id):
    gantt_task = get_object_or_404(GanttTaskTopic, pk=topic_id)
    origin = deepcopy(gantt_task)
    # if gantt_task.is_done:
    #     return Response({'result': False, 'message': '项目经理已确认最终完成'})
    message_temp = ""
    if gantt_task.is_dev_done:
        gantt_task.dev_done_at = None
        gantt_task.is_dev_done = False
        gantt_task.dev_done_type = None
    else:
        gantt_task.dev_done_at = timezone.now()
        gantt_task.is_dev_done = True
        gantt_task.dev_done_type = 'self'
        message_temp = "项目【{project}】甘特图任务【{name}】勾选完成，操作人:{username}"

    gantt_task.save()

    if message_temp:
        user = request.user
        project = gantt_task.gantt_chart.project
        message = message_temp.format(username=request.user.username, project=project.name, name=gantt_task.name)
        if project.manager_id and project.manager_id != user.id:
            create_notification(project.manager, message)
    Log.build_update_object_log(request.user, origin, gantt_task, related_object=gantt_task.gantt_chart)
    data = GanttTaskTopicSerializer(gantt_task).data

    return Response({'result': True, 'message': '', 'data': data})


@api_view(['POST'])
def gantt_role_last_edited_task(request, role_id):
    gantt_role = get_object_or_404(GanttRole, pk=role_id)
    role_gantt_tasks = gantt_role.task_topics.order_by('-modified_at')
    if role_gantt_tasks.exists():
        last_edited_task = role_gantt_tasks.first()
        data = GanttTaskTopicSerializer(last_edited_task).data
        expected_finish_time = last_edited_task.expected_finish_time
        workable_date = expected_finish_time + timedelta(days=1)
        # 默认为工作日
        if workable_date.weekday() == 6:
            workable_date = workable_date + timedelta(days=1)
        if workable_date.weekday() == 5:
            workable_date = workable_date + timedelta(days=2)
        data['workable_date'] = workable_date
        return api_success(data=data)
    return api_success(data=None)


@api_view(['POST'])
def sort_project_gantt_chart_topics(request, id):
    project_gantt = get_object_or_404(ProjectGanttChart, pk=id)
    task_catalogues = project_gantt.task_catalogues.all()
    for task_catalogue in task_catalogues:
        task_topics = task_catalogue.task_topics.all().order_by('expected_finish_time')
        for index, task_topic in enumerate(task_topics):
            task_topic.number = index
            task_topic.save()
    return Response({'result': True, 'message': '', "data": ''})


@api_view(['POST'])
def delay_project_gantt_chart_topics(request, id):
    project_gantt = get_object_or_404(ProjectGanttChart, pk=id)
    topic_id_list = request.data.get('task_topics', [])
    timedelta_days = request.data.get('timedelta_days', 0)
    if topic_id_list and timedelta_days:
        topic_id_list = set(topic_id_list)
        gantt_tasks = project_gantt.task_topics.filter(id__in=topic_id_list)
        for gantt_task in gantt_tasks:
            origin = deepcopy(gantt_task)
            gantt_task.start_time = get_date_by_timedelta_days(gantt_task.start_time, timedelta_days,
                                                               only_workday=gantt_task.only_workday)
            gantt_task.save()
            Log.build_update_object_log(request.user, origin, gantt_task, gantt_task.gantt_chart)
    return api_success()


@api_view(['GET'])
def role_gantt_chart(request, role):
    if role not in ['test', 'design']:
        return Response({'result': False, 'message': '甘特图角色无效'})
    role_types = ['test'] if role == 'test' else ['设计师', 'designer']

    project_ids = Project.ongoing_projects().values_list('id', flat=True)
    task_topics = GanttTaskTopic.objects.filter(role__role_type__in=role_types, gantt_chart__project_id__in=project_ids)
    gantt_chart_ids = set(task_topics.values_list('gantt_chart_id', flat=True))
    role_list = sorted(set(task_topics.values_list('role__name', flat=True)))
    roles_data = []
    for name in role_list:
        role_data = {'name': name, 'id': name}
        roles_data.append(role_data)
    task_topics_data = GanttTaskTopicTimeSerializer(task_topics, many=True).data

    finish_time = timezone.now().date()
    sorted_list = sorted(task_topics_data, key=lambda topic: topic['expected_finish_time'], reverse=True)
    if sorted_list:
        finish_time = sorted_list[0]['expected_finish_time']
    start_time = timezone.now().date()
    sorted_list = sorted(task_topics_data, key=lambda topic: topic['start_time'], reverse=False)
    if sorted_list:
        start_time = sorted_list[0]['start_time']
    if isinstance(start_time, str):
        start_time = datetime.strptime(start_time, settings.DATE_FORMAT).date()
    if isinstance(finish_time, str):
        finish_time = datetime.strptime(finish_time, settings.DATE_FORMAT).date()

    diff_last_week = request.GET.get('diff_last_week', False)
    diff_last_week = True if diff_last_week in {'true', '1', 'True'} else False

    if diff_last_week:
        for gantt_chart_id in gantt_chart_ids:
            last_week_data = cache.get('gantt-{}-data'.format(gantt_chart_id))
            if last_week_data:
                last_start_time = last_week_data.get('start_time')
                if last_start_time and start_time:
                    if isinstance(last_start_time, str):
                        last_start_time = datetime.strptime(last_start_time, settings.DATE_FORMAT).date()
                    if last_start_time < start_time:
                        start_time = last_start_time
                last_finish_time = last_week_data.get('finish_time')
                if last_finish_time and finish_time:
                    if isinstance(last_finish_time, str):
                        last_finish_time = datetime.strptime(last_finish_time, settings.DATE_FORMAT).date()
                    if last_finish_time > finish_time:
                        finish_time = last_finish_time
    data = {'roles': roles_data, 'start_time': start_time, 'finish_time': finish_time}
    return Response({'result': True, 'message': '', "data": data})


@api_view(['GET'])
def role_gantt_chart_tasks(request, role):
    if role not in ['test', 'design']:
        return Response({'result': False, 'message': '甘特图角色无效'})
    params = request.GET
    role_types = ['test'] if role == 'test' else ['设计师', 'designer']
    project_ids = Project.ongoing_projects().values_list('id', flat=True)
    task_topics = GanttTaskTopic.objects.filter(role__role_type__in=role_types, gantt_chart__project_id__in=project_ids)
    roles = params.get('roles', [])
    role_list = re.sub(r'[;；,，]', ' ', roles).split() if roles else []

    diff_last_week = params.get('diff_last_week', False)
    diff_last_week = True if diff_last_week in {'true', '1', 'True'} else False

    task_status = params.get('task_status', 'all')
    if task_status == 'undone':
        task_topics = task_topics.filter(is_done=False)
    elif task_status == 'expired':
        task_topics = task_topics.filter(expected_finish_time__lt=timezone.now().date(), is_done=False)

    if role_list:
        task_topics = task_topics.filter(role__name__in=role_list)

    gantt_chart_dict = {}
    topic_data_list = GanttTaskTopicSerializer(task_topics, many=True).data
    for topic_data in topic_data_list:
        key = topic_data['gantt_chart']['id']
        if key not in gantt_chart_dict:
            gantt_chart_dict[key] = {
                'id': key,
                'project': topic_data['gantt_chart']['project'],
                'task_topics': []
            }
        gantt_chart_dict[key]['task_topics'].append(topic_data)
    data = sorted(gantt_chart_dict.values(), key=lambda x: (x['project']['id']), reverse=True)

    if diff_last_week:
        for gantt_data in data:
            last_week_data = cache.get('gantt-{}-data'.format(gantt_data['id']))
            if last_week_data:
                for topic_data in gantt_data['task_topics']:
                    if topic_data['id'] in last_week_data['topics']:
                        topic_data['last_week_data'] = last_week_data['topics'][topic_data['id']]

    return Response({'result': True, 'message': '', "data": data})


def get_gantt_tasks_data_with_last_week_data(project_gantt, catalogues_data, add_deleted_data=False):
    last_week_data = cache.get('gantt-{}-data'.format(project_gantt.id))
    gantt_tasks = project_gantt.task_topics.all()
    # if not last_week_data:
    #     build_project_gantt_cache_data.delay(project_gantt.id)
    if last_week_data:
        # 把与上周对比删除的分类、任务添加到整个数据
        if add_deleted_data:
            catalogue_data_dict = {}
            catalogue_set = set()
            for catalogue_data in catalogues_data:
                catalogue_data_dict[catalogue_data['id']] = catalogue_data
                catalogue_set.add(catalogue_data['id'])
            deleted_catalogues = set(last_week_data['catalogues'].keys()) - catalogue_set
            for catalogue_id in deleted_catalogues:
                data = last_week_data['catalogues'][catalogue_id]
                data['is_deleted'] = True
                data['task_topics'] = []
                catalogue_data_dict[catalogue_id] = data

            # 删除的任务添加到整个数据
            topic_set = set(gantt_tasks.values_list('id', flat=True))
            deleted_topics = set(last_week_data['topics'].keys()) - topic_set

            for delete_topic_id in deleted_topics:
                topic_data = deepcopy(last_week_data['topics'][delete_topic_id])
                topic_data['is_deleted'] = True
                if topic_data['catalogue']:
                    catalogue_id = topic_data['catalogue']['id']
                    if catalogue_id in catalogue_data_dict:
                        catalogue_data_dict[catalogue_id]['task_topics'].append(topic_data)
            catalogues_data = list(catalogue_data_dict.values())
        # 将所有的任务里插入上周数据
        for catalogue_index, catalogue in enumerate(catalogues_data):
            for topic_index, topic in enumerate(catalogue['task_topics']):
                topic_data = catalogues_data[catalogue_index]['task_topics'][topic_index]
                topic_data['last_week_data'] = None
                if topic['id'] in last_week_data['topics']:
                    topic_data['last_week_data'] = deepcopy(last_week_data['topics'][topic['id']])
    return catalogues_data


@api_view(['GET'])
def my_gantt_chart_tasks(request):
    params = request.GET
    user = request.user
    gantt_roles = user.gantt_roles.all()

    role_ids = gantt_roles.values_list('id', flat=True)
    project_ids = Project.ongoing_projects().values_list('id', flat=True)
    task_topics = GanttTaskTopic.objects.filter(role_id__in=role_ids, gantt_chart__project_id__in=project_ids)

    group_type = params.get('group_type') in ['1', 'true', 'True', 1, True]
    this_week = params.get('this_week') in ['1', 'true', 'True', 1, True]

    is_done = None
    if "is_done" in params:
        is_done = params['is_done'] in {'true', '1', 'True', 1, True}

    if is_done is not None:
        task_topics = task_topics.filter(is_done=is_done)

    if this_week:
        week_end = this_week_end()
        task_topics = task_topics.filter(start_time__lte=week_end)

    total = task_topics.count()
    if is_done is False and group_type:
        tasks_data = {}
        today_date = timezone.now().date()
        expired_tasks = task_topics.filter(expected_finish_time__lt=today_date).order_by(
            'expected_finish_time')

        ongoing_tasks = task_topics.filter(start_time__lte=today_date, expected_finish_time__gte=today_date).order_by(
            'expected_finish_time')
        future_tasks = task_topics.filter(start_time__gt=today_date).order_by('expected_finish_time')

        tasks_data['expired_tasks'] = GanttTaskTopicSerializer(expired_tasks, many=True).data
        tasks_data['ongoing_tasks'] = GanttTaskTopicSerializer(ongoing_tasks, many=True).data
        tasks_data['future_tasks'] = GanttTaskTopicSerializer(future_tasks, many=True).data
        tasks_data['total'] = total

        return Response({"result": True, 'data': tasks_data})

    if is_done is True:
        task_topics = task_topics.order_by('-done_at')
    elif is_done is False:
        task_topics = task_topics.order_by('expected_finish_time')

    topics_data = GanttTaskTopicSerializer(task_topics, many=True).data
    return Response({"result": True, 'data': topics_data})


class ClientCalendarList(APIView):
    def get(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        calendars = project.calendars.order_by('-created_at')
        data = ClientCalendarSimpleSerializer(calendars, many=True).data
        return Response({"result": True, 'data': data})

    def post(self, request, project_id, action):
        project = get_object_or_404(Project, pk=project_id)
        request_data = deepcopy(request.data)
        request_data['project'] = project.id
        request_data['creator'] = request.user.id
        request_data['uid'] = gen_uuid()
        request_data['is_public'] = False
        stages = ClientCalendar.STAGES
        for field_name in stages:
            request_data[field_name] = str(request_data.get(field_name, []))
        serializer = ClientCalendarSerializer(data=request_data)
        if serializer.is_valid():
            if action == 'create':
                calendar = serializer.save()
                Log.build_create_object_log(request.user, calendar, calendar.project)
            elif action == 'preview':
                calendar = serializer.save_to_cache(serializer.validated_data)
            else:
                return Response({"result": False, 'message': 'action参数不正确'})
            data = get_client_calendar_serializer_data(calendar)
            return Response({'result': True, 'data': data})
        return Response({"result": False, 'message': str(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)


# 项目最近的日程计划
@api_view(['GET'])
def project_last_calendar(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    calendars = project.calendars.order_by('-created_at')
    if not calendars.exists():
        return Response({"result": False, 'data': None, 'message': '项目没有日程计划数据'})
    data = get_client_calendar_serializer_data(calendars.first())
    return Response({"result": True, 'data': data})


class ClientCalendarDetail(APIView):
    def get(self, request, uid, type):
        if type == 'view':
            calendar = get_object_or_404(ClientCalendar, uid=uid)
        elif type == 'preview':
            calendar = cache.get('calendar' + uid)
            if not calendar:
                return Response({"result": False, 'message': '预览数据不存在'},
                                status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({"result": False, 'message': 'type参数不正确'})

        data = get_client_calendar_serializer_data(calendar)

        return Response({"result": True, 'data': data})

    def post(self, request, project_id, uid, action):
        calendar = get_object_or_404(ClientCalendar, uid=uid, project_id=project_id)
        origin = deepcopy(calendar)
        request_data = deepcopy(request.data)
        request_data['project'] = project_id
        request_data['uid'] = uid
        stages = ClientCalendar.STAGES
        for field_name in stages:
            request_data[field_name] = str(request_data.get(field_name, []))
        serializer = ClientCalendarSerializer(calendar, data=request_data)
        if serializer.is_valid():
            if action == 'edit':
                calendar = serializer.save()
                Log.build_update_object_log(request.user, origin, calendar, calendar.project)
            elif action == 'preview':
                calendar = serializer.update_to_cache(calendar, serializer.validated_data)
            else:
                return Response({"result": False, 'message': 'action参数不正确'})
            data = get_client_calendar_serializer_data(calendar)
            return Response({'result': True, 'data': data})
        return Response({"result": False, 'message': str(serializer.errors)})

    def delete(self, request, project_id, uid):
        calendar = get_object_or_404(ClientCalendar, uid=uid, project_id=project_id)
        origin = deepcopy(calendar)
        if request.user.id != calendar.project.manager_id:
            return Response({"result": False, 'message': '只有项目项目经理或管理员可以删除日历'})
        calendar.delete()
        Log.build_delete_object_log(request.user, origin, related_object=origin.project)
        return Response({"result": True})


def get_client_calendar_serializer_data(calendar):
    serializer = ClientCalendarReadOnlySerializer(calendar)
    data = serializer.data
    for field_name in ClientCalendar.STAGES:
        if field_name in data and data[field_name]:
            date_list = ast.literal_eval(data[field_name])
            data[field_name] = date_list
    return data


def change_gitlab_datetime_str(datetime_str):
    if '+08:00' in datetime_str:
        datetime_str = datetime.strptime(
            datetime_str,
            "%Y-%m-%dT%H:%M:%S.%f+08:00").strftime(
            settings.DATETIME_FORMAT)
    elif datetime_str.endswith('Z'):
        datetime_str = (
                datetime.strptime(datetime_str,
                                  "%Y-%m-%dT%H:%M:%S.%fZ") + timedelta(
            hours=8)).strftime(settings.DATETIME_FORMAT)
    return datetime_str


@api_view(['GET'])
def my_ongoing_projects_demo_status(request):
    projects = Project.ongoing_projects().filter(manager_id=request.user.id)
    farm_projects_demo_status = cache.get('farm_projects_demo_status', {})
    if not farm_projects_demo_status:
        farm_projects_demo_status = crawl_farm_projects_recent_half_hour_git_demo_commits()
    projects_data = []
    for project in projects:
        if project.id in farm_projects_demo_status:
            project_data = {"id": project.id, "name": project.name,
                            'demo_status': farm_projects_demo_status[project.id]}
            # 测试
            # project_data['demo_status']['need_alert'] = True
            last_commit = project_data['demo_status']['last_commit']
            if last_commit:
                last_commit['created_at'] = change_gitlab_datetime_str(last_commit['created_at'])
            projects_data.append(project_data)

    def demo_status_sort_key(data):
        demo_status = data['demo_status']
        status_code = 1 if demo_status['status'] == 'maintaining' else 0
        last_commit_created_at = demo_status['last_commit']['created_at'] if demo_status['last_commit'] else ''
        return status_code, last_commit_created_at

    result_data = sorted(projects_data, key=demo_status_sort_key, reverse=True)
    return Response({"result": True, 'message': '', 'data': result_data})


class ProjectDemoStatus(APIView):
    def get(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        project_links = ProjectLinks.objects.filter(project_id=project_id)
        if not project_links.exists():
            return Response({"result": False, 'message': "未绑定gitlab项目"}, status=status.HTTP_400_BAD_REQUEST)

        git_group = project.links.gitlab_group_id
        git_project = project.links.gitlab_project_id
        if not any([git_group, git_project]):
            return Response({"result": False, 'message': "未绑定gitlab项目"}, status=status.HTTP_400_BAD_REQUEST)

        farm_projects_demo_status = cache.get('farm_projects_demo_status', {})
        if not farm_projects_demo_status:
            farm_projects_demo_status = crawl_farm_project_recent_half_hour_git_demo_commits(project.id)
        demo_status = farm_projects_demo_status.get(project.id)
        project_data = {"id": project.id, "name": project.name,
                        'demo_status': demo_status}
        last_commit = project_data['demo_status']['last_commit']
        if last_commit:
            last_commit['created_at'] = change_gitlab_datetime_str(last_commit['created_at'])
        return Response({"result": True, 'data': project_data})

    def post(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        demo_status = request.data.get('status')
        demo_status_display = "维护中" if demo_status == 'maintaining' else "正常"
        if demo_status not in ['normal', 'maintaining']:
            return Response({"result": False, 'message': "status为必填，可选值为'normal、'maintaining'"},
                            status=status.HTTP_400_BAD_REQUEST)
        project_links = ProjectLinks.objects.filter(project_id=project_id)
        if not project_links.exists():
            return Response({"result": False, 'message': "未绑定gitlab项目"}, status=status.HTTP_400_BAD_REQUEST)

        gitlab_group_id = project.links.gitlab_group_id
        gitlab_project_id = project.links.gitlab_project_id
        if not any([gitlab_group_id, gitlab_project_id]):
            return Response({"result": False, 'message': "未绑定gitlab项目"}, status=status.HTTP_400_BAD_REQUEST)

        farm_projects_demo_status = cache.get('farm_projects_demo_status', {})
        if not farm_projects_demo_status:
            farm_projects_demo_status = crawl_farm_project_recent_half_hour_git_demo_commits(project.id)

        farm_project_demo_status = farm_projects_demo_status.get(project.id)

        farm_project_demo_status['status'] = demo_status
        farm_project_demo_status['need_alert'] = False
        farm_project_demo_status["modified_at"] = datetime.now().strftime(settings.DATETIME_FORMAT)
        farm_projects_demo_status[project_id] = deepcopy(farm_project_demo_status)
        cache.set('farm_projects_demo_status', farm_projects_demo_status, None)
        comment = '项目Demo应用状态改为' + demo_status_display
        Log.build_update_object_log(request.user, project, project, comment="项目Demo应用状态改为 " + comment)
        return Response({"result": True, 'message': ''})


@api_view(['GET'])
def daily_works_projects(request):
    if has_function_perm(request.user, 'view_all_ongoing_projects_developers_daily_works'):
        result_projects = Project.ongoing_projects()
    elif has_function_perm(request.user, 'view_my_ongoing_projects_developers_daily_works'):
        projects = Project.ongoing_projects()
        result_projects = get_user_projects(request.user, projects)
    else:
        return api_permissions_required()
    result_projects = result_projects.distinct().order_by('created_at')
    data = ProjectWithDeveloperListSerializer(result_projects, many=True).data
    return api_success(data=data)


@api_view(['GET'])
def daily_works_projects_recent_unread_dict(request):
    if has_function_perm(request.user, 'view_all_ongoing_projects_developers_daily_works'):
        result_projects = Project.ongoing_projects()
    elif has_function_perm(request.user, 'view_my_ongoing_projects_developers_daily_works'):
        projects = Project.ongoing_projects()
        result_projects = get_user_projects(request.user, projects)
    else:
        return api_permissions_required()

    projects_recent_unread_dict = {}
    result_projects = result_projects.distinct().order_by('created_at')
    # 遍历项目
    for project in result_projects:
        recent_unread_num = 0
        developers_data = {}

        # 遍历项目的日报
        daily_works = project.daily_works.exclude(status="pending").filter(
            day__gt=timezone.now().date() + timedelta(days=-7))
        for daily_work in daily_works:
            if not daily_work.browsing_histories.filter(visitor_id=request.user.id).exists():
                recent_unread_num += 1
                developer = daily_work.developer
                if developer:
                    day_str = daily_work.day.strftime(settings.DATE_FORMAT)
                    developer_id = developer.id
                    if developer_id not in developers_data:
                        developers_data[developer_id] = {"id": developer.id, 'name': developer.name, 'days': []}
                    developer_data_days = developers_data[developer_id]['days']
                    if day_str not in developer_data_days:
                        developer_data_days.append(day_str)

        projects_recent_unread_dict[project.id] = {"id": project.id, "name": project.name,
                                                   "recent_unread_num": recent_unread_num,
                                                   "developers_data": developers_data}

    return api_success(data=projects_recent_unread_dict)


from farmbase.tasks import crawl_quip_projects_folders, rebuild_bound_quip_projects_folders, \
    crawl_quip_projects_engineer_folders, rebuild_bound_quip_projects_engineer_folders


@api_view(['GET', ])
def quip_folders(request):
    folders_dict = cache.get('quip_projects_folders', None)
    # bound_quip_folders = cache.get("bound_quip_projects_folders", set())
    if folders_dict is None:
        folders_dict = crawl_quip_projects_folders()
    else:
        crawl_quip_projects_folders.delay()

    # if not bound_quip_folders:
    #     bound_quip_folders = rebuild_bound_quip_projects_folders()
    # else:
    #     rebuild_bound_quip_projects_folders.delay()

    folders = []
    for folder_key in folders_dict:
        folder_data = folders_dict[folder_key]
        folders.append(deepcopy(folder_data["folder"]))
        # if folder_key not in bound_quip_folders:
        #     folders.append(deepcopy(folder_data["folder"]))
    folder_list = sorted(folders, key=lambda x: x['created_usec'], reverse=True)
    return api_success(data=folder_list)


@api_view(['GET', ])
def quip_engineer_folders(request):
    folders_dict = cache.get('quip_projects_engineer_folders', None)
    # bound_quip_folders = cache.get("bound_quip_projects_engineer_folders", set())
    if folders_dict is None:
        folders_dict = crawl_quip_projects_engineer_folders()
    else:
        crawl_quip_projects_engineer_folders.delay()

    # if not bound_quip_folders:
    #     bound_quip_folders = rebuild_bound_quip_projects_engineer_folders()
    # else:
    #     rebuild_bound_quip_projects_engineer_folders.delay()

    folders = []
    for folder_key in folders_dict:
        folder_data = folders_dict[folder_key]
        folders.append(deepcopy(folder_data["folder"]))
        # if folder_key not in bound_quip_folders:
        #     folders.append(deepcopy(folder_data["folder"]))
    folder_list = sorted(folders, key=lambda x: x['created_usec'], reverse=True)
    return api_success(data=folder_list)


@api_view(['GET', ])
def quip_folder_children_folders(request, folder_id):
    from oauth.quip_utils import get_project_quip_folder_template
    template = get_project_quip_folder_template()
    template_folder_titles = set()
    if 'children' in template:
        for child in template['children']:
            if 'folder' in child:
                folder_title = child['folder']['title']
                template_folder_titles.add(folder_title)

    folders_dict = cache.get('quip_folder_children_folders', {})
    folder_dict = folders_dict.get(folder_id, None)
    if folder_dict:
        crawl_quip_folder_children_folders_to_cache.delay(folder_id)
    else:
        folder_dict = crawl_quip_folder_children_folders_to_cache(folder_id)
    folders = []
    if folder_dict:
        for folder_key in folder_dict:
            folder_data = folder_dict[folder_key]
            folder = folder_data["folder"]
            if folder['title'] not in template_folder_titles:
                folders.append(deepcopy(folder))
    folder_list = sorted(folders, key=lambda x: x['created_usec'], reverse=True)
    return api_success(data=folder_list)


@api_view(['GET'])
def projects_data_migrate(request):
    roles = GanttRole.objects.all()
    for role in roles:
        role.rebuild_role_type_user_developer()
    return api_success()


class ProjectWorkHourPlanList(APIView):
    def get(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        project_work_hour_plans = project.project_work_hour_plans.order_by("created_at")
        role = request.GET.get('role', '')
        if role:
            project_work_hour_plans = project_work_hour_plans.filter(role=role)
        data = ProjectWorkHourPlanSerializer(project_work_hour_plans, many=True).data
        return api_success(data)

    @transaction.atomic
    def post(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        work_hour_plans = request.data.get('work_hour_plans', '')
        remarks = request.data.get('remarks', '')
        # 存下来原来的id集合
        origin_ids = set(project.project_work_hour_plans.values_list('id', flat=True))
        now = timezone.now()
        # 新的阶段的id集合
        savepoint = transaction.savepoint()
        now_ids = set()
        for work_hour_data in work_hour_plans:
            if 'id' in work_hour_data:
                now_ids.add(work_hour_data['id'])

        role_member_set = set()
        for p in work_hour_plans:
            p['user'] = p.get('user', None)
            p['developer'] = p.get('developer', None)
            key = (p['role'], p['user'], p['developer'])
            if key in role_member_set:
                return api_bad_request('职位+人员不能出现重复的')
            role_member_set.add(key)

        deleted_ids = list(origin_ids - now_ids)
        for delete_id in deleted_ids:
            project_work_hour_plan = ProjectWorkHourPlan.objects.filter(pk=delete_id).first()
            if project_work_hour_plan.elapsed_time:
                transaction.savepoint_rollback(savepoint)
                return api_bad_request('已有耗时的成员不可被删除')
            project_work_hour_plan.delete()

        for work_hour_data in work_hour_plans:
            work_hour_data['project'] = project_id
            serializer = ProjectWorkHourPlanCreateSerializer(data=work_hour_data)
            origin_work_hour_plan = None
            if 'id' in work_hour_data:
                work_hour_old = ProjectWorkHourPlan.objects.filter(id=work_hour_data['id']).first()
                if not work_hour_old:
                    transaction.savepoint_rollback(savepoint)
                    return api_bad_request('工时计划不存在')
                if work_hour_old.elapsed_time:
                    if (work_hour_old.developer and work_hour_old.developer.id != work_hour_data['developer']) or (
                            work_hour_old.user and work_hour_old.user.id != work_hour_data['user']):
                        transaction.savepoint_rollback(savepoint)
                        return api_bad_request('不能修改已有耗时的工时计划成员')
                origin_work_hour_plan = deepcopy(work_hour_old)
                serializer = ProjectWorkHourPlanEditSerializer(work_hour_old, data=work_hour_data)
            if serializer.is_valid():
                work_hour_plan = serializer.save()
                if origin_work_hour_plan:
                    origin_plan_consume_days = origin_work_hour_plan.plan_consume_days
                    if origin_plan_consume_days != work_hour_data['plan_consume_days']:
                        ProjectWorkHourOperationLog.build_log(work_hour_plan, request.user, 'edit', remarks,
                                                              origin_plan_consume_days=origin_plan_consume_days,
                                                              new_plan_consume_days=work_hour_plan.plan_consume_days,
                                                              created_at=now)
                else:
                    ProjectWorkHourOperationLog.build_log(work_hour_plan, request.user, 'create', remarks,
                                                          origin_plan_consume_days=None,
                                                          new_plan_consume_days=work_hour_plan.plan_consume_days,
                                                          created_at=now)
            else:
                transaction.savepoint_rollback(savepoint)
                return api_bad_request(str(serializer.errors))
        return api_success()


class WorkHourRecordList(APIView):
    @transaction.atomic
    def post(self, request, project_id):
        savepoint = transaction.savepoint()
        work_hour_record_list = request.data.get('work_hour_records', '')
        statistic_start_date = request.data.get('statistic_start_date', '')
        statistic_end_date = request.data.get('statistic_end_date', '')
        for work_hour_record in work_hour_record_list:
            work_hour_record['statistic_start_date'] = statistic_start_date
            work_hour_record['statistic_end_date'] = statistic_end_date
            project_work_hour_plan = get_object_or_404(ProjectWorkHourPlan,
                                                       pk=work_hour_record['project_work_hour_plan'])
            work_hour_record_old = WorkHourRecord.objects.filter(
                statistic_start_date=statistic_start_date,
                statistic_end_date=statistic_end_date, project_work_hour_plan=project_work_hour_plan).first()
            week_consume_days = work_hour_record['week_consume_hours'] / 8
            week_consume_days = float(Decimal(week_consume_days).quantize(Decimal("0.1"), rounding="ROUND_HALF_UP"))
            if work_hour_record_old:
                serializer = WorkHourRecordEditSerializer(work_hour_record_old, data=work_hour_record)
                old_week_consume_days = work_hour_record_old.week_consume_hours / 8
                old_week_consume_days = float(
                    Decimal(old_week_consume_days).quantize(Decimal("0.1"), rounding="ROUND_HALF_UP"))
                project_work_hour_plan.elapsed_time = project_work_hour_plan.elapsed_time - old_week_consume_days + week_consume_days
            else:
                serializer = WorkHourRecordCreateSerializer(data=work_hour_record)
                project_work_hour_plan.elapsed_time += week_consume_days
            if serializer.is_valid():
                work_hour_record = serializer.save()
                work_hour_record.modified_at = timezone.now()
                work_hour_record.save()
                project_work_hour_plan.save()
            else:
                transaction.savepoint_rollback(savepoint)
                return api_bad_request(str(serializer.errors))
        return api_success()


@api_view(['GET'])
def get_project_work_hour_statistic_data(request):
    params = request.GET
    projects = Project.ongoing_projects()
    search = params.get('search_value', '')
    if search:
        projects = projects.filter(name__icontains=search)
    group_bys = {'manager', 'product_manager', 'tpm', 'designer', 'test', 'developer'}
    group_by = params.get('group_by', 'manager')
    if group_by not in group_bys:
        return api_bad_request("分组可用字段：".format(','.join(group_bys)))
    project_group_dict = {}
    role_null_data = {'user': None, 'projects': []}
    projects_data = ProjectWithWorkHourPlanSerializer(projects, many=True).data
    group_by_test = group_by == 'test'
    for project_data in projects_data:
        if group_by_test:
            tests = project_data['members_dict'].get("tests", None)
            if not tests:
                role_null_data['projects'].append(project_data)
                continue
            for test in tests:
                group_role_username = test['username']
                if group_role_username not in project_group_dict:
                    project_group_dict[group_role_username] = {'user': test, 'projects': []}
                project_group_dict[group_role_username]['projects'].append(project_data)
        else:
            group_role = project_data['members_dict'].get(group_by, None)
            if not group_role:
                role_null_data['projects'].append(project_data)
                continue
            group_role_username = group_role['username']
            if group_role_username not in project_group_dict:
                project_group_dict[group_role_username] = {'user': group_role, 'projects': []}
            project_group_dict[group_role_username]['projects'].append(project_data)
    result_data = []
    sorted_username = sorted(project_group_dict.keys(), key=lambda x: ''.join(lazy_pinyin(x)))
    for username in sorted_username:
        data = deepcopy(project_group_dict[username])
        data['projects'] = sorted(data['projects'], key=lambda x: (x['start_date'], x['created_at']))
        result_data.append(data)

    if role_null_data['projects']:
        data = deepcopy(role_null_data)
        data['projects'] = sorted(data['projects'], key=lambda x: (x['start_date'], x['created_at']))
        result_data.append(data)
    return api_success(result_data)


@api_view(['GET'])
def get_project_work_hour_operation_log(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    work_hour_plan_logs = ProjectWorkHourOperationLog.objects.filter(project_work_hour__project=project).order_by(
        '-created_at')
    project_work_hour_plan_operation_logs_data = ProjectWorkHourOperationLogSerializer(
        work_hour_plan_logs, many=True).data
    logs_data = {}
    for project_work_hour_plan_operation_log in project_work_hour_plan_operation_logs_data:
        created_at = project_work_hour_plan_operation_log['created_at']
        if created_at not in logs_data:
            logs_data[created_at] = {"date": created_at, "data": []}
        logs_data[created_at]['data'].append(project_work_hour_plan_operation_log)
    data = sorted(logs_data.values(), key=lambda x: x['date'], reverse=True)
    return api_success(data)
