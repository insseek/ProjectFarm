import logging
from copy import deepcopy
import re
from datetime import datetime, timedelta
import json

from django.conf import settings
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.urls import reverse
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.db.models import Case, IntegerField, Q, Sum, When, F
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from gearfarm.utils.common_utils import get_request_ip
from gearfarm.utils.farm_response import api_success, api_bad_request, build_pagination_response
from gearfarm.utils import farm_response
from farmbase.utils import gen_uuid, get_protocol_host, get_active_users_by_function_perm
from farmbase.serializers import UserBasicSerializer
from farmbase.permissions_utils import has_function_perm, func_perm_any_required, has_any_function_perms, \
    superuser_required
from gearfarm.utils.decorators import request_params_required, request_data_fields_required
from clients.models import Lead
from proposals.models import Proposal
from reports.quip_to_report import QuipToReport
from reports.models import Report, FrameDiagramTag, FrameDiagram, QuotationPlan, \
    CommentPoint, OperatingRecord, Grade, ReportEvaluation
from reports.serializers import IndustrySerializer, ApplicationPlatformSerializer, ProductTypeSerializer, \
    ProductTypeWithChildrenSerializer, MindMapSerializer, ReportFileSerializer, \
    FrameDiagramTagSerializer, FrameDiagramSerializer, ReportCreateSerializer, \
    QuotationPlanSerializer, QuotationPlanEditSerializer, ReportEditSerializer, ReportDetailSerializer, \
    QuotationPlanDetailSerializer, ReportCommentPointSerializer, ReportCommentPointWithCommentsSerializer, \
    RevisionHistoryCreateSerializer, RevisionHistoryDetailSerializer, OperatingRecordDetailSerializer, \
    ReportTagSerializer, LeadReportCreateSerializer, ReportReviewerSerializer, \
    ReportPublishApplicantSerializer, ReportSimpleSerializer, ProposalTagSerializer, ReportEvaluationSerializer, \
    ReportEvaluationViewSerializer, build_lead_filed_data, build_proposal_filed_data, ReportPageSerializer
from logs.models import Log
from reports.markdown_parser import ReportMarkDownParser
from reports.quill_html_parser import QuillHTMLParser
from reports.utils import download_frame_diagram, download_and_convert_opml_to_json_and_img, download_report_file, \
    get_report_uid, get_report_date, \
    report_user_return, report_user_leave, check_report_editable_status, check_report_deletable_status
from reports.report_init_data import report_new_init_content, report_update_init_content, report_new_init_html, \
    report_update_init_html, update_ops, update_html, report_new_init_text, update_text, report_update_init_text
from reports.lead_report_init_data import lead_report_new_init_content, lead_report_new_init_html, \
    lead_report_new_init_text
from proposals.models import Industry, ApplicationPlatform, ProductType

from notifications.utils import create_notification, create_notification_to_users, send_feishu_card_message_to_user
from notifications.tasks import send_report_editable_data_update_reminder
from comments.models import Comment
from comments.serializers import CommentSerializer
from reports.tasks import build_all_report_group_list, build_report_group_list, \
    add_report_to_all_report_group_cache_data


@api_view(['POST'])
def extend_expiration(request, uid):
    report = get_object_or_404(Report, uid=uid)
    report.extend_expiration()
    report_data = ReportDetailSerializer(report).data
    result = {'result': True, 'data': report_data}
    return Response(result)


@api_view(['POST'])
def expire_now(request, uid):
    report = get_object_or_404(Report, uid=uid)
    report.expire_now()
    result = {'result': True, 'data': {'expired_at': report.expired_at}}
    return Response(result)


# 所属行业 应用平台 产品分类
def build_report_tags(report, request):
    industries = request.data.get('industries', None)
    application_platforms = request.data.get('application_platforms', None)
    product_types = request.data.get('product_types', None)

    if industries is not None:
        report.industries.clear()
        industries = Industry.objects.filter(pk__in=industries)
        report.industries.add(*industries)
    if application_platforms is not None:
        report.application_platforms.clear()
        application_platforms = ApplicationPlatform.objects.filter(pk__in=application_platforms)
        report.application_platforms.add(*application_platforms)
    if product_types is not None:
        report.product_types.clear()
        product_types = ProductType.objects.filter(pk__in=product_types)
        report.product_types.add(*product_types)


@api_view(['POST'])
@request_data_fields_required(['industries', 'application_platforms', 'product_types'])
@check_report_editable_status()
def publish_report(request, uid):
    report = get_object_or_404(Report, uid=uid)
    origin = deepcopy(report)
    if report.report_type == 'proposal' and not has_function_perm(request.user, 'publish_proposal_report'):
        return api_bad_request('你没有发布报告的权限')
    if report.is_public:
        return api_bad_request('报告已发布 不能重新发布')
    build_report_tags(report, request)

    report.is_public = True
    report.publisher = request.user
    report.published_at = timezone.now()
    report.expired_at = timezone.now() + timedelta(days=14)
    report.save()

    add_report_to_all_report_group_cache_data.delay(report.id)

    reminders = [report.creator, report.publish_applicant]
    if report.proposal:
        reminders.extend([report.proposal.pm, report.proposal.bd])
    notification_users = set()
    for reminder in reminders:
        if reminder and reminder.is_active and reminder.id != request.user.id:
            notification_users.add(reminder)
    notification_url = get_protocol_host(request) + reverse('reports:preview', kwargs={'uid': report.uid})
    if report.proposal:
        notification_content = '需求【{} {}】的反馈报告发布成功，发布人：{}'.format(report.proposal.id, report.proposal.name,
                                                                  report.publisher.username)
    elif report.lead:
        notification_content = '线索【{} {}】的反馈报告发布成功，发布人：{}'.format(report.lead.id, report.lead.name,
                                                                  report.publisher.username)
    else:
        notification_content = '报告【{}】发布成功，发布人：{}'.format(report.title, report.publisher.username)

    create_notification_to_users(notification_users, notification_content, url=notification_url, priority="important")
    report_data = ReportSimpleSerializer(report).data
    Log.build_update_object_log(request.user, origin, report,
                                related_object=report.proposal if report.proposal else report.lead, comment="发布报告")
    return Response({'result': True, 'data': report_data})


@api_view(['GET'])
def report_reviewers(request):
    users = get_active_users_by_function_perm('publish_proposal_report')
    serializer = UserBasicSerializer(users, many=True)
    return Response({'result': True, 'data': serializer.data})


@api_view(['POST'])
@request_data_fields_required(['industries', 'application_platforms', 'product_types'])
def publish_review_report(request, uid):
    report = get_object_or_404(Report, uid=uid)
    if report.report_type == 'proposal' and not has_any_function_perms(request.user, ['publish_proposal_report',
                                                                                      'publish_proposal_report_review_required']):
        return Response({'result': False, 'message': "你没有发布报告的权限"})

    if report.is_public:
        return Response({'result': False, 'message': "报告已发布 不能重新发布"})
    if report.reviewer:
        return Response({'result': False, 'message': "报告正在申请审核发布 当前审核人{}".format(report.reviewer.username)})

    comment = request.data.get('comment', None)
    if comment:
        request.data['publish_applicant_comment'] = comment
    request.data['publish_applicant'] = request.user.id
    request.data['publish_applicant_at'] = datetime.now()
    serializer = ReportReviewerSerializer(report, data=request.data)
    if serializer.is_valid():
        report = serializer.save()
        build_report_tags(report, request)
        send_report_reviewer_message(request, report)
        return Response({'result': True, 'data': serializer.data})
    return Response({"result": False, "message": serializer.errors})


def send_report_reviewer_message(request, report):
    comment = request.data.get('comment', None)
    # 飞书卡片消息
    feishu_card_message_data = {
        "title": "需求报告审核提醒",
        "fields": [
        ],
        "link": settings.SITE_URL + '/mp/reports/detail/edit/?uid={}'.format(report.uid)
    }
    card_fields = feishu_card_message_data['fields']

    notification_url = get_protocol_host(request) + reverse('reports:new_report', kwargs={'uid': report.uid})
    notification_content = '{}等待发布，请尽快审核。{}，{}{}'

    large_title = ''
    report_title = "报告【{}】".format(report.title)
    applicant = "申请人：{}".format(request.user.username)
    applicant_time = "申请时间：{}".format(timezone.now().strftime(settings.DATETIME_FORMAT))
    comment = "备注：" + comment if comment else ''

    if report.proposal:
        large_title = "需求【{} {}】".format(report.proposal.id, report.proposal.name)
    elif report.lead:
        large_title = '线索【{} {}】'.format(report.lead.id, report.lead.name)

    notification_title = large_title + report_title
    notification_content = notification_content.format(notification_title, applicant, applicant_time, comment)

    for text in [large_title, report_title, applicant, applicant_time, comment]:
        if text:
            card_fields.append(text)

    create_notification(report.reviewer, notification_content, url=notification_url, priority="important",
                        send_feishu=False)
    send_feishu_card_message_to_user(report.reviewer, feishu_card_message_data)


@method_decorator(check_report_editable_status(), name='post')
@method_decorator(check_report_deletable_status(), name='delete')
class ReportDetail(APIView):
    def get(self, request, uid, format=None):
        report = get_object_or_404(Report, uid=uid)
        report_data = ReportDetailSerializer(report).data
        return Response({'result': True, 'data': report_data})

    @transaction.atomic
    def post(self, request, uid, format=None):
        report = get_object_or_404(Report, uid=uid)
        if report.is_public:
            return Response({"result": False, "message": "该报告已经发布不能编辑"})
        if report.creation_source != 'farm':
            return Response({'result': False, 'message': "只有通过Farm创建的报告才能编辑"})

        if report.report_type == 'proposal':
            return edit_proposal_report(request, report)
        else:
            return edit_lead_report(request, report)

    def delete(self, request, uid, format=None):
        report = get_object_or_404(Report, uid=uid)
        if report.is_public:
            return Response({"result": False, "message": "该报告已经发布不能删除"})
        origin = deepcopy(report)
        report.delete()
        Log.build_delete_object_log(request.user, origin, origin.proposal if origin.proposal else origin.lead,
                                    comment='删除报告草稿')
        return Response({'result': True})


def edit_proposal_report(request, report):
    request.data.pop('meeting_participants', None)
    if request.data.get('version_content'):
        version_content = deepcopy(request.data['version_content'])
        # 如果版本数据是空的 默认生成一个
        if not version_content:
            version_content = [
                {'author': request.user.username, 'date': get_report_date(timezone.now()), 'version': 'v1.0'}]
        request.data['version_content'] = json.dumps(version_content, ensure_ascii=False)
        first_version = version_content[0]
        request.data['version'] = first_version['version'] if first_version['version'] else None
        request.data['date'] = first_version['date'] if first_version['date'] else None
        request.data['author'] = first_version['author'] if first_version['author'] else None
    if request.data.get('main_content'):
        request.data['main_content'] = json.dumps(request.data['main_content'], ensure_ascii=False)
    request.data['last_operator'] = request.user.id
    savepoint = transaction.savepoint()
    origin_report = deepcopy(report)
    serializer = ReportEditSerializer(report, data=request.data)
    if serializer.is_valid():
        report = serializer.save()
        try:
            # 报价方案数据
            handle_report_quotation_plans(request, report)
            need_new_history = get_need_new_revision_history(request, origin_report, report)
            # 创建报告操作记录
            handle_report_operating_record(request, origin_report, report, need_new_history)
            # 创建版本历史
            if need_new_history:
                handle_report_revision_history(origin_report, report)
        except Exception as e:
            transaction.savepoint_rollback(savepoint)
            return Response({"result": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        report_data = ReportDetailSerializer(report).data
        leave_page = request.data.get('leave_page') in ['1', 1, 'True', True, 'true']
        # 离开页面
        if leave_page:
            report_user_leave(report, request.user)
        return Response({"result": True, "data": report_data})
    return Response({"result": False, "message": serializer.errors})


def edit_lead_report(request, report):
    request.data.pop('version_content', None)
    if request.data.get('meeting_participants'):
        meeting_participants = deepcopy(request.data['meeting_participants'])
        # 如果参会人员数据是空的 默认生成一个
        if not meeting_participants:
            meeting_participants = [
                {"company": '北京齿轮易创科技有限公司', "name": request.user.username, "position": '',
                 "contact": request.user.profile.phone_number}]
        request.data['meeting_participants'] = json.dumps(meeting_participants, ensure_ascii=False)
    if request.data.get('main_content'):
        request.data['main_content'] = json.dumps(request.data['main_content'], ensure_ascii=False)
    request.data['last_operator'] = request.user.id
    savepoint = transaction.savepoint()
    origin_report = deepcopy(report)
    serializer = ReportEditSerializer(report, data=request.data)
    if serializer.is_valid():
        report = serializer.save()
        try:
            # 报价方案数据
            handle_report_quotation_plans(request, report)
            need_new_history = get_need_new_revision_history(request, origin_report, report)
            # 创建报告操作记录
            handle_report_operating_record(request, origin_report, report, need_new_history)
            # 创建版本历史
            if need_new_history:
                handle_report_revision_history(origin_report, report)
        except Exception as e:
            transaction.savepoint_rollback(savepoint)
            return Response({"result": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        report_data = ReportDetailSerializer(report).data
        leave_page = request.data.get('leave_page') in ['1', 1, 'True', True, 'true']
        # 离开页面
        if leave_page:
            report_user_leave(report, request.user)
        return Response({"result": True, "data": report_data})
    return Response({"result": False, "message": serializer.errors})


def handle_report_quotation_plans(request, report):
    quotation_plan_price_unit = request.data.get('quotation_plan_price_unit', '')
    if request.data.get('quotation_plans'):
        quotation_plans_data = request.data.get('quotation_plans')
        for plan_data in quotation_plans_data:
            plan_data = deepcopy(plan_data)
            quotation_plan = report.quotation_plans.filter(pk=plan_data['id'])
            if quotation_plan.exists():
                quotation_plan = quotation_plan.first()
                if not plan_data.get('title'):
                    plan_data.pop('title', '')
                if plan_data.get('price_detail'):
                    plan_data['price_detail'] = json.dumps(plan_data['price_detail'], ensure_ascii=False)
                if plan_data.get('price'):
                    plan_data['price'] = plan_data['price'] + quotation_plan_price_unit
                serializer = QuotationPlanEditSerializer(quotation_plan, data=plan_data)
                now = timezone.now()
                if serializer.is_valid():
                    plan = serializer.save()
                    if plan.updated_at and plan.updated_at > now:
                        report.updated_at = timezone.now()
                        report.save()
                else:
                    raise Exception(str(serializer.errors))


def get_need_new_revision_history(request, origin_report, report):
    last_operator = origin_report.last_operator
    current_editor = request.user
    # 换人编辑
    if last_operator.id != current_editor.id:
        return True
    # 不存在
    if not report.histories.exists():
        handle_report_revision_history(origin_report, report)
        return False
    return_page = request.data.get('return_page') in ['1', 1, 'True', True, 'true']
    leave_page = request.data.get('leave_page') in ['1', 1, 'True', True, 'true']
    # 离开页面
    if leave_page:
        return True
    # 进入页面第一次编辑 编辑者不变 不创建新版本
    if return_page:
        return False
    # 每隔五分钟创建一个新版本
    last_history = report.histories.order_by('-created_at').first()
    if timezone.now() > last_history.created_at + timedelta(minutes=5):
        return True


def handle_report_revision_history(origin_report, report):
    last_history = None
    if report.histories.exists():
        last_history = report.histories.order_by('-created_at').first()
    report_data = ReportDetailSerializer(origin_report).data
    new_number = last_history.number + 1 if last_history else 1
    data = {'report_data': json.dumps(report_data, ensure_ascii=False), 'author': origin_report.last_operator.id,
            'report': report.id, 'number': new_number}
    serializer = RevisionHistoryCreateSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
    else:
        raise Exception(str(serializer.errors))


def handle_report_operating_record(request, origin_report, report, need_new_history):
    last_history = report.histories.order_by('-created_at').first()
    # 生成新版本之前 创建一个操作记录
    history_report_data = json.loads(last_history.report_data, encoding='utf-8')
    report_data = ReportDetailSerializer(report).data
    origin_report_data = ReportDetailSerializer(origin_report).data
    record_data = None
    if need_new_history:
        # 生成新版本之前 创建一个操作记录
        OperatingRecord.build_update_report_log(request.user, history_report_data, origin_report_data, report,
                                                request=request)
        # 创建最近操作记录
        cache_record = OperatingRecord.build_update_report_log(request.user, origin_report_data, report_data, report,
                                                               read_only=True, request=request)
        if cache_record:
            record_data = OperatingRecordDetailSerializer(cache_record).data
    # 不需要新版本 最近操作记录存在缓存中（避免每次改动都修改数据库）
    else:
        cache_record = OperatingRecord.build_update_report_log(request.user, history_report_data, report_data, report,
                                                               read_only=True, request=request)
        if cache_record:
            record_data = OperatingRecordDetailSerializer(cache_record).data
    if record_data:
        if not cache.get('reports_last_records'):
            cache.set('reports_last_records', {report.uid: record_data})
        else:
            reports_last_records = cache.get('reports_last_records')
            reports_last_records[report.uid] = record_data
            cache.set('reports_last_records', reports_last_records, None)


@api_view(['GET'])
def reports_tags(request):
    industries = IndustrySerializer(Industry.objects.order_by('index'), many=True).data
    application_platforms = ApplicationPlatformSerializer(ApplicationPlatform.objects.order_by('index'),
                                                          many=True).data
    product_types = ProductTypeWithChildrenSerializer(ProductType.objects.filter(parent_id=None).order_by('index'),
                                                      many=True).data
    data = {"application_platforms": application_platforms, "industries": industries, "product_types": product_types}

    return farm_response.api_success(data=data)


@method_decorator(request_data_fields_required(['industries', 'application_platforms', 'product_types']), name='post')
class ReportTags(APIView):
    def get(self, request, uid):
        report = get_object_or_404(Report, uid=uid)
        report_data = ReportTagSerializer(report).data
        if not any([report_data['industries'], report_data['application_platforms'], report_data['product_types']]):
            if report.previous_obj_public_report:
                report_data = ReportTagSerializer(report.previous_obj_public_report).data
            elif report.proposal:
                report_data = ProposalTagSerializer(report.proposal).data
        return farm_response.api_success(data=report_data)

    def post(self, request, uid):
        report = get_object_or_404(Report, uid=uid)
        build_report_tags(report, request)
        report_data = ReportTagSerializer(report).data
        return Response({'result': True, 'data': report_data})


def filter_public_reports(request, report_type, queryset=None):
    params = request.GET
    search_value = params.get('search_value', None)
    industries = params.get('industries', None)
    application_platforms = params.get('application_platforms', None)
    product_types = params.get('product_types', None)
    reports = queryset or Report.objects.filter(is_public=True, report_type=report_type)
    # 筛选   关键词 行业、产品形态、分类
    if search_value:
        reports = reports.filter(Q(title__icontains=search_value) | Q(author__icontains=search_value))
    if industries:
        industry_ids = re.sub(r'[;；,，]', ' ', industries).split()
        reports = reports.filter(industries__id__in=industry_ids).distinct()
    if application_platforms:
        platform_ids = re.sub(r'[;；,，]', ' ', application_platforms).split()
        reports = reports.filter(application_platforms__id__in=platform_ids).distinct()
    if product_types:
        product_type_ids = set(re.sub(r'[;；,，]', ' ', product_types).split())
        product_types = ProductType.objects.filter(id__in=product_type_ids)
        for product_type in product_types:
            children_ids = set(product_type.children.values_list('id', flat=True))
            product_type_ids = product_type_ids | children_ids
        reports = reports.filter(product_types__id__in=product_type_ids).distinct()

    reports = reports.order_by("-published_at")
    return reports


def build_report_group_pagination_response(report_group_list, request):
    params = request.GET
    page = int(params.get('page')) if params.get('page') else 1
    page_size = int(params.get('page_size')) if params.get('page_size') else 20
    group_count = len(report_group_list)
    page_groups = []
    if group_count:
        # 获取分页 起始 和 结束位置
        group_start = int(page - 1) * int(page_size)
        group_end = int(page) * int(page_size)
        if group_start < 0:
            group_start = 0
        if group_end < 0:
            group_end = 0
        page_groups = report_group_list[group_start:group_end]
        # 构建json数据
        for page_group in page_groups:
            proposal_id = page_group.get('proposal', None)
            lead_id = page_group.get('lead', None)
            if proposal_id:
                proposal = Proposal.objects.filter(pk=proposal_id).first()
                if proposal:
                    page_group["proposal"] = build_proposal_filed_data(proposal)
            if lead_id:
                lead = Lead.objects.filter(pk=lead_id).first()
                if lead:
                    page_group["lead"] = build_proposal_filed_data(lead)
            reports = Report.objects.filter(id__in=page_group["reports"]).order_by("-published_at")
            page_group["reports"] = ReportPageSerializer(reports, many=True).data
            page_group.pop('published_at', None)
    pagination_params = json.dumps({'total': group_count, 'page': int(page), 'page_size': int(page_size)})
    headers = {'X-Pagination': pagination_params,
               'Access-Control-Expose-Headers': 'X-Pagination'}
    return farm_response.api_success(data=page_groups, headers=headers)


@api_view(['GET'])
@request_params_required(['page', 'page_size'])
def all_report_list(request):
    is_all_reports = True
    params = request.GET
    if is_all_reports:
        for filter_field in ["search_value", "industries", "application_platforms", "product_types"]:
            if params.get(filter_field, None):
                is_all_reports = False
                break
    # 提升查询效率 全部报告使用缓存
    if is_all_reports:
        report_group_list, report_group_dict = build_all_report_group_list("proposal")
    else:
        reports = filter_public_reports(request, "proposal")
        report_group_list, report_group_dict = build_report_group_list(reports)
    return build_report_group_pagination_response(report_group_list, request)


@api_view(['GET'])
@request_params_required(['page', 'page_size'])
def lead_report_list(request):
    params = request.GET
    user = request.user
    reports = Report.objects.filter(is_public=True, report_type="lead")
    is_all_reports = True
    if not has_function_perm(request.user, 'view_all_leads'):
        my_lead_ids = Lead.objects.filter(Q(creator_id=user.id) | Q(salesman_id=user.id)).values_list('id', flat=True)
        reports = reports.filter(lead_id__in=my_lead_ids)
        is_all_reports = False
    if is_all_reports:
        for filter_field in ["search_value", "industries", "application_platforms", "product_types"]:
            if params.get(filter_field, None):
                is_all_reports = False
                break
    if is_all_reports:
        report_group_list, report_group_dict = build_all_report_group_list("lead")
    else:
        reports = filter_public_reports(request, "lead", queryset=reports)
        report_group_list, report_group_dict = build_report_group_list(reports)
    return build_report_group_pagination_response(report_group_list, request)


@api_view(['POST'])
def create_report_by_md(request):
    action = request.data.get('action', None)
    if action not in ['preview', 'create', 'pdf', 'replace', 'new']:
        return Response({"result": False, "message": "请求参数action无效 有效值为['preview', 'create', 'pdf', 'replace', 'new']"},
                        status=status.HTTP_400_BAD_REQUEST)
    if not {'proposal', 'md'}.issubset(request.data.keys()):
        return Response({"result": False, "message": "MD创建报告时,需求、MD文本"}, status=status.HTTP_400_BAD_REQUEST)

    proposal_id = request.data['proposal']
    proposal = get_object_or_404(Proposal, pk=proposal_id)

    md = request.data['md']
    if 'undefined' in md:
        return Response({'result': False, 'message': "Markdown文本中含:'undefined', 可能为QUIP新版本问题，请尝试用QUIP链接生成"})

    show_next = request.data.get('show_next', True)
    show_services = request.data.get('show_services', True)
    parser = ReportMarkDownParser(md)

    try:
        parser.parse()
    except Exception as e:
        logger = logging.getLogger()
        logger.error(e)
        return Response({'result': False, 'message': "解析Markdown错误，可能为格式问题"})

    # 查找该需求重复报告
    if action != 'preview':
        title = parser.title
        version = parser.docRecord.version
        repeated_reports = Report.objects.filter(Q(title=title), Q(version=version), Q(proposal=proposal))

    if action == 'create':
        if repeated_reports.exists():
            return Response({"result": False, "is_repeated": True, "message": "该需求存在相同名字、版本的报告"})
        report = parser.save(proposal, show_next=show_next, show_services=show_services)
        Log.build_create_object_log(request.user, report, related_object=proposal)
        result = {'result': True, 'report_url': settings.REPORTS_HOST + reverse('reports:view', args=(report.uid,)),
                  "message": "报告生成成功"}
    elif action == 'pdf':
        report = parser.save(proposal, show_next=show_next, show_services=show_services)
        result = {'report_url': reverse('reports:pdf', args=(report.uid,))}
    elif action == 'preview':
        report = parser.new_report(proposal, show_next=show_next, show_services=show_services)
        cache.set(report.uid, report, 180)
        result = {'result': True, 'preview': True, 'report_url': reverse('reports:preview', args=(report.uid,)),
                  "message": "预览报告生成成功"}
    elif action == 'new':
        report = parser.save(proposal, show_next=show_next, show_services=show_services)

        Log.build_create_object_log(request.user, report, related_object=proposal)
        result = {'result': True, 'report_url': settings.REPORTS_HOST + reverse('reports:view', args=(report.uid,)),
                  "message": "报告生成成功"}
    elif action == 'replace':
        if not repeated_reports.exists():
            return Response({"result": False, "is_repeated": False, "message": "该需求不存在相同名字、版本的报告，无法替换"})
        origin = deepcopy(repeated_reports[0])
        report = parser.replace_report(proposal, show_next=show_next, show_services=show_services,
                                       repeated_report=repeated_reports[0])

        Log.build_update_object_log(request.user, origin, report, related_object=proposal)
        result = {'result': True, 'report_url': settings.REPORTS_HOST + reverse('reports:view', args=(report.uid,)),
                  "message": "报告替换成功"}
    else:
        return Response({"result": False, "message": "请求参数action无效"}, status=status.HTTP_400_BAD_REQUEST)
    return Response(result)


@api_view(['POST'])
def create_report_by_quip_url(request):
    action = request.data.get('action', None)

    if action not in ['preview', 'create', 'replace', 'new']:
        return Response({"result": False, "message": "请求参数action无效 有效值为['preview', 'create', 'replace', 'new']"},
                        status=status.HTTP_400_BAD_REQUEST)

    if not {'proposal', 'quip_url'}.issubset(request.data.keys()):
        return Response({"result": False, "message": "QUIP链接创建报告时,需求 链接、类型、行业必填"}, status=status.HTTP_400_BAD_REQUEST)

    proposal_id = request.data['proposal']
    proposal = get_object_or_404(Proposal, pk=proposal_id)

    show_next = request.data.get('show_next', True)
    show_services = request.data.get('show_services', True)

    url = request.data['quip_url']

    if request.is_secure():
        protocol = 'https'
    else:
        protocol = 'http'
    request_domain = protocol + "://" + request.get_host()

    quip_to_report = QuipToReport(url=url, request_domain=request_domain)
    report = quip_to_report.create_report(proposal, show_next=show_next, show_services=show_services)

    # 查找该需求重复报告

    if action != "preview":
        title = quip_to_report.html_parser.title
        version = quip_to_report.html_parser.current_version.version
        repeated_reports = Report.objects.filter(Q(title=title), Q(version=version), Q(proposal=proposal))

    if action == "preview":
        cache.set(report.uid, report, 180)
        result = {'result': True, 'preview': True, 'report_url': reverse('reports:cache_view', args=(report.uid,), ),
                  "message": "预览报告生成成功"}
    elif action == "create":
        if repeated_reports.exists():
            return Response({"result": False, "is_repeated": True, "message": "该需求存在相同名字、版本的报告"})
        report.save()

        Log.build_create_object_log(request.user, report, related_object=proposal)
        content = '需求【{}】{} 生成了新报告'.format(proposal.id, proposal.name)
        create_notification(proposal.bd, content,
                            url='/proposals/detail/?proposalId={}'.format(proposal.id))
        result = {'result': True, 'report_url': settings.REPORTS_HOST + reverse('reports:view', args=(report.uid,)),
                  "message": "报告生成成功"}
    elif action == "replace":
        if not repeated_reports.exists():
            return Response({"result": False, "is_repeated": False, "message": "该需求不存在相同名字、版本的报告，无法替换"})
        origin = deepcopy(repeated_reports[0])
        report = quip_to_report.replace_report(proposal, show_next=show_next, show_services=show_services,
                                               repeated_report=repeated_reports[0])

        Log.build_update_object_log(request.user, origin, report, related_object=proposal, comment="更新报告内容 原地址不变")
        content = '需求【{}】{} 生成了新报告'.format(proposal.id, proposal.name)
        create_notification(proposal.bd, content,
                            url='/proposals/detail/?proposalId={}'.format(proposal.id))
        result = {'result': True, 'report_url': settings.REPORTS_HOST + reverse('reports:view', args=(report.uid,)),
                  "message": "报告替换成功"}
    elif action == "new":
        report.save()

        Log.build_create_object_log(request.user, report, related_object=proposal)
        content = '需求【{}】{} 生成了新报告'.format(proposal.id, proposal.name)
        create_notification(proposal.bd, content, url='/proposals/detail/?proposalId={}'.format(proposal.id))
        result = {'result': True, 'report_url': settings.REPORTS_HOST + reverse('reports:view', args=(report.uid,)),
                  "message": "报告生成成功"}
    else:
        return Response({"result": False, "message": "请求参数action无效 有效值为['preview', 'create', 'replace', 'new']"},
                        status=status.HTTP_400_BAD_REQUEST)
    return Response(result)


class ReportHistoryList(APIView):
    def get(self, request, uid):
        report = get_object_or_404(Report, uid=uid)
        histories = report.histories.all().order_by('-created_at')
        data = RevisionHistoryDetailSerializer(histories, many=True).data
        return Response({'result': True, 'data': data})


class ReportHistoryDetail(APIView):
    def get(self, request, uid, id):
        report = get_object_or_404(Report, uid=uid)
        histories = report.histories.filter(pk=id)
        if histories.exists():
            history = histories.first()
            data = RevisionHistoryDetailSerializer(history).data
            return Response({'result': True, 'data': data})
        return Response({"result": False, "message": "不存在"})


class OperatingRecordList(APIView):
    def get(self, request, uid):
        report = get_object_or_404(Report, uid=uid)
        params = request.GET
        order_by = params.get('order_by', 'created_at')
        order_dir = params.get('order_dir', 'asc')
        if order_dir == 'desc':
            order_by = '-' + order_by
        operating_logs = report.operating_logs.all().order_by(order_by)
        data = OperatingRecordDetailSerializer(operating_logs, many=True).data

        reports_last_records = cache.get('reports_last_records')
        if reports_last_records:
            last_record = reports_last_records.get(uid)
            if last_record:
                data.append(last_record)
        return Response({'result': True, 'data': data})


@method_decorator(check_report_editable_status(), name='post')
class ReportQuotationPlanList(APIView):
    def get(self, request, uid):
        report = get_object_or_404(Report, uid=uid)
        quotation_plans = report.quotation_plans.order_by('position')
        data = QuotationPlanDetailSerializer(quotation_plans, many=True).data
        return api_success(data)

    def post(self, request, uid):
        report = get_object_or_404(Report, uid=uid)
        request.data['report'] = report.id
        request.data['uid'] = gen_uuid()
        request.data['title'] = request.data['title'] if request.data.get('title') else "报价方案"
        if request.data.get('price_detail'):
            request.data['price_detail'] = json.dumps(request.data['price_detail'], ensure_ascii=False)
        request.data['position'] = report.quotation_plans.order_by(
            '-position').first().position + 1 if report.quotation_plans.exists() else 0
        serializer = QuotationPlanSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_success(serializer.data)

        return farm_response.api_bad_request(serializer.errors)


class ReportQuotationPlanDetail(APIView):
    def get(self, request, uid, plan_id):
        report = get_object_or_404(Report, uid=uid)
        quotation_plan = report.quotation_plans.filter(pk=plan_id).first()
        if quotation_plan:
            data = QuotationPlanDetailSerializer(quotation_plan).data
            return Response({'result': True, 'data': data})
        return Response({"result": False, "message": "不存在"})

    def post(self, request, uid, plan_id):
        report = get_object_or_404(Report, uid=uid)
        quotation_plan = report.quotation_plans.filter(pk=plan_id).first()
        if quotation_plan:
            if not request.data.get('title'):
                request.data.pop('title', '')
            if request.data.get('price_detail'):
                request.data['price_detail'] = json.dumps(request.data['price_detail'], ensure_ascii=False)
            serializer = QuotationPlanEditSerializer(quotation_plan, data=request.data)
            if serializer.is_valid():
                quotation_plan = serializer.save()
                data = QuotationPlanDetailSerializer(quotation_plan).data
                return Response({"result": True, "data": data})
            return Response({"result": False, "message": serializer.errors})
        return Response({"result": False, "message": "不存在"})

    def patch(self, request, uid, plan_id):
        report = get_object_or_404(Report, uid=uid)
        quotation_plan = report.quotation_plans.filter(pk=plan_id).first()
        if quotation_plan:
            if not request.data.get('title'):
                request.data.pop('title', '')
            if request.data.get('price_detail'):
                request.data['price_detail'] = json.dumps(request.data['price_detail'], ensure_ascii=False)
            serializer = QuotationPlanEditSerializer(quotation_plan, data=request.data, partial=True)
            if serializer.is_valid():
                quotation_plan = serializer.save()
                data = QuotationPlanDetailSerializer(quotation_plan).data
                return Response({"result": True, "data": data})
            return Response({"result": False, "message": serializer.errors})
        return farm_response.api_not_found("该报价计划不存在")

    def delete(self, request, uid, plan_id):
        report = get_object_or_404(Report, uid=uid)
        quotation_plan = report.quotation_plans.filter(pk=plan_id)
        if quotation_plan.exists():
            quotation_plan = quotation_plan.first()
            quotation_plan.delete()
            return Response({'result': True})
        return Response({"result": False, "message": "不存在"})


@api_view(['POST'])
def move_report_quotation_plan(request, uid, plan_id, move_type):
    report = get_object_or_404(Report, uid=uid)
    quotation_plan = report.quotation_plans.filter(pk=plan_id)
    if quotation_plan.exists():
        quotation_plan = quotation_plan.first()
        current_obj = quotation_plan
        current_position = quotation_plan.position
        if move_type == 'move_up':
            previous_siblings = report.quotation_plans.filter(position__lt=current_position).order_by('-position')
            if previous_siblings.exists():
                previous_sibling = previous_siblings.first()
                previous_sibling.position, current_obj.position = current_obj.position, previous_sibling.position
                previous_sibling.save()
                current_obj.save()
        if move_type == 'move_down':
            next_siblings = report.quotation_plans.filter(position__gt=current_position).order_by('position')
            if next_siblings.exists():
                next_sibling = next_siblings.first()
                next_sibling.position, current_obj.position = current_obj.position, next_sibling.position
                next_sibling.save()
                current_obj.save()
        data = QuotationPlanDetailSerializer(quotation_plan).data
        return Response({'result': True, 'data': data})
    return Response({"result": False, "message": "不存在"})


class FrameDagramList(APIView):
    def get(self, request, format=None):
        frame_diagrams = FrameDiagram.objects.all().order_by('-created_at')
        if 'is_standard' in request.GET and request.GET['is_standard'] in [True, '1', 1, 'true']:
            frame_diagrams = frame_diagrams.filter(is_standard=True)
        if 'is_standard' in request.GET and request.GET['is_standard'] in [False, '0', 0, 'false']:
            frame_diagrams = frame_diagrams.filter(is_standard=False)

        filtered_tags = request.GET.get('tags', None)
        if filtered_tags:
            filtered_tags = re.sub(r'[;；,，]', ' ', filtered_tags).split()
            frame_diagrams = frame_diagrams.filter(tags__name__in=filtered_tags).distinct()

        return build_pagination_response(request, frame_diagrams, FrameDiagramSerializer)


@api_view(['POST'])
@transaction.atomic
def create_proposal_report_by_farm(request):
    request_data = deepcopy(request.data)
    if 'proposal' not in request_data or not request_data['proposal'] or not Proposal.objects.filter(
            pk=request_data['proposal']).exists():
        return Response({"result": False, "message": "创建需求报告时,有效的参数proposal必填"})
    proposal = get_object_or_404(Proposal, pk=request_data['proposal'])
    source_report = request_data.get('source_report', None)
    if source_report:
        if not has_function_perm(request.user, 'clone_proposal_report'):
            return Response({"result": False, "message": "缺失克隆需求报告的权限"})
    else:
        if not has_function_perm(request.user, 'create_proposal_report'):
            return Response({"result": False, "message": "缺失创建需求报告的权限"})
    request_data['report_type'] = 'proposal'
    report_type = request_data['report_type']

    if source_report:
        source_id = request_data.get('source_report')
        if not Report.objects.filter(pk=source_id, report_type=report_type).exists():
            return Response({'result': False, 'message': "报告源不存在"}, status=status.HTTP_400_BAD_REQUEST)
        source_report = Report.objects.get(pk=source_id, report_type=report_type)
        if source_report.creation_source != 'farm':
            return Response({'result': False, 'message': "只有通过Farm创建的报告才能copy"})

    request_data['title'] = proposal.name + ' 项目反馈报告' if proposal.name else '项目反馈报告'
    request_data['version'] = 'v1.0'
    request_data['date'] = get_report_date(timezone.now())
    request_data['proposal'] = proposal.id

    request_data['author'] = request.user.username
    request_data['creator'] = request.user.id
    request_data['last_operator'] = request.user.id

    request_data['creation_source'] = 'farm'
    request_data['uid'] = get_report_uid()
    request_data['is_public'] = False

    version_content = []

    request_data['main_content'] = json.dumps(report_new_init_content, ensure_ascii=False)
    request_data['main_content_html'] = report_new_init_html
    request_data['main_content_text'] = report_new_init_text
    if proposal.reports.exists():
        request_data['main_content'] = json.dumps(report_update_init_content, ensure_ascii=False)
        request_data['main_content_html'] = report_update_init_html
        request_data['main_content_text'] = report_update_init_text

    if source_report:
        request_data['title'] = source_report.title
        if source_report.version_content:
            version_content = json.loads(source_report.version_content, encoding='utf-8')
            try:
                first_version = version_content[0]
                version = first_version['version']
                if version:
                    version_match = re.match(r'^.*?(\d+\.\d+).*$', version)
                    if version_match:
                        new_version = float(version_match.group(1)) + 0.1
                        new_version = str(round(new_version, 1))
                        request_data['version'] = 'v' + new_version
            except Exception as e:
                pass
        if source_report.main_content_html and source_report.main_content:
            parser = QuillHTMLParser(source_report.main_content_html)
            content_html = parser.html
            content_text = source_report.main_content_text if source_report.main_content_text else ''
            main_content = json.loads(source_report.main_content, encoding='utf-8')
            clean_comment_content(main_content)
            main_content_ops = deepcopy(main_content['ops'])
            update_title_match = re.match(r'<h2[\S\s]*?>[\S\s]*?修改记录[\S\s]*?</h2>', content_html)
            if not update_title_match:
                content_html = update_html + content_html
                main_content['ops'] = update_ops + main_content_ops
                content_text = update_text + content_text
            request_data['main_content_html'] = content_html
            request_data['main_content_text'] = content_text
            request_data['main_content'] = json.dumps(main_content, ensure_ascii=False)
    version_data = {"author": request_data['author'], "date": request_data['date'],
                    "version": request_data['version']}
    version_content.insert(0, version_data)
    request_data['version_content'] = json.dumps(version_content, ensure_ascii=False)
    savepoint = transaction.savepoint()
    serializer = ReportCreateSerializer(data=request_data)
    if serializer.is_valid():
        report = serializer.save()
        try:
            # # 初始化操作记录、报价方案
            if source_report:
                if source_report.is_public:
                    comment = "内容克隆自{title}({author} {version} {published_at})".format(title=source_report.title,
                                                                                       author=source_report.author,
                                                                                       published_at=source_report.published_at.strftime(
                                                                                           settings.DATETIME_FORMAT),
                                                                                       version=report.version)
                else:
                    comment = "内容克隆自草稿 {title}({published_at})".format(title=source_report.title,
                                                                       author=source_report.author,
                                                                       published_at=source_report.created_at.strftime(
                                                                           settings.DATETIME_FORMAT),
                                                                       version=report.version)
                OperatingRecord.build_create_report_log(request.user, report, comment=comment,
                                                        source_report=source_report)
                for plan in source_report.quotation_plans.all():
                    QuotationPlan.objects.create(report=report, title=plan.title, uid=get_report_uid(),
                                                 period=plan.period,
                                                 price=plan.price,
                                                 projects=plan.projects, services=plan.services,
                                                 price_detail=plan.price_detail,
                                                 position=plan.position
                                                 )
            else:
                OperatingRecord.build_create_report_log(request.user, report, comment=None, source_report=source_report)
                QuotationPlan.objects.create(report=report, title="报价方案", uid=get_report_uid())
            Log.build_create_object_log(request.user, report, report.proposal)
            # 初始化第一个历史版本
            report_data = ReportDetailSerializer(report).data
            data = {'report_data': json.dumps(report_data, ensure_ascii=False), 'author': request.user.id,
                    'report': report.id, 'number': 1}
            serializer = RevisionHistoryCreateSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
            else:
                raise Exception(str(serializer.errors))
        except Exception as e:
            transaction.savepoint_rollback(savepoint)
            return Response({'result': False, 'message': str(e)})
        # report_data = ReportDetailSerializer(report).data
        return Response({'result': True, 'data': report_data})
    return Response({'result': False, 'message': str(serializer.errors)})


@api_view(['POST'])
@transaction.atomic
def create_lead_report_by_farm(request):
    request_data = deepcopy(request.data)
    if 'lead' not in request_data or not request_data['lead'] or not Lead.objects.filter(
            pk=request_data['lead']).exists():
        return Response({"result": False, "message": "创建线索报告时,有效的参数lead必填"})
    lead = Lead.objects.get(pk=request_data['lead'])

    request_data['report_type'] = 'lead'
    report_type = request_data['report_type']
    source_report = None

    if request_data.get('source_report'):
        source_id = request_data.get('source_report')
        if not Report.objects.filter(pk=source_id, report_type=report_type).exists():
            return Response({'result': False, 'message': "报告源不存在"}, status=status.HTTP_400_BAD_REQUEST)
        source_report = Report.objects.get(pk=source_id, report_type=report_type)
        if source_report.creation_source != 'farm':
            return Response({'result': False, 'message': "只有通过Farm创建的报告才能copy"})

    request_data['title'] = lead.name + ' 沟通反馈记录'

    request_data['lead'] = lead.id

    request_data['author'] = request.user.username
    request_data['creator'] = request.user.id
    request_data['last_operator'] = request.user.id

    request_data['creation_source'] = 'farm'
    request_data['uid'] = get_report_uid()
    request_data['is_public'] = False
    request_data['show_plan'] = False

    meeting_participants = [
        {"company": '北京齿轮易创科技有限公司', "name": request.user.username, "position": '',
         "contact": request.user.profile.phone_number}]

    request_data['main_content'] = json.dumps(lead_report_new_init_content, ensure_ascii=False)
    request_data['main_content_html'] = lead_report_new_init_html
    request_data['main_content_text'] = lead_report_new_init_text

    # 克隆数据导入
    if source_report:
        request_data['title'] = source_report.title
        request_data['show_plan'] = source_report.show_plan
        if source_report.meeting_participants:
            meeting_participants = json.loads(source_report.meeting_participants, encoding='utf-8')

        if source_report.main_content_html and source_report.main_content:
            parser = QuillHTMLParser(source_report.main_content_html)
            content_html = parser.html
            content_text = source_report.main_content_text if source_report.main_content_text else ''
            main_content = json.loads(source_report.main_content, encoding='utf-8')
            clean_comment_content(main_content)

            request_data['main_content_html'] = content_html
            request_data['main_content_text'] = content_text
            request_data['main_content'] = json.dumps(main_content, ensure_ascii=False)

    request_data['meeting_participants'] = json.dumps(meeting_participants, ensure_ascii=False)
    savepoint = transaction.savepoint()
    serializer = LeadReportCreateSerializer(data=request_data)
    if serializer.is_valid():
        report = serializer.save()
        try:
            # 初始化操作记录
            if source_report:
                if source_report.is_public:
                    comment = "内容克隆自{title}({author}{published_at})".format(title=source_report.title,
                                                                            author=source_report.author,
                                                                            published_at=source_report.published_at.strftime(
                                                                                settings.DATETIME_FORMAT))
                else:
                    comment = "内容克隆自草稿 {title}({published_at})".format(title=source_report.title,
                                                                       author=source_report.author,
                                                                       published_at=source_report.created_at.strftime(
                                                                           settings.DATETIME_FORMAT))
                OperatingRecord.build_create_report_log(request.user, report, comment=comment,
                                                        source_report=source_report)
                for plan in source_report.quotation_plans.all():
                    QuotationPlan.objects.create(report=report, title=plan.title, uid=get_report_uid(),
                                                 period=plan.period,
                                                 price=plan.price,
                                                 projects=plan.projects, services=plan.services,
                                                 price_detail=plan.price_detail,
                                                 position=plan.position
                                                 )
            else:
                OperatingRecord.build_create_report_log(request.user, report, comment=None, source_report=source_report)
            Log.build_create_object_log(request.user, report, report.lead)
            # 初始化第一个历史版本
            report_data = ReportDetailSerializer(report).data
            data = {'report_data': json.dumps(report_data, ensure_ascii=False), 'author': request.user.id,
                    'report': report.id, 'number': 1}
            serializer = RevisionHistoryCreateSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
            else:
                raise Exception(str(serializer.errors))
        except Exception as e:
            transaction.savepoint_rollback(savepoint)
            return Response({'result': False, 'message': str(e)})
        # report_data = ReportDetailSerializer(report).data
        return Response({'result': True, 'data': report_data})
    return Response({'result': False, 'message': str(serializer.errors)})


@api_view(['POST'])
@transaction.atomic
@check_report_editable_status()
def restore_report_history(request, uid, id):
    report = get_object_or_404(Report, uid=uid)
    if report.is_public:
        return Response({'result': False, 'message': "报告已经发布"},
                        status=status.HTTP_400_BAD_REQUEST)
    histories = report.histories.filter(pk=id)
    if histories.exists():
        history = histories.first()
        savepoint = transaction.savepoint()
        try:
            report = restore_report(request, report, history)
        except Exception as e:
            transaction.savepoint_rollback(savepoint)
            return Response({'result': False, 'message': str(e)},
                            status=status.HTTP_400_BAD_REQUEST)
        report_data = ReportDetailSerializer(report).data
        return Response({'result': True, 'data': report_data})
    return Response({"result": False, "message": "不存在"})


def restore_report(request, report, history):
    current_user = request.user
    report_data = ReportDetailSerializer(report).data

    last_history = report.histories.order_by('-created_at').first()
    if last_history.created_at < report.updated_at:
        # 还原前  当前报告数据生成一个新版本 并创建操作记录
        new_number = last_history.number + 1 if last_history else 1
        data = {'report_data': json.dumps(report_data, ensure_ascii=False), 'author': request.user.id,
                'report': report.id, 'number': new_number}
        serializer = RevisionHistoryCreateSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
        else:
            raise Exception(str(serializer.errors))
        last_history_report_data = json.loads(last_history.report_data, encoding='utf-8')
        OperatingRecord.build_update_report_log(request.user, last_history_report_data, report_data, report,
                                                request=request)

    history_report_data = json.loads(history.report_data, encoding='utf-8')
    # 还原历史版本数据
    report.title = history_report_data['title']
    report.main_content_html = history_report_data['main_content_html']
    report.main_content_text = history_report_data['main_content_text'] if history_report_data.get(
        'main_content_text') else report_update_init_text
    report.main_content = json.dumps(history_report_data['main_content'], ensure_ascii=False)
    report.version_content = json.dumps(history_report_data['version_content'], ensure_ascii=False)
    report.show_next = history_report_data['show_next']
    report.show_services = history_report_data['show_services']
    report.show_plan = history_report_data['show_plan']
    report.last_operator = current_user
    report.save()
    report.quotation_plans.all().delete()
    for plan in history_report_data['quotation_plans']:
        price_detail = json.dumps(plan['price_detail'], ensure_ascii=False) if plan['price_detail'] else None
        QuotationPlan.objects.create(report=report, title=plan['title'], uid=get_report_uid(),
                                     price=plan['price'],
                                     period=plan['period'],
                                     projects=plan['projects'], services=plan['services'],
                                     price_detail=price_detail)
    # 创建新的历史版本
    remarks = '还原了第{}版历史记录'.format(history.number)
    last_history = report.histories.order_by('-created_at').first()
    new_number = last_history.number + 1 if last_history else 1
    data = {'report_data': history.report_data, 'author': request.user.id,
            'report': report.id, 'number': new_number, 'remarks': remarks}
    serializer = RevisionHistoryCreateSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
    else:
        raise Exception(str(serializer.errors))
    # 创建还原历史版本操作记录
    OperatingRecord.build_update_report_log(request.user, report_data, history_report_data, report, comment=remarks,
                                            request=request)
    return report


@api_view(['POST'])
def upload_files(request):
    if 'file' not in request.data:
        return Response({'result': False, 'message': '缺少有效文件'})
    request_data = {}
    file = request.data['file']
    request_data['submitter'] = request.user.id
    request_data['file'] = file
    request_data['filename'] = file.name
    request_data['uid'] = gen_uuid()
    serializer = ReportFileSerializer(data=request_data)
    if serializer.is_valid():
        report_file = serializer.save()
        download_report_file(report_file)
        data = ReportFileSerializer(report_file).data
        return Response({'result': True, 'data': data})
    return Response({'result': False, 'message': str(serializer.errors)},
                    status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def upload_mind_maps(request):
    if 'file' not in request.data:
        return Response({'result': False, 'message': '缺少有效文件'})
    if not request.data.get('file').name.endswith('opml'):
        return Response({"result": False, "message": "脑图文件只支持opml格式, 需要上传图片请直接插入图片"})
    request_data = {}

    file = request.data['file']
    request_data['submitter'] = request.user.id
    request_data['file'] = file
    request_data['filename'] = file.name
    request_data['uid'] = gen_uuid()

    if request.is_secure():
        protocol = 'https'
    else:
        protocol = 'http'
    request_domain = protocol + "://" + request.get_host()

    serializer = MindMapSerializer(data=request_data)
    if serializer.is_valid():
        mind_map = serializer.save()
        result = download_and_convert_opml_to_json_and_img(mind_map, request_domain=request_domain)
        if not result:
            return Response({'result': False, 'message': "脑图图片生成失败"},
                            status=status.HTTP_400_BAD_REQUEST)
        data = MindMapSerializer(mind_map).data
        return Response({'result': True, 'data': data})
    return Response({'result': False, 'message': str(serializer.errors)},
                    status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@transaction.atomic
def upload_frame_diagrams(request):
    user_id = request.user.id
    if 'file' not in request.data:
        return Response({'result': False, 'message': '缺少有效文件'})
    files = request.data.getlist('file')
    tags = request.data.get('tags', [])
    if isinstance(tags, str):
        tags = re.sub(r'[;；,，]', ' ', tags).split()
    savepoint = transaction.savepoint()
    is_standard = False
    if 'is_standard' in request.data and request.data['is_standard'] in [True, '1', 1, 'true']:
        is_standard = True
    frame_diagrams = []
    for file in files:
        data = {}
        data['is_standard'] = is_standard
        data['submitter'] = user_id
        data['file'] = file
        data['filename'] = file.name
        data['uid'] = gen_uuid()
        serializer = FrameDiagramSerializer(data=data)
        if serializer.is_valid():
            frame_diagram = serializer.save()
            frame_diagrams.append(frame_diagram)
            if tags:
                add_tags(frame_diagram, tags)
            download_frame_diagram(frame_diagram)
        else:
            transaction.savepoint_rollback(savepoint)
            return Response({'result': False, 'message': str(serializer.errors)},
                            status=status.HTTP_400_BAD_REQUEST)
    if len(frame_diagrams) > 1:
        data = FrameDiagramSerializer(frame_diagrams, many=True).data
    elif len(frame_diagrams) == 1:
        data = FrameDiagramSerializer(frame_diagrams[0], many=False).data
    else:
        data = None
    return Response({'result': True, 'data': data})


def add_tags(frame_diagram, tags: list):
    from reports.models import FrameDiagramTag
    for tag in tags:
        FrameDiagramTag.objects.get_or_create(name=tag)
    tag_list = FrameDiagramTag.objects.filter(name__in=tags)
    frame_diagram.tags.add(*tag_list)


@api_view(['GET'])
def frame_diagram_filter_data(request):
    tags = FrameDiagramTag.objects.all()
    tags_data = FrameDiagramTagSerializer(tags, many=True).data
    return Response({'result': True, 'data': {'tags': tags_data}})


class ReportCommentPointList(APIView):
    def get(self, request, uid):
        report = get_object_or_404(Report, uid=uid)
        ordering = request.GET.get('ordering', "created_at")
        comment_points = report.comment_points.all()
        if ordering:
            comment_points = comment_points.order_by(ordering)
        data = ReportCommentPointWithCommentsSerializer(comment_points, many=True).data
        return Response({"result": True, 'data': data})

    def post(self, request, uid):
        report = get_object_or_404(Report, uid=uid)
        request_data = deepcopy(request.data)
        request_data['report'] = report.id
        request_data['uid'] = get_report_uid()
        if {'content_type_app', 'content_type_model', 'object_id'}.issubset(set(request_data.keys())):
            content_type = ContentType.objects.filter(app_label=request_data['content_type_app'],
                                                      model=request_data['content_type_model'])
            if not content_type.exists():
                return Response({'result': False, 'message': 'ContentType matching query does not exist'})
            content_type = content_type.first()
            object_id = int(request_data['object_id'])
            request_data['content_type'] = content_type.id
            request_data['object_id'] = object_id
        serializer = ReportCommentPointSerializer(data=request_data)
        if serializer.is_valid():
            serializer.save()
            return Response({"result": True, 'data': serializer.data})
        return Response({"result": False, "message": str(serializer.errors)})


class ReportCommentPointDetail(APIView):
    def get(self, request, uid):
        comment_point = get_object_or_404(CommentPoint, uid=uid)
        serializer = ReportCommentPointWithCommentsSerializer(comment_point)
        return Response({"result": True, 'data': serializer.data})

    def post(self, request, uid):
        comment_point = get_object_or_404(CommentPoint, uid=uid)
        if not request.data.get('content', None):
            return Response({"result": False, "message": "缺少评论内容"})

        top_user = request.top_user
        comment = Comment(content_object=comment_point, content=request.data['content'],
                          creator=top_user)
        if top_user.is_employee:
            comment.author = top_user.user
        elif top_user.is_developer:
            comment.developer = top_user.developer
        comment.save()
        serializer = ReportCommentPointWithCommentsSerializer(comment_point)
        return Response({"result": True, 'data': serializer.data})

    def delete(self, request, uid):
        comment_point = get_object_or_404(CommentPoint, uid=uid)
        report = comment_point.report
        origin = deepcopy(comment_point)
        comment_point.delete()
        return Response({"result": True})


class ReportCommentPointCommentList(APIView):
    def get(self, request, uid):
        params = request.GET
        comment_point = get_object_or_404(CommentPoint, uid=uid)
        comments = comment_point.comments.all()
        order_by_list = ['-is_sticky']
        order_by = params.get('order_by', 'created_at')
        order_dir = params.get('order_dir', 'desc')
        if order_dir == 'desc':
            order_by = '-' + order_by
        order_by_list.append(order_by)
        comments = comments.order_by(*order_by_list)
        data = CommentSerializer(comments, many=True).data
        return Response({"result": True, 'data': data})

    def post(self, request, uid):
        comment_point = get_object_or_404(CommentPoint, uid=uid)
        if not request.data.get('content', None):
            return Response({"result": False, "message": "缺少评论内容"})

        top_user = request.top_user
        comment = Comment(content_object=comment_point, content=request.data['content'],
                          creator=top_user)
        if top_user.is_employee:
            comment.author = top_user.user
        elif top_user.is_developer:
            comment.developer = top_user.developer
        comment.save()

        return Response({"result": True, 'data': None})


def clean_comment_content(data):
    if isinstance(data, list):
        for item in data:
            clean_comment_content(item)
    if isinstance(data, dict):
        keys = list(data.keys())
        for item_key in keys:
            if item_key == "comment":
                del data[item_key]
                continue
            if item_key == "comment_uid":
                del data[item_key]
                continue
            if item_key == 'class' and 'active' in data[item_key]:
                if isinstance(data[item_key], list):
                    data[item_key].remove('active')
                if isinstance(data[item_key], str):
                    data[item_key] = data[item_key].replace('active', '')
            clean_comment_content(data[item_key])
    return data


@api_view(['POST'])
def return_report_page(request):
    report_uid = request.data.get('report_uid')
    if not report_uid:
        return Response({"result": False, "message": "参数report_uid为必填"})
    report = Report.objects.filter(uid=report_uid)
    if not report.exists():
        return Response({"result": False, "message": "report不存在"})
    report = report.first()
    report_user_return(report, request.user)
    return Response({"result": True, 'data': {}, 'message': '数据保存成功'})


@api_view(['POST'])
def leave_report_page(request):
    report_uid = request.data.get('report_uid')
    if not report_uid:
        return Response({"result": False, "message": "参数report_uid为必填"})
    report = Report.objects.filter(uid=report_uid)
    if not report.exists():
        return Response({"result": False, "message": "report不存在"})
    report = report.first()
    report_user_leave(report, request.user)
    return Response({"result": True, 'data': {}, 'message': '数据保存成功'})


@api_view(['GET'])
def report_page_users(request):
    report_uid = request.GET.get('report_uid')
    if not report_uid:
        return Response({"result": False, "message": "参数report_uid为必填"})
    report = Report.objects.filter(uid=report_uid)
    if not report.exists():
        return Response({"result": False, "message": "report不存在"})
    report = report.first()
    result_data = get_report_users_data(request, report)
    return Response({"result": True, 'data': result_data, 'message': '数据获取成功'})


def get_report_users_data(request, report):
    user = request.user
    reports_data = cache.get('reports_editable_data', {})
    is_updated = False
    result_data = {'is_editable': True, 'editing_user': None, 'viewing_users': []}
    now = timezone.now()
    current_user_data = {'username': user.username, 'updated_at': now}
    if reports_data:
        if report.uid in reports_data:
            report_data = reports_data[report.uid]
            # 编辑人员数据 如果最近编辑时间为五分钟前 置空
            editable_data = report_data['editable_data']
            updated_at = editable_data['updated_at']
            if updated_at:
                if updated_at < timezone.now() - timedelta(minutes=3):
                    report_data['editable_data'] = {'username': None, 'updated_at': None}
                    is_updated = True
                else:
                    editing_username = editable_data['username']
                    if user.username != editing_username:
                        result_data['is_editable'] = False
                    editing_user = User.objects.get(username=editing_username)
                    editing_user_data = UserBasicSerializer(editing_user).data
                    result_data['editing_user'] = editing_user_data
            # 查看人员数据
            if "users" in report_data:
                users = report_data['users']
                new_users = {}
                for username, user_data in users.items():
                    updated_at = user_data['updated_at']
                    if updated_at > timezone.now() - timedelta(minutes=3):
                        new_users[username] = users[username]
                    else:
                        is_updated = True
                if user.username not in users:
                    is_updated = True
                new_users[user.username] = current_user_data
                report_data['users'] = new_users
                username_list = new_users.keys()
                user_list = User.objects.filter(username__in=username_list)
                users_data = UserBasicSerializer(user_list, many=True).data
                result_data['viewing_users'] = users_data
    cache.set('reports_editable_data', reports_data, None)
    if is_updated:
        send_report_editable_data_update_reminder.delay(report.id)
    return result_data


class ReportEvaluationList(APIView):
    def get(self, request, report_uid):
        report = get_object_or_404(Report, uid=report_uid)
        queryset = report.evaluations.order_by('-created_at')
        return build_pagination_response(request, queryset, ReportEvaluationViewSerializer)

    def post(self, request, report_uid):
        report = get_object_or_404(Report, uid=report_uid)
        request_data = deepcopy(request.data)
        request_data['report'] = report.id
        request_data['user_agent'] = request.META.get('HTTP_USER_AGENT')
        request_data['host'] = request.META.get('REMOTE_HOST')
        request_data['ip'] = get_request_ip(request)

        serializer = ReportEvaluationSerializer(data=request_data)
        uid = request.data.get('uid', None)
        if uid:
            origin_obj = ReportEvaluation.objects.filter(uid=uid, report_id=report.id).first()
            if origin_obj:
                serializer = ReportEvaluationSerializer(origin_obj, data=request_data)
        if serializer.is_valid():
            evaluation = serializer.save()
            return api_success()
        return api_bad_request(serializer.errors)


@superuser_required()
@api_view(['GET'])
def publish_applicant_data_export(request):
    from wsgiref.util import FileWrapper

    from django.http import FileResponse
    from django.utils.encoding import escape_uri_path
    from django.conf import settings

    import xlwt
    from xlwt import Workbook

    reports = Report.objects.filter(publish_applicant_id__isnull=False)
    # reports = Report.objects.all()
    data = ReportPublishApplicantSerializer(reports, many=True).data

    w = Workbook()  # 创建一个工作簿
    ws = w.add_sheet("报告审核统计表")  # 创建一个工作表

    export_fields = [
        {'field_name': 'status_display', 'verbose_name': '状态', 'col_width': 12},
        {'field_name': 'report_title', 'verbose_name': '报告名称', 'col_width': 18},
        {'field_name': 'proposal_title', 'verbose_name': '需求名称', 'col_width': 18},

        {'field_name': 'publish_applicant', 'verbose_name': '发布申请人', 'col_width': 8},
        {'field_name': 'reviewer', 'verbose_name': '审核人', 'col_width': 8},
        {'field_name': 'publisher', 'verbose_name': '发布人', 'col_width': 8},

        {'field_name': 'created_at', 'verbose_name': '创建时间', 'col_width': 16},

        {'field_name': 'publish_applicant_at', 'verbose_name': '申请发布时间', 'col_width': 16},
        {'field_name': 'published_at', 'verbose_name': '发布时间', 'col_width': 16},

        {'field_name': 'publish_applicant_during', 'verbose_name': '发布审核时长', 'col_width': 26},

    ]

    for index_num, field in enumerate(export_fields):
        ws.write(0, index_num, field['verbose_name'])

    for index_num, lead_data in enumerate(data):
        for field_num, field in enumerate(export_fields):
            field_value = lead_data.get(field['field_name'], '')
            ws.write(index_num + 1, field_num, field_value)

    for i in range(len(export_fields)):
        ws.col(i).width = 256 * export_fields[i]['col_width']

    path = settings.MEDIA_ROOT + 'report_publish_applicants.xls'
    w.save(path)  # 保存
    wrapper = FileWrapper(open(path, 'rb'))
    filename = "报告审核统计表-{}.xls".format(datetime.now().strftime('%y_%m_%d_%H_%M'))
    response = FileResponse(wrapper, content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = "attachment; filename*=utf-8''{}".format(escape_uri_path(filename))
    return response
