import json
import os
import re
from copy import deepcopy
from datetime import datetime, timedelta

from django.conf import settings
from django.core.cache import cache
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from farmbase.permissions_utils import func_perm_required, func_perm_any_required, superuser_required
from farmbase.utils import this_month_start, this_month_end
from logs.models import BrowsingHistory
from reports import pdf_gen
from reports.quip_html_parser import HTMLParser
from reports.markdown_parser import ReportMarkDownParser
from reports.quill_html_parser import QuillHTMLParser
from reports.models import Grade, Report
from reports.serializers import ReportDetailSerializer, ReportSimpleSerializer, ReportDetailPageViewSerializer
from reports.utils import report_user_return
from oauth import we_chat


@require_http_methods(['GET'])
def view(request, uid):
    report = get_object_or_404(Report, uid=uid, is_public=True)
    return render_report(request, report)


def preview(request, uid):
    report = get_object_or_404(Report, uid=uid)
    return render_report(request, report, is_preview=True)


def render_report(request, report, is_preview=False):
    if report.is_expired() and not is_preview:
        return render(request, 'reports/report-past.html')

    if report.creation_source == 'farm':
        return render_report_view(request, report, 'farm', is_preview=is_preview)
    if report.markdown != '':
        return render_report_view(request, report, 'markdown', is_preview=is_preview)
    if report.html:
        return render_report_view(request, report, 'quip_link', is_preview=is_preview)
    return Http404


# 微信数据

def get_wx_sign_data(request):
    url = request.build_absolute_uri()
    if settings.USE_HTTPS:
        url = url.replace("http://", "https://")
    data = {'appId': '', 'signature': '', 'timestamp': '', 'nonceStr': ''}
    if not settings.DEVELOPMENT:
        data = we_chat.get_default_sign_data(url)
    return data


def get_report_view_data(request, report, creation_source):
    protocol = 'https' if request.is_secure() else 'http'
    request_domain = protocol + "://" + request.get_host()

    # 报告内容
    content_list = []
    # 计划方案
    plans = []

    version_content = None
    if creation_source == 'farm':
        parser = QuillHTMLParser(report.main_content_html, request_domain=request_domain, request=request)
        parser.build_html()
        content_list = parser.sections
        for content in content_list:
            content.content = replace_content_image(content.content)
    elif creation_source == 'quip_link':
        parser = HTMLParser(report.html, request_domain=request_domain)
        parser.build_html()
        # 版本历史
        version_content = parser.doc_records
        # 报告内容
        content_list = parser.sections
        for content in content_list:
            content.content = replace_content_image(content.content)
        # 时间及金额预估
        plans = parser.get_plans()
    elif creation_source == 'markdown':
        parser = ReportMarkDownParser(report.markdown)
        parser.parse()
        # 版本历史
        version_content = parser.docRecords
        # 报告内容
        content_list = parser.sections
        for content in content_list:
            content.content = replace_content_image(content.content)
        # 时间及金额预估
        plans = parser.plans
    report_view_data = deepcopy(ReportDetailPageViewSerializer(report).data)
    report_view_data['catalogue'] = parser.catalogue
    report_view_data['plans'] = plans

    report_view_data['content_list'] = content_list
    if version_content is not None:
        report_view_data['version_content'] = version_content
    return report_view_data


def render_report_view(request, report, create_source, is_preview=False):
    wx_data = get_wx_sign_data(request)
    report_data = ReportSimpleSerializer(report).data
    report_view_data = get_report_view_data(request, report, create_source)
    result_data = {'report': report_view_data, "report_data_str": json.dumps(report_data), 'is_preview': is_preview,
                   "wx_data": wx_data}
    template_html = 'reports/report_view_proposal_new.html'
    if report_data['report_type'] == 'lead':
        template_html = 'reports/report_view_lead_new.html'
    return render(request, template_html, result_data)


def pdf(request, uid):
    if not os.path.isfile(pdf_gen.report_path(uid)):
        pdf_gen.gen(request, uid)
    file = open(pdf_gen.report_path(uid), 'rb')
    report = Report.objects.get(uid=uid)
    filename = report.title + report.version
    response = HttpResponse(file, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename={}.pdf'.format(
        filename)
    return response


def replace_content_image(htmltext):
    p = re.compile('(<img src="(\S+)"[\s\S]*?\>)')
    for m in p.finditer(htmltext):
        img_text = m.group(1)
        if 'gear-custom-module' in img_text:
            continue
        src = m.group(2)
        htmltext = htmltext.replace(m.group(1), build_content_image(src))
    return htmltext


def build_content_image(src):
    return '<a class="content-image-container">' \
           '<img class="content-image" src="{}" alt="">' \
           '</a>'.format(src)


def mindmap_view(request):
    json_url = request.GET.get('json_url')
    return render(request, 'reports/report-mindmap.html', {'json_url': json_url})


@func_perm_required('view_report_frame_diagrams')
def upload_frame_diagrams(request):
    return render(request, 'reports/upload-frame-diagrams.html')


@func_perm_required('view_report_frame_diagrams')
def frame_diagrams(request):
    return render(request, 'reports/frame-diagrams.html')


def new_report(request, uid):
    report = get_object_or_404(Report, uid=uid)
    report_data = ReportSimpleSerializer(report).data
    if report.is_public:
        return render_report(request, report)
    report_user_return(report, request.user)
    return render(request, 'reports/new-report.html',
                  {'report': report, "report_data_str": json.dumps(report_data, ensure_ascii=False),
                   "report_data": report_data})


@superuser_required()
def reports_pv(request):
    month_str = request.GET.get('month_str', None)
    start_day = request.GET.get('start_day', None)
    end_day = request.GET.get('end_day', None)
    if start_day:
        start_day = datetime.strptime(start_day, '%Y-%m-%d')
        if end_day:
            end_day = datetime.strptime(end_day, '%Y-%m-%d')
        else:
            end_day = timezone.now().date()
        month_str = start_day.strftime('%Y-%m-%d') + '-' + end_day.strftime('%Y-%m-%d')
    elif month_str:
        month = datetime.strptime(month_str, '%Y-%m')
        start_day = this_month_start(month)
        end_day = this_month_end(month)
    else:
        now = timezone.now().date()
        end_day = now
        start_day = now - timedelta(days=30)
        month_str = '最近一个月'
    data = {"month_str": month_str, "pv_total": 0, 'uv_total': 0, 'pv_list': []}
    report_content_type = ContentType.objects.get(app_label='reports', model='report')
    ips = set()
    logs = BrowsingHistory.objects.all().filter(content_type=report_content_type, created_at__gte=start_day,
                                                created_at__lte=end_day, visitor_id__isnull=True).exclude(
        ip_address='106.120.244.82').order_by(
        '-created_date').distinct()
    data['pv_total'] = logs.count()
    for log in logs:
        if log.ip_address not in ips:
            data['pv_list'].append(log)
            ips.add(log.ip_address)
    data['uv_total'] = len(data['pv_list'])
    return render(request, 'reports/reports_pv.html', data)
