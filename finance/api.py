import os
import time
from copy import deepcopy
from datetime import datetime, timedelta
import re
import json
from wsgiref.util import FileWrapper
from collections import Counter

import json_tools
import requests
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models import Sum, IntegerField, When, Case, Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404, reverse
from django.core.files import File as DjangoFile
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from django.utils.decorators import method_decorator
from django.utils.encoding import escape_uri_path
from django.utils.http import urlquote
from docx import Document
from docx.shared import Inches, RGBColor, Pt

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from developers.models import Developer
from gearfarm.utils.base64_to_image_file import base64_string_to_file
from files.models import File
from files.utils import handle_obj_files
from finance.tasks import create_job_contract_docx_pdf_files, create_confidentiality_agreement_docx_pdf_files
from gearfarm.settings import LEGAL_PERSONNEL
from gearfarm.utils.common_utils import get_protocol_host, format_currency, gen_uuid, get_file_suffix, this_week_end, \
    clean_text
from gearfarm.utils.farm_response import api_success, api_bad_request, api_permissions_required, \
    build_pagination_response, api_request_params_required, build_pagination_queryset_data
from gearfarm.utils import farm_response
from farmbase.user_utils import get_user_projects, in_group
from farmbase.users_undone_works_utils import get_user_developers_regular_contracts_undone_work_count
from finance.models import JobPayment, ProjectPayment, ProjectPaymentStage, JobContract
from finance.serializers import JobPaymentBoardSerializer, JobPaymentRetrieveSerializer, JobPaymentListSerializer, \
    JobPaymentEditSerializer, \
    JobPaymentCreateSerializer, ProjectWithPaymentSerializer, \
    ProjectPaymentCreateSerializer, ProjectPaymentEditSerializer, ProjectPaymentSerializer, \
    ProjectPaymentStageSerializer, ProjectPaymentStageCreateSerializer, ProjectPaymentStageEditSerializer, \
    ProjectPaymentStageReceiptedSerializer, ProjectPaymentStageExpectedDateSerializer, JobContractCreateSerializer, \
    JobContractEditSerializer, JobContractRedactSerializer, DeveloperContractSerializer, \
    JobDesignContractCreateSerializer, JobDesignContractEditSerializer, JobContractDetailSerializer, \
    JobContractListSerializer, JobContractSerializer, JobContractEditSerializer, JobContractRedactSerializer, \
    DeveloperContractSerializer, JobContractRegularListSerializer, JobRegularContractCreateSerializer, \
    JobRegularContractRedactSerializer
from logs.api import get_paginate_queryset
from logs.models import Log
from logs.utils import get_field_value
from oauth.e_sign import ESign
from projects.models import JobPosition, Project
from projects.serializers import JobWithPaymentsSerializer
from finance.utils import send_payment_notification, word_to_pdf, content_encoding, find_sign_location
from farmbase.permissions_utils import has_function_perm, func_perm_required
from notifications.utils import create_notification, create_notification_group, create_notification_to_users
from notifications.notification_factory import NotificationFactory


class JobPaymentList(APIView):
    # 所有打款项 默认排除记录状态
    def get(self, request, format=None):
        params = request.GET
        queryset = JobPayment.objects.exclude(status=0).order_by('status', '-expected_at')
        filter_date = params.get('date', None)
        status = params.get('status', None)
        group_by = params.get('group_by', None)

        if status:
            queryset = queryset.filter(status=status)
        if filter_date and filter_date == 'this_week':
            week_end = this_week_end()
            queryset = queryset.filter(expected_at__lte=week_end)
        # 本周打款是分组
        if filter_date == 'this_week' and not group_by:
            group_by = "manager"
        data, headers = build_pagination_queryset_data(request, queryset, JobPaymentBoardSerializer)
        if group_by == "manager":
            group_data = {}
            for payment in data:
                manager = payment['manager']
                if manager["id"] not in group_data:
                    group_data[manager["id"]] = {
                        'payments': [],
                        'manager': deepcopy(manager)
                    }
                group_data[manager["id"]]['payments'].append(payment)
            data = group_data.values()
        return api_success(data=data, headers=headers)


class JobPositionPayments(APIView):
    def get(self, request, position_id):
        job_position = get_object_or_404(JobPosition, pk=position_id)
        serializer = JobWithPaymentsSerializer(job_position)
        return Response({"result": True, "data": serializer.data})

    def post(self, request, position_id):
        job_position = get_object_or_404(JobPosition, pk=position_id)
        project = job_position.project
        developer = job_position.developer
        job_contract = None
        job_contract_id = request.data.get('job_contract', '')
        if job_contract_id:
            job_contract = get_object_or_404(JobContract, pk=job_contract_id)
        return handle_developer_payment_create(request, developer, job_contract, job_position, project)


class JobPaymentDetail(APIView):
    def get(self, request, id):
        payment = get_object_or_404(JobPayment, pk=id)
        serializer = JobPaymentRetrieveSerializer(payment)
        return Response(serializer.data)

    def post(self, request, id):
        payment = get_object_or_404(JobPayment, pk=id)
        if payment.status != 0:
            message = '该工程师打款不处在记录状态，当前状态为{},不能编辑信息'.format(payment.status_display)
            return api_bad_request(message)
        # 项目职位打款
        if payment.project:
            project = payment.project
            is_mine = has_function_perm(request.user,
                                        'manage_my_project_job_positions') and request.user in project.members
            has_perm = is_mine or has_function_perm(request.user, 'manage_all_project_job_positions')
            if not has_perm:
                return api_permissions_required('你没有权限编辑工程师打款，请联系项目的项目经理、或管理员')
        request.data['name'] = payment.developer.name
        origin = deepcopy(payment)
        serializer = JobPaymentEditSerializer(payment, data=request.data)
        if serializer.is_valid():
            if payment.job_contract:
                payment_amount = payment.amount
                remaining_amount = payment.job_contract.remaining_payment_amount + payment_amount
                if remaining_amount - float(request.data['amount']) < 0:
                    return api_bad_request("打款金额超过剩余额度")
            payment = serializer.save()
            if payment.project:
                Log.build_update_object_log(request.user, origin, payment, related_object=payment.position.project)
                Log.build_update_object_log(request.user, origin, payment, related_object=payment.position)
            if payment.job_contract:
                Log.build_update_object_log(request.user, origin, payment, related_object=payment.job_contract)
            Log.build_update_object_log(request.user, origin, payment)
            return api_success(serializer.data)
        return api_bad_request(serializer.errors)

    def delete(self, request, id):
        payment = get_object_or_404(JobPayment, pk=id)
        if payment.status != 0:
            message = '该打款不处在记录状态，当前状态为{},不能删除'.format(payment.status_display)
            return api_bad_request(message)
        project = payment.project
        if project:
            is_mine = has_function_perm(request.user,
                                        'manage_my_project_job_positions') and request.user in project.members
            has_perm = is_mine or has_function_perm(request.user, 'manage_all_project_job_positions')
            if not has_perm:
                return api_permissions_required('你没有权限编辑工程师打款，请联系项目的项目经理、或管理员')
        origin = deepcopy(payment)
        payment.delete()
        if project:
            Log.build_delete_object_log(request.user, origin, project)
            Log.build_delete_object_log(request.user, origin, origin.position)
        if payment.job_contract:
            Log.build_delete_object_log(request.user, origin, payment.job_contract)
        return api_success()


@api_view(['POST'])
def change_payment_status(request, payment_id, action_type):
    payment = get_object_or_404(JobPayment, pk=payment_id)

    # 操作判断
    allowed_actions = []
    status_dict = JobPayment.STATUS_ACTIONS_DICT
    if payment.status in status_dict:
        allowed_actions = list(status_dict[payment.status]['actions'].keys())
    if action_type not in allowed_actions:
        return api_bad_request('该打款当前状态为{},不能进行该操作'.format(payment.status_display))

    project = payment.project
    origin = deepcopy(payment)

    # 权限判断
    if not request.user.is_superuser:
        if action_type == 'start':
            if project:
                is_mine = has_function_perm(request.user,
                                            'manage_my_project_job_positions') and request.user in project.members
                has_perm = is_mine or has_function_perm(request.user, 'manage_all_project_job_positions')
                if not has_perm:
                    return api_permissions_required('你没有权限编辑工程师打款，请联系项目的项目经理、或管理员')
            else:
                if not has_function_perm(request.user, 'finance.manage_regular_developer_contract_payments'):
                    return api_permissions_required()
        else:
            if not has_function_perm(request.user, 'handle_all_developer_payments'):
                return api_permissions_required()
    # 状态变更：
    if action_type == 'start':
        payment.start_at = timezone.now()
    else:
        payment.completed_at = timezone.now().date()
    payment.status = status_dict[payment.status]["actions"][action_type]['result_status']
    payment.save()
    if action_type == 'finish':
        if payment.job_contract:
            payment.job_contract.save()
    if project:
        Log.build_update_object_log(request.user, origin, payment, related_object=payment.position.project)
        Log.build_update_object_log(request.user, origin, payment, related_object=payment.position)
    if payment.job_contract:
        Log.build_update_object_log(request.user, origin, payment, related_object=payment.job_contract)
    NotificationFactory.build_job_payment_notifications(payment, request.user)
    data = JobPaymentListSerializer(payment).data
    return api_success(data)


@api_view(['GET'])
def projects_payments(request, is_mine):
    projects = Project.objects.all()
    if is_mine:
        projects = get_user_projects(request.user, projects, members=['manager', 'mentor', 'bd'])

    projects = projects.filter(project_payments__isnull=False).distinct()
    main_status = request.GET.get('main_status', None)
    # 近期收款的项目：    项目中包含进行中收款、 项目未完成
    if main_status == 'ongoing':
        projects = projects.filter(
            Q(project_payments__status='process') | Q(done_at__isnull=True)).distinct().order_by(
            'created_at')
    # 完成收款的项目：    项目已完成 且 项目中不包含进行中收款
    elif main_status == 'closed':
        projects = projects.filter(done_at__isnull=False).exclude(
            project_payments__status='process').distinct().order_by('-created_at')

    search_value = request.GET.get('search_value', None)
    page = request.GET.get('page', None)
    page_size = request.GET.get('page_size', None)
    if search_value:
        projects = projects.filter(
            Q(name__icontains=search_value) | Q(manager__username__icontains=search_value))

    return build_pagination_response(request, projects, ProjectWithPaymentSerializer)


class ProjectPaymentList(APIView):
    def get(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        payments = project.project_payments.order_by('created_at')
        data = ProjectPaymentSerializer(payments, many=True).data
        return api_success(data)

    def post(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        request.data["project"] = project.id
        serializer = ProjectPaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        total_amount = validated_data.get('total_amount', None)
        if not total_amount:
            return api_bad_request("总金额必填")
        if not isinstance(total_amount, (int, float)):
            return api_bad_request("总金额格式有误")
        stages_total_amount = 0
        stages_data = request.data.get('stages', [])
        for stage_data in stages_data:
            receivable_amount = stage_data.get('receivable_amount', None)
            if not receivable_amount:
                return api_bad_request("每个阶段应收款必填")
            if not isinstance(receivable_amount, (int, float)):
                return api_bad_request("应收款金额格式有误")
            stages_total_amount += receivable_amount
        if total_amount != stages_total_amount:
            return api_bad_request('各阶段应收款金额加起来必须等于总金额')
        try:
            with transaction.atomic():
                payment = serializer.save()
                for index, stage_data in enumerate(stages_data):
                    stage_data['project_payment'] = payment.id
                    stage_data['index'] = index
                    stage_serializer = ProjectPaymentStageCreateSerializer(data=stage_data)
                    stage_serializer.is_valid(raise_exception=True)
                    stage = stage_serializer.save()
                    print(stage.id)
        except Exception as e:
            return api_bad_request(str(e))

        Log.build_create_object_log(request.user, payment, payment.project)
        Log.build_create_object_log(request.user, payment, payment)
        notification_content = '项目【{}】添加了一份新的收款合同【{}】'.format(payment.project.name, payment.contract_name)
        if request.user != payment.project.manager:
            project_url = get_protocol_host(request) + '/projects/{}/?anchor=myProjectPay'.format(project.id)
            create_notification(payment.project.manager, notification_content, project_url)
        projects_payments_url = get_protocol_host(request) + '/finance/projects/payments/'
        create_notification_group(settings.GROUP_NAME_DICT["finance"], notification_content, projects_payments_url)
        return api_success(serializer.data)


def user_edit_project_payment_permission(user, payment):
    if user.is_superuser:
        return True
    project = payment.project
    if user.id in [project.manager_id, project.mentor_id]:
        return True
    return False


class ProjectPaymentDetail(APIView):
    def get(self, request, payment_id):
        payment = get_object_or_404(ProjectPayment, pk=payment_id)
        serializer = ProjectPaymentSerializer(payment)
        return api_success(serializer.data)

    def put(self, request, payment_id):
        '''
           在合同未收款前，可以编辑合同全部内容
           合同名称、付款账号/公司、是否需要发票 这三项 任何时候都能编辑
           合同已收到款, 合同总额 和 已收款项不能修改
        '''
        payment = get_object_or_404(ProjectPayment, pk=payment_id)
        if not user_edit_project_payment_permission(request.user, payment):
            return api_bad_request("只有本项目的项目经理，导师有权限编辑项目收款")
        if payment.status != 'process':
            return api_bad_request("合同{}, 不能编辑".format(payment.status_display))
        origin = deepcopy(payment)
        serializer = ProjectPaymentEditSerializer(payment, data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        total_amount = validated_data.get('total_amount', None)
        if not total_amount:
            return api_bad_request("总金额必填")
        if not isinstance(total_amount, (int, float)):
            return api_bad_request("总金额格式有误")

        paid_stage_count = payment.paid_stage_count
        if paid_stage_count:
            if total_amount != payment.total_amount:
                return api_bad_request("合同已收到款, 合同总额不能修改")

        origin_stage_ids = set([stage.id for stage in payment.stages.all()])
        paid_stages = payment.paid_stages
        paid_stage_ids = set()
        for stage in paid_stages:
            paid_stage_ids.add(stage.id)

        stages_total_amount = 0
        stages_data = request.data.get('stages', [])
        new_stage_ids = set()
        for stage_data in stages_data:
            stage_id = stage_data.get('id', None)
            receivable_amount = stage_data.get('receivable_amount', None)
            if stage_id:
                stage = get_object_or_404(ProjectPaymentStage, pk=stage_id, project_payment=payment.id)
                new_stage_ids.add(stage_id)
                if stage_id in paid_stage_ids:
                    if receivable_amount != stage.receivable_amount:
                        return api_bad_request("合同已收款项不能修改")
            else:
                if not receivable_amount:
                    return api_bad_request("每个阶段应收款必填")
                if not isinstance(receivable_amount, (int, float)):
                    return api_bad_request("应收款金额格式有误")
            stages_total_amount += receivable_amount
        if total_amount != stages_total_amount:
            return api_bad_request('各阶段应收款金额加起来必须等于总金额')

        if not new_stage_ids.issuperset(paid_stage_ids):
            return api_bad_request('合同已收款项不能删除')

        try:
            with transaction.atomic():
                payment = serializer.save()
                # 编辑的同时   财务操作导致完成
                if payment.status == 'completed':
                    return api_bad_request("合同已完成, 不能编辑")
                for index, stage_data in enumerate(stages_data):
                    stage_id = stage_data.get('id', None)
                    if stage_id:
                        stage = get_object_or_404(ProjectPaymentStage, pk=stage_id, project_payment=payment.id)
                        # 如果已经付款了 不能修改
                        if stage.receipted_amount:
                            stage_data = {'index': index}
                        stage_serializer = ProjectPaymentStageEditSerializer(stage, stage_data, partial=True)
                    else:
                        stage_data['project_payment'] = payment.id
                        stage_data['index'] = index
                        stage_serializer = ProjectPaymentStageCreateSerializer(data=stage_data)
                    stage_serializer.is_valid(raise_exception=True)
                    stage = stage_serializer.save()
                    new_stage_ids.add(stage.id)
                delete_ids = origin_stage_ids - new_stage_ids
                ProjectPaymentStage.objects.filter(pk__in=delete_ids).delete()
                payment.save()
        except Exception as e:
            return api_bad_request(str(e))

        Log.build_update_object_log(request.user, origin, payment)
        send_project_payment_notifications(request, origin, payment)

        return api_success()


@api_view(['POST'])
def close_project_payment(request, payment_id):
    payment = get_object_or_404(ProjectPayment, pk=payment_id)
    if not user_edit_project_payment_permission(request.user, payment):
        return api_bad_request("只有本项目的项目经理，导师有权限编辑项目收款")
    if payment.status != 'process':
        return api_bad_request("项目打款当前状态为{} 不能终止".format(payment.status_display))

    close_remarks = request.data.get('close_remarks', '')
    termination_reason = request.data.get('termination_reason', None)
    if not termination_reason:
        return api_bad_request('请填写终止原因')
    origin = deepcopy(payment)
    payment.termination_reason = termination_reason
    payment.status = 'termination'
    if close_remarks:
        payment.close_remarks = close_remarks
    payment.save()
    comment = '{} {}'.format(payment.get_termination_reason_display(), close_remarks)
    Log.build_update_object_log(request.user, origin, payment, comment=comment)
    send_project_payment_notifications(request, origin, payment, comment=comment)
    return api_success()


@api_view(['POST'])
def open_project_payment(request, payment_id):
    payment = get_object_or_404(ProjectPayment, pk=payment_id)
    if not user_edit_project_payment_permission(request.user, payment):
        return api_bad_request("只有本项目的项目经理，导师有权限编辑项目收款")
    if payment.status != 'termination':
        return api_bad_request("项目打款当前状态为{} 不能终止".format(payment.status_display))
    remarks = request.data.get('remarks')
    if not remarks:
        return api_bad_request('请填写恢复正常理由')
    origin = deepcopy(payment)
    payment.status = 'process'
    payment.save()
    Log.build_update_object_log(request.user, origin, payment, comment=remarks)
    send_project_payment_notifications(request, origin, payment, comment=remarks)
    return api_success()


class ProjectPaymentStageDetail(APIView):
    def get(self, request, stage_id):
        stage = get_object_or_404(ProjectPaymentStage, pk=stage_id)
        serializer = ProjectPaymentStageSerializer(stage)
        return api_success(serializer.data)


@api_view(['PUT'])
def project_payment_stage_expected_date(request, stage_id):
    stage = get_object_or_404(ProjectPaymentStage, pk=stage_id)
    payment = stage.project_payment
    has_permission = user_edit_project_payment_permission(request.user, payment)
    is_finance = in_group(request.user, settings.GROUP_NAME_DICT["finance"])
    if not has_permission and not is_finance:
        return api_bad_request("只有本项目的项目经理、导师 及财务有权限编辑项目收款预计日期")

    if payment.status != 'process':
        return api_bad_request("合同{}, 不能编辑".format(payment.status_display))
    if stage.receipted_amount:
        return api_bad_request("已填写收款, 无需编辑预计日期")
    origin = deepcopy(stage)
    serializer = ProjectPaymentStageExpectedDateSerializer(stage, data=request.data)
    serializer.is_valid(raise_exception=True)
    stage = serializer.save()
    Log.build_update_object_log(request.user, origin, stage, related_object=payment)
    data = ProjectPaymentStageSerializer(stage).data
    return api_success(data)


@api_view(['PUT'])
def project_payment_stage_receipt(request, stage_id):
    stage = get_object_or_404(ProjectPaymentStage, pk=stage_id)
    payment = stage.project_payment
    is_finance = in_group(request.user, settings.GROUP_NAME_DICT["finance"])
    if not request.user.is_superuser and not is_finance:
        return api_bad_request("只有财务有权限填写已收款信息")
    if payment.status != 'process':
        return api_bad_request("合同{}, 不能编辑".format(payment.status_display))
    origin = deepcopy(stage)

    serializer = ProjectPaymentStageReceiptedSerializer(stage, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    stage = serializer.save()
    payment.save()
    Log.build_update_object_log(request.user, origin, stage, related_object=payment)
    data = ProjectPaymentStageSerializer(stage).data
    send_project_payment_stage_notifications(request, origin, stage)
    return api_success(data)


def send_project_payment_stage_notifications(request, origin, stage, comment=None):
    payment = stage.project_payment
    project = payment.project
    notification_users = set()
    if project.manager_id and project.manager_id != request.user.id:
        notification_users.add(project.manager)
    if project.mentor_id and project.mentor_id != request.user.id:
        notification_users.add(project.mentor)
    if not notification_users:
        return

    fields = set(request.data.keys())
    fields.add('status')
    # 构造推送消息
    content = "{username}修改了项目【{project}】的【payment_name】收款记录：".format(username=request.user.username,
                                                                      project=payment.project.name,
                                                                      payment_name=payment.contract_name)
    content_detail = ''
    for field_name in fields:
        if hasattr(origin, field_name):
            field = stage._meta.get_field(field_name)
            new_value = get_field_value(stage, field)
            old_value = get_field_value(origin, field)
            if new_value != old_value:
                verbose_name = origin._meta.get_field(field_name).verbose_name
                field_update_content = ' {field_name}: {old_value}➔{new_value}；'.format(field_name=verbose_name,
                                                                                        old_value=old_value,
                                                                                        new_value=new_value)
                content_detail = content_detail + field_update_conten
    if content_detail:
        content = content + content_detail
        content = content.rsplit('；', 1)[0]
        if comment:
            content = content + ' 备注：' + comment
        project_url = get_protocol_host(request) + '/projects/{}/?anchor=myProjectPay'.format(project.id)
        create_notification_to_users(notification_users, content, project_url)


def send_project_payment_notifications(request, origin, payment, comment=None):
    project = payment.project
    notification_users = set()
    if project.manager_id and project.manager_id != request.user.id:
        notification_users.add(project.manager)
    if project.mentor_id and project.mentor_id != request.user.id:
        notification_users.add(project.mentor)
    if not notification_users:
        return

    fields = set(request.data.keys())
    fields.add('status')
    # 构造推送消息
    content = "{username}修改了项目【{project}】的【{payment_name}】收款记录：".format(username=request.user.username,
                                                                        project=payment.project.name,
                                                                        payment_name=payment.contract_name)
    content_detail = ''
    for field_name in fields:
        if hasattr(origin, field_name):
            field = payment._meta.get_field(field_name)
            new_value = get_field_value(payment, field)
            old_value = get_field_value(origin, field)
            if new_value != old_value:
                verbose_name = origin._meta.get_field(field_name).verbose_name
                field_update_content = ' {field_name}: {old_value}➔{new_value}；'.format(field_name=verbose_name,
                                                                                        old_value=old_value,
                                                                                        new_value=new_value)
                content_detail = content_detail + field_update_content
    if content_detail:
        content = content + content_detail
        content = content.rsplit('；', 1)[0]
        if comment:
            content = content + ' 备注：' + comment
        project_url = get_protocol_host(request) + '/projects/{}/?anchor=myProjectPay'.format(project.id)
        create_notification_to_users(notification_users, content, project_url)


class JobContractList(APIView):
    def get(self, request):
        contract_category = request.GET.get('contract_category', 'project')
        serializer_class = JobContractRegularListSerializer if contract_category == 'regular' else JobContractListSerializer
        if contract_category == 'project':
            if not has_function_perm(request.user, 'finance.view_all_project_developer_contracts'):
                return api_permissions_required()
            queryset = JobContract.valid_project_contracts()
        elif contract_category == 'regular':
            queryset = JobContract.objects.none()
            if has_function_perm(request.user, 'finance.view_all_regular_developer_contracts'):
                queryset = JobContract.valid_regular_contracts()
            elif has_function_perm(request.user, 'finance.view_my_regular_developer_contracts'):
                queryset = JobContract.my_regular_contracts(request.user)
        else:
            queryset = JobContract.objects.none()

        params = request.GET
        contract_id = params.get('contract_id', '')
        search = params.get('search', '')
        status = params.get('status', '')
        pay_status = params.get('pay_status', '')
        pay_status = re.sub(r'[;；,，]', ' ', pay_status).split() if pay_status else []
        ordering = params.get('ordering', 'committed_at')

        if status:
            queryset = queryset.filter(status=status)
        if pay_status:
            queryset = queryset.filter(pay_status__in=pay_status)

        if search:
            queryset = queryset.filter(Q(job_position__project__name__icontains=search) | Q(name__icontains=search))
        if contract_id:
            queryset = queryset.filter(pk=contract_id)
        if ordering:
            ordering_fields = re.sub(r'[;；,，]', ' ', ordering).split()
            ordering_fields = [param.strip() for param in ordering_fields if param.strip()]
            if ordering_fields:
                queryset = queryset.order_by(*ordering_fields)

        return build_pagination_response(request, queryset, serializer_class)

    # 项目经理添加合同
    @transaction.atomic
    def post(self, request):
        contract_category = request.data.get('contract_category', 'project')
        project = None
        if contract_category == 'regular':
            developer_id = request.data.get('developer', None)
            if not developer_id:
                return api_request_params_required('developer')
            developer = get_object_or_404(Developer, pk=developer_id)
            contract_type = 'regular'
        else:
            job_position_id = request.data.get('job_position', '')
            job_position = get_object_or_404(JobPosition, pk=job_position_id)
            developer = job_position.developer

            project = job_position.project
            is_mine = has_function_perm(request.user,
                                        'manage_my_project_job_positions') and request.user in project.members
            has_perm = is_mine or has_function_perm(request.user, 'manage_all_project_job_positions')
            if not has_perm:
                return api_permissions_required()
            contract_type = 'design' if job_position.role.name == '设计师' else 'common'

            # 文档校验
            f1 = request.data.get('develop_function_declaration', None)
            f2 = request.data.get('delivery_list', None)
            if contract_type == 'common' and not f1:
                return api_bad_request('请上传开发功能说明文档')
            if contract_type == 'design' and not f2:
                return api_bad_request('请上传交付清单')
            for f_id in [f1, f2]:
                if f_id:
                    f = get_object_or_404(File, pk=f_id)
                    excel_type = get_file_suffix(f.file.name)
                    if excel_type not in ['docx', 'doc']:
                        return api_bad_request('请上传word格式的文档')

        # 金额校验
        contract_money = request.data.get('contract_money', 0)
        if not contract_money or not isinstance(contract_money, int):
            return api_bad_request("合同金额必填， 且为整数")
        pay_way = request.data.get('pay_way', 'installments')

        # 验证打款方式
        if pay_way == 'installments':
            remit_way = request.data.get('remit_way', None)
            if not remit_way:
                return api_bad_request('请输入打款方式')
            if contract_type == 'regular':
                if remit_way['amount'] > contract_money:
                    return api_bad_request("进度打款金额不能大于总金额")
            else:
                proportion_total = 0
                if remit_way:
                    for i in remit_way:
                        proportion = i['proportion']
                        proportion_total += proportion
                        item_money = round(contract_money * proportion / 100, 2)
                        if not item_money - int(item_money):
                            item_money = int(item_money)
                        i['money'] = item_money
                    if proportion_total != 100:
                        return api_bad_request("打款比例相加要等于100%")
            request.data['remit_way'] = json.dumps(remit_way, ensure_ascii=False)
        request.data['project_results_show'] = json.dumps(request.data.get('project_results_show', []),
                                                          ensure_ascii=False)
        request.data['creator'] = request.user.id
        request.data['developer'] = developer.id
        serializer_dict = {
            'design': JobDesignContractCreateSerializer,
            'common': JobContractCreateSerializer,
            'regular': JobRegularContractCreateSerializer
        }
        serializer_class = serializer_dict[contract_type]
        serializer = serializer_class(data=request.data)
        savepoint = transaction.savepoint()
        if serializer.is_valid():
            job_contract = serializer.save()
            if contract_category == 'regular':
                job_contract.status = "un_generate"
                job_contract.save()
            # 同步工程师的身份信息+打款信息
            developer_data = DeveloperContractSerializer(developer).data
            if developer.front_side_of_id_card:
                file = developer.front_side_of_id_card
                suffix = get_file_suffix(file.name) or 'png'
                front_side_file = DjangoFile(file, name="{}.{}".format(gen_uuid(8), suffix))
                developer_data['front_side_of_id_card'] = front_side_file
            if developer.back_side_of_id_card:
                file = developer.back_side_of_id_card
                suffix = get_file_suffix(file.name) or 'png'
                back_side_file = DjangoFile(file, name="{}.{}".format(gen_uuid(8), suffix))
                developer_data['back_side_of_id_card'] = back_side_file

            new_data = {}
            for key, value in developer_data.items():
                if value:
                    new_data[key] = value
            contract_serializer = JobContractRedactSerializer(job_contract, data=new_data, partial=True)
            if not contract_serializer.is_valid():
                transaction.savepoint_rollback(savepoint)
                return api_bad_request(contract_serializer.errors)

            job_contract = contract_serializer.save()
            if contract_category == "project":
                Log.build_create_object_log(request.user, job_contract, job_contract.job_position.project)
                Log.build_create_object_log(request.user, job_contract, job_contract.job_position)
            else:
                Log.build_create_object_log(request.user, job_contract)
            create_job_contract_docx_pdf_files.delay(job_contract.id)
            create_confidentiality_agreement_docx_pdf_files.delay(job_contract.id)
            data = JobContractSerializer(job_contract).data
            return api_success(data=data)
        return api_bad_request(serializer.errors)


@api_view(['GET'])
def get_contract_statistic(request):
    contract_category = request.GET.get('contract_category', 'project')
    if contract_category == 'project':
        queryset = JobContract.valid_project_contracts()
    elif contract_category == 'regular':
        queryset = JobContract.objects.none()
        if has_function_perm(request.user, 'finance.view_all_regular_developer_contracts'):
            queryset = JobContract.valid_regular_contracts()
        elif has_function_perm(request.user, 'finance.view_my_regular_developer_contracts'):
            queryset = JobContract.my_regular_contracts(request.user)
    else:
        queryset = JobContract.objects.none()
    status_list = list(queryset.values_list('status', flat=True))
    pay_status_list = list(queryset.exclude(pay_status__isnull=True).values_list('pay_status', flat=True))
    list_data = []
    list_data.extend(status_list)
    list_data.extend(pay_status_list)
    data = dict(Counter(list_data))
    if contract_category == 'regular':
        data['need_started_payment_count'] = get_user_developers_regular_contracts_undone_work_count(request.user)
    return api_success(data=data)


@api_view(['POST'])
def job_contract_detail_diff_developer(request, contract_id):
    job_contract = get_object_or_404(JobContract, pk=contract_id)
    if job_contract.status not in ['uncommitted', 'un_generate']:
        return api_bad_request('合同处于{}状态，不能编辑'.format(job_contract.get_status_display()))
    developer = job_contract.developer
    developer_data = DeveloperContractSerializer(developer).data
    origin_data = {}
    new_data = {}

    for key in developer_data:
        if key in request.data:
            new_data[key] = request.data[key]
            origin_data[key] = developer_data[key]

    diff_res = json_tools.diff(dict(origin_data), dict(new_data))
    for diff_item in diff_res:
        for i in ['replace', 'remove', 'add']:
            if i in diff_item:
                diff_item['type'] = i
                diff_item['field'] = diff_item[i].replace('/', '')
                diff_item.pop(i)
                break
    return api_success(data=diff_res)


@api_view(['GET'])
def job_contract_payments_statistics(request, contract_id):
    job_contract = get_object_or_404(JobContract, pk=contract_id)
    return api_success(data=job_contract.payments_statistics)


def handle_developer_payment_create(request, developer, job_contract, job_position, project):
    if job_contract:
        if job_contract.status != 'signed':
            return api_bad_request('该合同不处在已签约状态，当前状态为{},不能添加打款'.format(
                job_contract.get_status_display()))
        if job_contract.contract_category == "regular":
            if not has_function_perm(request.user, "finance.manage_regular_developer_contract_payments"):
                return api_permissions_required()
    if project:
        is_mine = has_function_perm(request.user,
                                    'manage_my_project_job_positions') and request.user in project.members
        has_perm = is_mine or has_function_perm(request.user, 'manage_all_project_job_positions')
        if not has_perm:
            return api_permissions_required("你没有权限编辑工程师打款，请联系项目的项目经理、或管理员")

    request_data = deepcopy(request.data)
    if job_contract:
        request_data['job_contract'] = job_contract.id
    if job_position:
        request_data['position'] = job_position.id
    request_data['name'] = developer.name
    request_data['developer'] = developer.id
    request_data['submitter'] = request.user.id
    request_data['status'] = 0
    serializer = JobPaymentCreateSerializer(data=request_data)
    if serializer.is_valid():
        # 检查打款金额
        if job_contract:
            remaining_amount = job_contract.remaining_payment_amount
            if remaining_amount - float(request.data['amount']) < 0:
                return api_bad_request("打款金额超过剩余额度")
        payment = serializer.save()
        # 老合同数据的同步  临时代码
        payee_fields = ('payee_name', 'payee_id_card_number', 'payee_phone', 'payee_opening_bank', 'payee_account')
        if job_contract and job_contract.is_null_contract and not job_contract.payee_name:
            for payee_field in payee_fields:
                setattr(job_contract, payee_field, getattr(payment, payee_field, None))
                job_contract.save()
        if not developer.payee_name and not developer.payee_account:
            for payee_field in payee_fields:
                setattr(developer, payee_field, getattr(payment, payee_field, None))
                developer.save()
        Log.build_create_object_log(request.user, payment, payment.project)
        if payment.position:
            Log.build_create_object_log(request.user, payment, payment.position)
        if job_contract:
            Log.build_create_object_log(request.user, payment, job_contract)
        data = JobPaymentListSerializer(payment).data
        return api_success(data)
    return api_bad_request(serializer.errors)


@api_view(['GET'])
def job_contract_payments(request, contract_id):
    job_contract = get_object_or_404(JobContract, pk=contract_id)
    payments = job_contract.payments.all().order_by('created_at')
    data = JobPaymentListSerializer(payments, many=True).data
    return api_success(data=data)


class JobContractPaymentList(APIView):
    def get(self, request, contract_id):
        job_contract = get_object_or_404(JobContract, pk=contract_id)
        payments = job_contract.payments.all().order_by('created_at')
        data = JobPaymentListSerializer(payments, many=True).data
        return api_success(data=data)

    def post(self, request, contract_id):
        job_contract = get_object_or_404(JobContract, pk=contract_id)
        developer = job_contract.developer
        project = job_contract.project
        job_position = job_contract.job_position
        return handle_developer_payment_create(request, developer, job_contract, job_position, project)


class JobContractDetail(APIView):
    def get(self, request, contract_id):
        job_contract = get_object_or_404(JobContract, pk=contract_id)
        data = JobContractDetailSerializer(job_contract).data
        return api_success(data=data)

    # 项目经理的编辑
    def put(self, request, contract_id):
        job_contract = get_object_or_404(JobContract, pk=contract_id)
        contract_type = job_contract.contract_type
        if contract_type == 'regular':
            return api_bad_request("本接口不开放")

        pay_way = request.data.get('pay_way', 'installments')
        if job_contract.status not in ['uncommitted', 'un_generate', 'rejected']:
            return api_bad_request('合同处于{}状态，不能编辑'.format(job_contract.get_status_display()))
        project = job_contract.job_position.project
        is_mine = has_function_perm(request.user,
                                    'manage_my_project_job_positions') and request.user in project.members
        has_perm = is_mine or has_function_perm(request.user, 'manage_all_project_job_positions')
        if not has_perm:
            return api_permissions_required()
        remit_way = request.data.get('remit_way', [])
        if not remit_way and pay_way == 'installments':
            return api_bad_request('请输入打款方式')

        f1 = request.data.get('develop_function_declaration', None)
        f2 = request.data.get('delivery_list', None)
        if not f1 and contract_type == 'common':
            api_bad_request('请上传开发功能说明文档')
        if not f2 and contract_type == 'design':
            api_bad_request('请上传交付清单')
        f = get_object_or_404(File, pk=f1 or f2)

        excel_type = get_file_suffix(f.file.name)
        if excel_type not in ['docx', 'doc']:
            return api_bad_request('请上传word格式的文档')

        contract_money = request.data.get('contract_money', 0)
        if not contract_money or not isinstance(contract_money, int):
            return api_bad_request("合同金额必填， 且为整数")
        proportion_total = 0
        if remit_way:
            for i in remit_way:
                proportion = i['proportion']
                proportion_total += proportion
                item_money = round(contract_money * proportion / 100, 2)
                if not item_money - int(item_money):
                    item_money = int(item_money)
                i['money'] = item_money
            if proportion_total != 100:
                return api_bad_request("打款比例相加要等于100%")

        request.data['remit_way'] = json.dumps(remit_way)
        request.data['project_results_show'] = json.dumps(request.data.get('project_results_show', []))
        serializer_class = JobDesignContractEditSerializer if contract_type == 'design' else JobContractEditSerializer
        serializer = serializer_class(job_contract, data=request.data)

        if serializer.is_valid():
            job_contract_ob = serializer.save()
            Log.build_update_object_log(request.user, job_contract, job_contract_ob, project)
            Log.build_update_object_log(request.user, job_contract, job_contract_ob, job_contract.job_position)
            create_job_contract_docx_pdf_files.delay(contract_id)
            create_confidentiality_agreement_docx_pdf_files.delay(contract_id)

            data = JobContractSerializer(job_contract_ob).data
            return api_success(data=data)

        return api_bad_request(serializer.errors)

    def delete(self, request, contract_id):
        obj = get_object_or_404(JobContract, pk=contract_id)
        if obj.contract_category == 'project':
            if obj.status not in ['uncommitted', 'rejected']:
                return api_bad_request('合同处于{}状态，不能删除'.format(obj.get_status_display()))
            project = obj.job_position.project
            is_mine = has_function_perm(request.user,
                                        'manage_my_project_job_positions') and request.user in project.members
            has_perm = is_mine or has_function_perm(request.user, 'manage_all_project_job_positions')
            if not has_perm:
                return api_permissions_required()
        else:
            if obj.status not in ['uncommitted', 'rejected', "un_generate"]:
                return api_bad_request('合同处于{}状态，不能删除'.format(obj.get_status_display()))
            if not has_function_perm(request.user, 'finance.manage_regular_developer_contracts'):
                return api_permissions_required()
        origin = deepcopy(obj)
        obj.delete()
        if obj.contract_category == 'project':
            project = obj.job_position.project
            Log.build_delete_object_log(request.user, origin, project)
            Log.build_delete_object_log(request.user, origin, origin.job_position)
        Log.build_delete_object_log(request.user, origin, origin.developer)
        return api_success()


# 法务的编辑
@api_view(['POST'])
def save_contract(request, contract_id):
    job_contract = get_object_or_404(JobContract, pk=contract_id)
    serializer_class = JobContractRedactSerializer
    contract_type = job_contract.contract_type
    if contract_type == 'regular':
        serializer_class = JobRegularContractRedactSerializer
    else:
        if not has_function_perm(request.user, 'finance.manage_all_project_developer_contracts'):
            return api_permissions_required()

    if contract_type == 'regular':
        # 金额校验
        contract_money = request.data.get('contract_money', 0)
        if not contract_money or not isinstance(contract_money, int):
            return api_bad_request("合同金额必填， 且为整数")
        pay_way = request.data.get('pay_way', 'installments')
        # 验证打款方式
        if pay_way == 'installments':
            remit_way = request.data.get('remit_way', None)
            if not remit_way:
                return api_bad_request('请输入打款方式')
            if remit_way['amount'] > contract_money:
                return api_bad_request("进度打款金额不能大于总金额")
            request.data['remit_way'] = json.dumps(remit_way, ensure_ascii=False)
        request.data['project_results_show'] = json.dumps(request.data.get('project_results_show', []),
                                                          ensure_ascii=False)
    # 身份证字段
    # 前端传参数修改图片
    # 前端没有传参数
    #   1、合同有 则不修改
    #   2、合同没有
    #       开发者有  同步开发者的信息
    #       开发者也没有 提示参数必传
    developer = job_contract.developer
    front_side_string = request.data.get('front_side_of_id_card', None)
    back_side_string = request.data.get('back_side_of_id_card', None)

    request_data = deepcopy(request.data)
    request_data.pop('front_side_of_id_card', None)
    request_data.pop('back_side_of_id_card', None)

    if front_side_string:
        front_side_file = base64_string_to_file(front_side_string)
        if not front_side_file:
            return api_bad_request("请上传有效的base64图片字符串")
        request_data['front_side_of_id_card'] = front_side_file
    elif job_contract.front_side_of_id_card:
        pass
    elif developer.front_side_of_id_card:
        file = developer.front_side_of_id_card
        suffix = get_file_suffix(file.name) or 'png'
        front_side_file = DjangoFile(file, name="{}.{}".format(gen_uuid(8), suffix))
        request_data['front_side_of_id_card'] = front_side_file
    else:
        return api_bad_request("请上传身份证照片")

    if back_side_string:
        back_side_file = base64_string_to_file(back_side_string)
        if not back_side_file:
            return api_bad_request("请上传有效的base64图片字符串")
        request_data['back_side_of_id_card'] = back_side_file
    elif job_contract.back_side_of_id_card:
        pass
    elif developer.back_side_of_id_card:
        file = developer.back_side_of_id_card
        suffix = get_file_suffix(file.name) or 'png'
        back_side_file = DjangoFile(file, name="{}.{}".format(gen_uuid(8), suffix))
        request_data['back_side_of_id_card'] = back_side_file
    else:
        return api_bad_request("请上传身份证照片")

    with transaction.atomic():
        sid = transaction.savepoint()
        try:
            serializers = serializer_class(job_contract, data=request_data)
            serializers.is_valid(raise_exception=True)
            serializers.save()
            is_save = request.data.get('is_save', '')  # 是否同步给developer
            if is_save:
                del request_data['is_save']
                request_data = deepcopy(request.data)
                if front_side_string:
                    front_side_file = base64_string_to_file(front_side_string)
                    if front_side_file:
                        request_data['front_side_of_id_card'] = front_side_file
                if back_side_string:
                    back_side_file = base64_string_to_file(back_side_string)
                    if back_side_file:
                        request_data['back_side_of_id_card'] = back_side_file
                serializer = DeveloperContractSerializer(developer, data=request_data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()
        except Exception as e:
            transaction.savepoint_rollback(sid)
            return api_bad_request(str(e))
        else:
            transaction.savepoint_commit(sid)
            create_job_contract_docx_pdf_files.delay(contract_id)
            create_confidentiality_agreement_docx_pdf_files.delay(contract_id)
            return api_success()


# 项目职位工程师合同
@api_view(['POST'])
def submit_contract(request, contract_id):
    job_contract = get_object_or_404(JobContract, pk=contract_id)
    if job_contract.status not in ["uncommitted", 'rejected']:
        return api_bad_request('合同处于{}状态，不能提交'.format(job_contract.get_status_display()))
    job_contract.status = 'un_generate'
    job_contract.committed_at = timezone.now()
    job_contract.save()
    NotificationFactory.build_job_contract_notifications(job_contract, request.user)
    return api_success()


# 终止一个合同
@api_view(['POST'])
def terminate_job_contract(request, contract_id):
    obj = get_object_or_404(JobContract, pk=contract_id)
    if obj.status != "signed":
        return api_bad_request('合同处于{}状态，不能终止'.format(obj.status_display))
    if obj.pay_status != "ongoing":
        return api_bad_request('合同处于{}打款状态，不能终止'.format(obj.pay_status_display))
    if obj.is_fully_paid:
        obj.pay_status = 'completed'
        obj.completed_at = timezone.now()
        obj.save()
        return api_bad_request('合同处于{}打款状态，不能终止'.format(obj.pay_status_display))

    terminated_remarks = request.data.get('terminated_remarks', '')
    terminated_reason = request.data.get('terminated_reason', None)
    if not terminated_reason:
        return api_bad_request('请填写终止原因')

    origin = deepcopy(obj)
    obj.terminated_reason = terminated_reason
    obj.pay_status = 'terminated'
    obj.completed_at = timezone.now()
    if terminated_remarks:
        obj.terminated_remarks = terminated_remarks
    obj.save()
    Log.build_update_object_log(request.user, origin, obj)
    return api_success()


# 项目职位工程师合同
@api_view(['POST'])
def reject_contract(request, contract_id):
    job_contract = get_object_or_404(JobContract, pk=contract_id)
    if job_contract.status != "un_generate":
        return api_bad_request('合同处于{}状态，不能驳回'.format(job_contract.get_status_display()))
    job_contract.status = 'rejected'
    job_contract.save()
    NotificationFactory.build_job_contract_notifications(job_contract, request.user)
    return api_success()


@api_view(['POST'])
@func_perm_required('finance.manage_all_project_developer_contracts')
def close_contract(request, contract_id):
    job_contract = get_object_or_404(JobContract, pk=contract_id)
    if job_contract.status != "waiting":
        return api_bad_request('合同处于{}状态，不能关闭'.format(job_contract.get_status_display()))
    flow_id = job_contract.flow_id if job_contract.flow_id else None
    secret_flow_id = job_contract.secret_flow_id if job_contract.secret_flow_id else None
    if flow_id and not job_contract.is_sign_contract:
        code, msg = ESign.revoke_signature_flow(flow_id)
        if code not in [0, 1437168]:
            return api_bad_request(msg)
    if secret_flow_id and not job_contract.is_sign_secret:
        code1, msg1 = ESign.revoke_signature_flow(secret_flow_id)
        if code1 not in [0, 1437168]:
            return api_bad_request(msg1)

    close_reason = '作废合同'
    if not job_contract.is_sign_secret and not job_contract.is_sign_contract:
        close_reason = '撤销签约'
    job_contract.status = 'closed'
    job_contract.closed_at = timezone.now()
    job_contract.close_reason = close_reason
    job_contract.save()
    NotificationFactory.build_job_contract_notifications(job_contract, request.user)
    return api_success()


@api_view(['GET'])
def preview_contract(request, contract_id):
    job_contract = get_object_or_404(JobContract, pk=contract_id)
    signature = request.GET.get('X-Gear-Signature', None)
    if not signature:
        return api_bad_request('没有秘钥不能预览')
    signature_key = cache.get(signature, None)
    if not signature_key:
        return api_bad_request('X-Gear-Signature参数无效')

    if job_contract.flow_id and job_contract.is_sign_contract:
        pdf_file_path = settings.MEDIA_ROOT + 'finance/developer_contract/{}_contract_signed.pdf'.format(
            contract_id)
    else:
        pdf_file_path = settings.MEDIA_ROOT + 'finance/developer_contract/{}_contract_preview.pdf'.format(contract_id)

    if not os.path.exists(pdf_file_path):
        if not job_contract.is_sign_contract:
            create_job_contract_docx_pdf_files(contract_id)
        else:
            code, msg, url = ESign.download_contract_documents(job_contract.flow_id)
            if code != 0:
                return api_bad_request(msg)
            r = requests.get(url)
            with open(pdf_file_path, "wb") as f:
                f.write(r.content)
    else:
        if not job_contract.flow_id:
            modified_time = os.path.getmtime(pdf_file_path)
            modified_at = datetime.fromtimestamp(modified_time)
            if modified_at <= job_contract.modified_at:
                create_job_contract_docx_pdf_files(contract_id)
            else:
                create_job_contract_docx_pdf_files.delay(contract_id)
    file_name = '{}_contract_preview.pdf'.format(contract_id)
    wrapper = FileWrapper(open(pdf_file_path, 'rb'))
    response = FileResponse(wrapper, content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = "attachment; filename*=utf-8''{}".format(escape_uri_path(file_name))
    response['Access-Control-Expose-Headers'] = 'Content-Disposition'
    return response


@api_view(['GET'])
def preview_contract_signature(request, contract_id):
    signature = gen_uuid(18) + str(contract_id)
    expires = 60 * 60
    cache.set(signature, True, expires)
    data = {'signature': signature, 'expires': expires}
    return api_success(data=data)


@api_view(['GET'])
def download_explain_template(request):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, 'contract_template/develop_function_declaration.docx')
    filename = '开发功能说明.docx'
    wrapper = FileWrapper(open(file_path, 'rb'))
    response = FileResponse(wrapper, content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = "attachment; filename*=utf-8''{}".format(escape_uri_path(filename))
    response['Access-Control-Expose-Headers'] = 'Content-Disposition'
    return response


@api_view(['GET'])
def download_design_delivery_list_template(request):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, 'contract_template/design_delivery_list_template.docx')
    filename = '设计交付清单.docx'
    wrapper = FileWrapper(open(file_path, 'rb'))
    response = FileResponse(wrapper, content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = "attachment; filename*=utf-8''{}".format(escape_uri_path(filename))
    response['Access-Control-Expose-Headers'] = 'Content-Disposition'
    return response


@api_view(['GET'])
def download_contract(request, contract_id):
    job_contract = get_object_or_404(JobContract, pk=contract_id)
    if job_contract.flow_id and job_contract.is_sign_contract:
        download_type = 'pdf'
        pdf_file_path = settings.MEDIA_ROOT + 'finance/developer_contract/{}_contract_signed.pdf'.format(
            contract_id)
    else:
        download_type = 'docx'
        pdf_file_path = settings.MEDIA_ROOT + 'finance/developer_contract/{}_contract.docx'.format(contract_id)

    if not os.path.exists(pdf_file_path):
        if not job_contract.is_sign_contract:
            create_job_contract_docx_pdf_files(contract_id)
        else:
            code, msg, url = ESign.download_contract_documents(job_contract.flow_id)
            if code != 0:
                return api_bad_request(msg)
            r = requests.get(url)
            with open(pdf_file_path, "wb") as f:
                f.write(r.content)
    else:
        if not job_contract.flow_id:
            modified_time = os.path.getmtime(pdf_file_path)
            modified_at = datetime.fromtimestamp(modified_time)
            if modified_at <= job_contract.modified_at:
                create_job_contract_docx_pdf_files(contract_id)

    filename = '{}.docx'.format(job_contract.contract_name)
    content_type = 'application/vnd.ms-excel'
    if download_type == 'pdf':
        filename = '{}.pdf'.format(job_contract.contract_name)
        content_type = 'application/pdf'
    wrapper = FileWrapper(open(pdf_file_path, 'rb'))
    response = FileResponse(wrapper, content_type=content_type)
    response['Content-Disposition'] = "attachment; filename*=utf-8''{}".format(escape_uri_path(filename))
    response['Access-Control-Expose-Headers'] = 'Content-Disposition'
    return response


@api_view(['GET'])
def preview_confidentiality_agreement(request, contract_id):
    job_contract = get_object_or_404(JobContract, pk=contract_id)
    signature = request.GET.get('X-Gear-Signature', None)
    if not signature:
        return api_bad_request('没有秘钥不能预览')
    signature_key = cache.get(signature, None)
    if not signature_key:
        return api_bad_request('X-Gear-Signature参数无效')

    if job_contract.secret_flow_id and job_contract.is_sign_secret:
        pdf_file_path = settings.MEDIA_ROOT + 'finance/developer_contract/{}_confidentiality_agreement_signed.pdf'.format(
            contract_id)
    else:
        pdf_file_path = settings.MEDIA_ROOT + 'finance/developer_contract/{}_confidentiality_agreement_preview.pdf'.format(
            contract_id)

    if not os.path.exists(pdf_file_path):
        if not job_contract.is_sign_secret:
            create_confidentiality_agreement_docx_pdf_files(contract_id)
        else:
            code, msg, url = ESign.download_contract_documents(job_contract.secret_flow_id)
            if code != 0:
                return api_bad_request(msg)
            r = requests.get(url)
            with open(pdf_file_path, "wb") as f:
                f.write(r.content)
    else:
        if not job_contract.secret_flow_id:
            modified_time = os.path.getmtime(pdf_file_path)
            modified_at = datetime.fromtimestamp(modified_time)
            if modified_at <= job_contract.modified_at:
                create_confidentiality_agreement_docx_pdf_files(contract_id)
            else:
                create_confidentiality_agreement_docx_pdf_files.delay(contract_id)
    file_name = '{}_confidentiality_agreement_preview.pdf'.format(contract_id)
    wrapper = FileWrapper(open(pdf_file_path, 'rb'))
    response = FileResponse(wrapper, content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = "attachment; filename*=utf-8''{}".format(escape_uri_path(file_name))
    response['Access-Control-Expose-Headers'] = 'Content-Disposition'
    return response


@api_view(['GET'])
def download_confidentiality_agreement(request, contract_id):
    job_contract = get_object_or_404(JobContract, pk=contract_id)

    if job_contract.secret_flow_id and job_contract.is_sign_secret:
        download_type = 'pdf'
        pdf_file_path = settings.MEDIA_ROOT + 'finance/developer_contract/{}_confidentiality_agreement_signed.pdf'.format(
            job_contract.id)
    else:
        download_type = 'docx'
        pdf_file_path = settings.MEDIA_ROOT + 'finance/developer_contract/{}_confidentiality_agreement.docx'.format(
            job_contract.id)

    if not os.path.exists(pdf_file_path):
        if not job_contract.is_sign_secret:
            create_confidentiality_agreement_docx_pdf_files(contract_id)
        else:
            code, msg, url = ESign.download_contract_documents(job_contract.secret_flow_id)
            if code != 0:
                return api_bad_request(msg)
            r = requests.get(url)
            with open(pdf_file_path, "wb") as f:
                f.write(r.content)

    else:
        if not job_contract.secret_flow_id:
            modified_time = os.path.getmtime(pdf_file_path)
            modified_at = datetime.fromtimestamp(modified_time)
            if modified_at <= job_contract.modified_at:
                create_confidentiality_agreement_docx_pdf_files(contract_id)

    filename = '{}保密协议.docx'.format(job_contract.contract_name)
    content_type = 'application/vnd.ms-excel'
    if download_type == 'pdf':
        filename = '{}.pdf'.format(job_contract.contract_name)
        content_type = 'application/pdf'
    wrapper = FileWrapper(open(pdf_file_path, 'rb'))
    response = FileResponse(wrapper, content_type=content_type)
    response['Content-Disposition'] = "attachment; filename*=utf-8''{}".format(escape_uri_path(filename))
    response['Access-Control-Expose-Headers'] = 'Content-Disposition'
    return response


@api_view(['GET'])
def dev_table(request):
    page = request.GET.get('page', None)
    page_size = request.GET.get('page_size', None)
    if request.user.is_superuser:
        projects = Project.objects.order_by('-created_at').all()[:100]
        rows = []
        for p in projects:
            start = p.created_at.date()
            end = p.done_at
            name = p.name
            price = 0
            for q in p.project_payments.all():
                if q.total_amount:
                    price += q.total_amount
            dev = 0
            for d in p.job_positions.all():
                if d.pay:
                    dev += d.pay
                elif d.developer and d.developer.name == "翟西文":
                    dev += 5000
            cost = dev * 1.1
            days = 0
            days = (end - start).days if end else (datetime.today().date() - start).days
            weeks = days / 7
            cs = 250 * weeks
            tpm = 500 * weeks
            qa = 3500
            pm = 4000 + 500 * (weeks - 1)
            fixed = 2000
            cost += cs + tpm + qa + pm + fixed
            margin = (price - cost) / price if price > 0 else 0
            rows.append({"name": name, "start": start, "end": end, "days": days, "price": price,
                         "dev": dev, "cost": cost, "margin": margin * 100, "internal": cs + tpm + qa + pm, "pid": p.id})
        if page and page_size:
            total = len(rows)
            data = get_paginate_queryset(rows, page, page_size)
            pagination_params = json.dumps({'total': total, 'page': int(page), 'page_size': int(page_size)})
            headers = {'X-Pagination': pagination_params,
                       'Access-Control-Expose-Headers': 'X-Pagination'}
            return api_success(data=data, headers=headers)
        return api_success(rows)
    else:
        return


def upload_pdf_create_flow(pdf_file_path, account_id, contract_name, contract_type):
    filename = clean_text(contract_name) + '.pdf'
    file_size = os.stat(pdf_file_path).st_size
    contract_content_md5 = content_encoding(pdf_file_path)
    code = 0
    msg = '创建成功'
    flow_id = None
    code1, msg1, upload_url, file_id = ESign.get_upload_url(contract_content_md5, filename, file_size)
    if code1 != 0:
        return code1, msg1, flow_id, file_id

    file_bytes = None
    with open(pdf_file_path, "rb") as file:
        file_bytes = file.read()

    code2, msg2 = ESign.upload_contract_pdf(upload_url, contract_content_md5, file_bytes)
    if code2 != 0:
        return code2, msg2, flow_id, file_id

    company_page_index, company_y = find_sign_location(pdf_file_path, "企签区")
    user_page_index, user_y = find_sign_location(pdf_file_path, "乙签区")

    company_x = 330
    company_y = company_y + 25
    user_y = user_y - 25
    if contract_type == 'secret':
        company_x = 280

    # 超过边界的处理
    if company_y < 65:
        company_y = 65
    if company_y > 650:
        company_y = 650
    if user_y > 650:
        user_y = 650
    if user_y < 65:
        user_y = 65

    company_coordinate = {'page': company_page_index, 'x': company_x, 'y': company_y}
    user_coordinate = {'page': user_page_index, 'x': company_x, 'y': user_y}
    code3, msg3, flow_id = ESign.one_step_create_sign_flow(file_id, filename, account_id, contract_name,
                                                           company_coordinate, user_coordinate)
    if code3 != 0:
        return code3, msg3, flow_id, file_id
    return code, msg, flow_id, file_id


@api_view(['POST'])
def generate_sign_contract(request, contract_id):
    job_contract = get_object_or_404(JobContract, pk=contract_id)
    developer = job_contract.developer
    job_contract_data = JobContractRedactSerializer(job_contract).data
    if not developer.is_real_name_auth:
        return api_bad_request('请联系工程师登录开发者端，完成实名认证。链接：https://developer.chilunyc.com')
    for i in job_contract_data:
        if not job_contract_data[i]:
            return api_bad_request('请先完善合同信息')

    if settings.DEVELOPMENT:
        job_contract.generate_at = timezone.now()
        job_contract.signed_at = timezone.now()
        job_contract.is_sign_secret = True
        job_contract.is_sign_contract = True
        job_contract.status = 'signed'
        job_contract.save()
        return api_success()

    # 合同的文件
    pdf_file_path = settings.MEDIA_ROOT + 'finance/developer_contract/{}_contract.pdf'.format(
        job_contract.id)
    if not os.path.exists(pdf_file_path):
        create_job_contract_docx_pdf_files(contract_id)
    else:
        modified_time = os.path.getmtime(pdf_file_path)
        modified_at = datetime.fromtimestamp(modified_time)
        today = timezone.now().date()
        if modified_at <= job_contract.modified_at or today != modified_at.date():
            create_job_contract_docx_pdf_files(contract_id)
    # 保密协议文件
    secret_file_path = settings.MEDIA_ROOT + 'finance/developer_contract/{}_confidentiality_agreement.pdf'.format(
        contract_id)
    if not os.path.exists(secret_file_path):
        create_confidentiality_agreement_docx_pdf_files(contract_id)
    else:
        modified_time = os.path.getmtime(pdf_file_path)
        modified_at = datetime.fromtimestamp(modified_time)
        today = timezone.now().date()
        if modified_at <= job_contract.modified_at or today != modified_at.date():
            create_confidentiality_agreement_docx_pdf_files(contract_id)

    account_id = developer.esign_account_id if developer.esign_account_id else None
    if not account_id:
        code, msg, account_id = ESign.create_person_account(developer.id, job_contract.name,
                                                            job_contract.id_card_number,
                                                            job_contract.phone, job_contract.email)
        developer.esign_account_id = account_id
        developer.save()

    code1, msg1, flow_id, file_id = upload_pdf_create_flow(pdf_file_path, account_id, job_contract.contract_name,
                                                           contract_type='contract')
    if code1 != 0:
        return api_bad_request(msg1)
    job_contract.flow_id = flow_id
    job_contract.file_id = file_id
    job_contract.save()
    contract_name = job_contract.contract_name + '保密协议'
    code2, msg2, secret_flow_id, secret_file_id = upload_pdf_create_flow(secret_file_path, account_id,
                                                                         contract_name, contract_type='secret',
                                                                         )
    if code2 != 0:
        return api_bad_request(msg2)
    job_contract.status = 'waiting'
    job_contract.secret_flow_id = secret_flow_id
    job_contract.secret_file_id = secret_file_id
    job_contract.generate_at = timezone.now()
    job_contract.save()

    return api_success()


@api_view(['GET'])
def get_sign_link(request, contract_id):
    job_contract = get_object_or_404(JobContract, pk=contract_id)
    developer = job_contract.developer
    account_id = developer.esign_account_id if developer.esign_account_id else None
    flow_id = job_contract.flow_id if job_contract.flow_id else None
    secret_flow_id = job_contract.secret_flow_id if job_contract.secret_flow_id else None
    if not account_id or not flow_id or not secret_flow_id:
        return api_bad_request('合同未生成流程或未创建账户无法获取签署链接')
    contract_sign_link = job_contract.contract_sign_link
    if not contract_sign_link and flow_id:
        code1, msg, contract_sign_link = ESign.get_sign_url(account_id, flow_id)
        if code1 != 0:
            return api_bad_request('获取合同签署链接失败' + msg)
        job_contract.contract_sign_link = contract_sign_link
        job_contract.save()

    secret_sign_link = job_contract.secret_sign_link
    if not secret_sign_link and secret_flow_id:
        code2, msg2, secret_sign_link = ESign.get_sign_url(account_id, secret_flow_id)
        if code2 != 0:
            return api_bad_request('获取保密协议签署链接失败' + msg2)
        job_contract.secret_sign_link = secret_sign_link
        job_contract.save()
    data = {'contract_sign_link': contract_sign_link, 'secret_sign_link': secret_sign_link}
    return api_success(data=data)


@api_view(['POST'])
def call_back_handle(request):
    action = request.data.get('action', None)
    if action == 'SIGN_FLOW_FINISH':
        flow_id = request.data.get('flowId')
        flow_result = request.data.get('flowStatus')
        if flow_result and flow_result == '2':
            job_contract = JobContract.objects.filter(flow_id=flow_id).first()
            if job_contract:
                job_contract.is_sign_contract = True
                if job_contract.is_sign_secret:
                    job_contract.signed_at = timezone.now()
                    job_contract.status = 'signed'
                job_contract.save()
            else:
                job_contract = JobContract.objects.filter(secret_flow_id=flow_id).first()
                if job_contract:
                    job_contract.is_sign_secret = True
                    if job_contract.is_sign_contract:
                        job_contract.signed_at = timezone.now()
                        job_contract.status = 'signed'
                    job_contract.save()
            if job_contract and job_contract.status == 'signed':
                NotificationFactory.build_job_contract_notifications(job_contract)
    return Response({'result': True, 'result_code': '200', "message": '请求成功'}, status=200, )
