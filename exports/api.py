from datetime import datetime, timedelta
from decimal import Decimal
from wsgiref.util import FileWrapper
from copy import deepcopy
import csv

from django.contrib.auth.models import User
from django.http import HttpResponse
from rest_framework.decorators import api_view

from wsgiref.util import FileWrapper
from django.http import FileResponse
from django.utils.encoding import escape_uri_path
from django.conf import settings
import xlwt
from xlwt import Workbook

from farmbase.permissions_utils import func_perm_required, superuser_required
from gearfarm.utils.farm_response import api_bad_request, api_success
from gearfarm.utils.common_utils import this_week_end
from finance.models import JobPayment, ProjectPayment
from projects.models import JobPosition, Project
from exports.serializers import JobExportSerializer, JobUnevaluatedExportSerializer, \
    ProjectWithJobPositionExportSerializer, ProjectExportSerializer, ProjectPaymentExportSerializer, \
    DeveloperWithRegularExportSerializer
from clients.models import Lead
from clients.serializers import LeadExportSerializer
from proposals.models import Proposal
from proposals.serializers import ProposalExportSerializer
from exports.utils import build_excel_response
from developers.models import Developer
from projects.models import WorkHourRecord, ProjectWorkHourPlan


@api_view(['GET'])
@func_perm_required('view_all_developers')
def unpaid_jobs(request):
    jobs = JobPosition.objects.filter(project__done_at__isnull=True).order_by('created_at')
    jobs_list = []
    for j in jobs:
        if not j.is_fully_paid:
            jobs_list.append(j)
    export_data = JobExportSerializer(jobs_list, many=True).data
    export_fields = [
        {'field_name': 'developer_name', 'verbose_name': '工程师', 'col_width': 10},
        {'field_name': 'project_name', 'verbose_name': '项目名称', 'col_width': 20},
        {'field_name': 'project_status_display', 'verbose_name': '项目阶段', 'col_width': 10},
        {'field_name': 'manager_name', 'verbose_name': '项目经理', 'col_width': 10},

        {'field_name': 'role_name', 'verbose_name': '岗位名称', 'col_width': 15},
        {'field_name': 'created_at', 'verbose_name': '添加日期', 'col_width': 15},
        {'field_name': 'days', 'verbose_name': '历时', 'col_width': 15},

        {'field_name': 'total_amount', 'verbose_name': '总金额(元)', 'col_width': 10},
        {'field_name': 'paid_payment_amount', 'verbose_name': '已付金额(元)', 'col_width': 10},

        {'field_name': 'last_paid_payment_amount', 'verbose_name': '最近打款金额(元)', 'col_width': 15},
        {'field_name': 'last_paid_payment_date', 'verbose_name': '最近打款日期', 'col_width': 15},
    ]

    response = build_excel_response(export_data, export_fields, 'UnpaidJobs', verbose_filename='未付款工程师列表')
    return response


@api_view(['GET'])
@func_perm_required('view_all_leads')
def leads_excel(request):
    lead_list = Lead.objects.all().order_by('created_at')
    status = request.GET.get('status', None)
    if status == 'closed':
        lead_list = lead_list.filter(Q(status='no_deal') | Q(status='invalid'))
    elif status == 'ongoing':
        lead_list = lead_list.filter(Q(status='contact') | Q(status='proposal'))
    leads_data = LeadExportSerializer(lead_list, many=True).data
    export_fields = [
        {'field_name': 'id', 'verbose_name': 'ID', 'col_width': 10},
        {'field_name': 'created_at', 'verbose_name': '创建时间', 'col_width': 15},
        {'field_name': 'status_display', 'verbose_name': '状态', 'col_width': 10},
        {'field_name': 'name', 'verbose_name': '名称', 'col_width': 20},
        {'field_name': 'description', 'verbose_name': '简介', 'col_width': 25},
        {'field_name': 'remarks', 'verbose_name': '提交备注', 'col_width': 25},
        {'field_name': 'proposal', 'verbose_name': '关联需求ID', 'col_width': 10},
        {'field_name': 'closed_at', 'verbose_name': '关闭时间', 'col_width': 15},
        {'field_name': 'closed_reason', 'verbose_name': '关闭理由', 'col_width': 18},
        {'field_name': 'creator_username', 'verbose_name': '提交人', 'col_width': 10},
        {'field_name': 'salesman_username', 'verbose_name': 'BD', 'col_width': 10},

        {'field_name': 'source_display', 'verbose_name': '来源', 'col_width': 12},
        {'field_name': 'source_info', 'verbose_name': '来源详情', 'col_width': 25},

        {'field_name': 'contact_name', 'verbose_name': '客户姓名', 'col_width': 15},
        {'field_name': 'company_name', 'verbose_name': '公司', 'col_width': 15},
        {'field_name': 'contact_job', 'verbose_name': '职位', 'col_width': 12},
        {'field_name': 'phone_number', 'verbose_name': '电话', 'col_width': 12},
        {'field_name': 'address', 'verbose_name': '地区', 'col_width': 12}
    ]
    response = build_excel_response(leads_data, export_fields, 'LeadStatisticTable', verbose_filename='线索数据统计')
    return response


@api_view(['GET'])
def projects_excel(request):
    queryset = Project.objects.order_by('-created_at')
    data = ProjectExportSerializer(queryset, many=True).data
    export_fields = [
        {'field_name': 'name', 'verbose_name': '项目名', 'col_width': 20},
        {'field_name': 'manager_username', 'verbose_name': '项目经理', 'col_width': 10},
        {'field_name': 'created_at', 'verbose_name': '项目创建时间', 'col_width': 12},
        {'field_name': 'done_at', 'verbose_name': '项目完成时间', 'col_width': 12},
        {'field_name': 'bd_username', 'verbose_name': '项目BD', 'col_width': 12},
    ]
    response = build_excel_response(data, export_fields, 'AllProjectsTable', verbose_filename='全部项目列表')
    return response


def proposals_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="需求列表导出.csv"'
    writer = csv.writer(response, dialect='excel')
    writer.writerow(['提交日期', '状态', '提交人', '需求名称', '来源', '产品经理', '联系打卡', '报告打卡', '成单/关闭时间', '未成单理由'])
    proposals = Proposal.objects.order_by('created_at').all()
    for p in proposals:
        writer.writerow([
            p.created_at,
            p.get_status_display(),
            p.submitter if p.submitter_id and User.objects.filter(pk=p.submitter_id).exists() else None,
            p.name or p.description,
            p.source_display,
            p.pm if p.pm_id and User.objects.filter(pk=p.pm_id).exists() else None,
            p.contact_at,
            p.report_at,
            p.closed_at,
            "%s (%s)" % (p.get_closed_reason_text, p.closed_reason_remarks)
        ])
    return response


#
@superuser_required()
def proposals_excel(request):
    lead_list = Proposal.objects.all().order_by('created_at')
    no_lead = request.GET.get('no_lead', None)
    if no_lead:
        lead_list = lead_list.filter(lead_id__isnull=True)
    leads_data = ProposalExportSerializer(lead_list, many=True).data
    export_fields = [
        {'field_name': 'id', 'verbose_name': 'ID', 'col_width': 10},
        {'field_name': 'created_at', 'verbose_name': '提交日期', 'col_width': 15},
        {'field_name': 'status_display', 'verbose_name': '状态', 'col_width': 10},
        {'field_name': 'submitter_username', 'verbose_name': '提交人', 'col_width': 10},
        {'field_name': 'name', 'verbose_name': '需求名称', 'col_width': 20},
        {'field_name': 'description', 'verbose_name': '简介', 'col_width': 25},

        {'field_name': 'source_display', 'verbose_name': '来源', 'col_width': 12},
        {'field_name': 'source_info', 'verbose_name': '来源详情', 'col_width': 25},

        {'field_name': 'pm_username', 'verbose_name': '产品经理', 'col_width': 10},

        {'field_name': 'contact_at', 'verbose_name': '联系打卡', 'col_width': 15},
        {'field_name': 'report_at', 'verbose_name': '报告打卡', 'col_width': 15},
        {'field_name': 'closed_at', 'verbose_name': '成单/关闭时间', 'col_width': 15},

        {'field_name': 'closed_reason', 'verbose_name': '未成单理由', 'col_width': 25},
        {'field_name': 'lead_name', 'verbose_name': '关联线索', 'col_width': 15},
    ]
    response = build_excel_response(leads_data, export_fields, 'ProposalStatisticTable', verbose_filename='需求数据统计')
    return response


@superuser_required()
def unevaluated_jobs_excel(request):
    jobs = JobPosition.objects.filter(project__done_at__isnull=False, job_standard_score__isnull=True).order_by(
        '-project__done_at')
    export_data = JobUnevaluatedExportSerializer(jobs, many=True).data
    export_fields = [
        {'field_name': 'project_name', 'verbose_name': '项目名称', 'col_width': 20},
        {'field_name': 'project_done_at', 'verbose_name': '项目阶段', 'col_width': 15},
        {'field_name': 'manager_name', 'verbose_name': '项目经理', 'col_width': 10},

        {'field_name': 'developer_name', 'verbose_name': '工程师', 'col_width': 10},
        {'field_name': 'role_name', 'verbose_name': '岗位名称', 'col_width': 15},
        {'field_name': 'developer_is_active', 'verbose_name': '在职', 'col_width': 15},

        {'field_name': 'total_amount', 'verbose_name': '总金额(元)', 'col_width': 10},
    ]
    response = build_excel_response(export_data, export_fields, 'unevaluated_projects_jobs',
                                    verbose_filename='未评分的项目工程师职位')
    return response


def developers_excel(request):
    '''
    人是需要被克服的 东西:克服 压力 欲望 道德 颓废
    不是阉割 而是转化升华:迎接 生命 快乐 超越 创造
    :param request:
    :return:
    '''
    from developers.serializers import DeveloperStatisticSerializer, Developer
    developers = Developer.objects.order_by('-status')
    developer_data = DeveloperStatisticSerializer(developers, many=True).data
    export_fields = [
        {'field_name': 'name', 'verbose_name': '姓名', 'col_width': 10},
        {'field_name': 'location', 'verbose_name': '地点', 'col_width': 10},
        {'field_name': 'role_names', 'verbose_name': '职位', 'col_width': 10},
        {'field_name': 'created_at', 'verbose_name': '添加日期', 'col_width': 15},
        {'field_name': 'status_display', 'verbose_name': '状态', 'col_width': 10},
        {'field_name': 'project_total', 'verbose_name': '项目总数', 'col_width': 10},
        {'field_name': 'payment_total', 'verbose_name': '总报酬', 'col_width': 10},

    ]
    response = build_excel_response(developer_data, export_fields, 'DeveloperStatisticTable',
                                    verbose_filename='工程师数据统计')
    return response


@api_view(['GET'])
def export_job_payments(request):
    params = request.GET
    filter_date = params.get('date', None)
    status = params.get('status', None)
    projects = Project.objects.all()

    filename = 'JobPaymentStatisticTable.xls'
    file_path = settings.MEDIA_ROOT + filename

    queryset = JobPayment.objects.exclude(status=0)
    # 构建数据
    # 如果有筛选 筛选过滤
    if status or filter_date:
        filename = 'JobPaymentStatisticTable{}{}.xls'.format(status or '', filter_date or '')
        file_path = settings.MEDIA_ROOT + filename
        if status:
            queryset = queryset.filter(status=status)
        if filter_date and filter_date == 'this_week':
            week_end = this_week_end()
            queryset = queryset.filter(expected_at__lte=week_end)

    # 项目的职位打款
    project_payments = queryset.filter(position_id__isnull=False)
    project_ids = set([q.position.project_id for q in project_payments])
    queryset_ids = set([q.id for q in project_payments])
    projects = projects.filter(pk__in=project_ids).order_by('created_at')
    projects_data = ProjectWithJobPositionExportSerializer(projects, many=True).data
    new_projects_data = []
    for project_data in projects_data:
        new_project_data = None
        for position_data in project_data['job_positions']:
            new_position_data = None
            for payment_data in position_data['payments']:
                if payment_data['id'] in queryset_ids:
                    if not new_position_data:
                        new_position_data = deepcopy(position_data)
                        new_position_data['payments'] = []
                    new_position_data['payments'].append(payment_data)
            if new_position_data:
                if not new_project_data:
                    new_project_data = deepcopy(project_data)
                    new_project_data['job_positions'] = []
                new_project_data['job_positions'].append(new_position_data)
        if new_project_data:
            new_projects_data.append(new_project_data)
    project_export_fields = [
        {'field_name': 'name', 'verbose_name': '项目名', 'col_width': 20},
        {'field_name': 'manager_username', 'verbose_name': '项目经理', 'col_width': 10},
        {'field_name': 'status_display', 'verbose_name': '项目阶段', 'col_width': 10},
        {'field_name': 'created_at', 'verbose_name': '项目创建时间', 'col_width': 12},
        {'field_name': 'done_at', 'verbose_name': '项目完成时间', 'col_width': 12},
    ]
    position_export_fields = [
        {'field_name': 'role_name', 'verbose_name': '职位', 'col_width': 15},
        {'field_name': 'developer_name', 'verbose_name': '工程师(收款姓名)', 'col_width': 15},
        {'field_name': 'total_amount', 'verbose_name': '总金额', 'col_width': 10},
        {'field_name': 'paid_payment_amount', 'verbose_name': '已打金额', 'col_width': 10},
    ]
    payment_export_fields = [
        {'field_name': 'amount', 'verbose_name': '本次打款金额', 'col_width': 12},
        {'field_name': 'expected_at', 'verbose_name': '期望日期', 'col_width': 12},
        {'field_name': 'completed_at', 'verbose_name': '完成日期', 'col_width': 12},
        {'field_name': 'status_display', 'verbose_name': '状态', 'col_width': 12},

        {'field_name': 'contract_name', 'verbose_name': '合同名称', 'col_width': 15},
        {'field_name': 'payee_name', 'verbose_name': '收款人户名', 'col_width': 15},
        {'field_name': 'payee_id_card_number', 'verbose_name': '收款人身份证号码', 'col_width': 15},
        {'field_name': 'payee_phone', 'verbose_name': '收款人手机号', 'col_width': 15},
        {'field_name': 'payee_opening_bank', 'verbose_name': '收款人开户行', 'col_width': 15},
        {'field_name': 'payee_account', 'verbose_name': '收款人收款账号', 'col_width': 15},
        {'field_name': 'remarks', 'verbose_name': '打款备注', 'col_width': 20},
    ]

    workbook = Workbook()  # 创建一个工作簿
    sheet_name = "项目职位工程师打款统计"
    export_fields_groups = (project_export_fields, position_export_fields, payment_export_fields)
    data_fields = ("job_positions", "payments")
    data = new_projects_data
    add_group_workbook_sheet(data, workbook, sheet_name, export_fields_groups, data_fields)

    # 固定工程师的职位打款
    contract_payments = queryset.filter(job_contract__contract_category='regular')
    developer_ids = set([q.developer_id for q in contract_payments])
    queryset_ids = set([q.id for q in contract_payments])
    projects = Developer.objects.filter(pk__in=developer_ids).order_by('created_at')
    developers_data = DeveloperWithRegularExportSerializer(projects, many=True).data
    new_developers_data = []
    for project_data in developers_data:
        new_project_data = None
        for position_data in project_data['regular_contracts']:
            new_position_data = None
            for payment_data in position_data['payments']:
                if payment_data['id'] in queryset_ids:
                    if not new_position_data:
                        new_position_data = deepcopy(position_data)
                        new_position_data['payments'] = []
                    new_position_data['payments'].append(payment_data)
            if new_position_data:
                if not new_project_data:
                    new_project_data = deepcopy(project_data)
                    new_project_data['regular_contracts'] = []
                new_project_data['regular_contracts'].append(new_position_data)
        if new_project_data:
            new_developers_data.append(new_project_data)

    developer_export_fields = [
        {'field_name': 'name', 'verbose_name': '工程师姓名', 'col_width': 10},
    ]
    contract_export_fields = [
        {'field_name': 'contract_name', 'verbose_name': '合同名称', 'col_width': 20},
        {'field_name': 'signed_at', 'verbose_name': '签约时间', 'col_width': 20},
        {'field_name': 'principal_name', 'verbose_name': '负责人', 'col_width': 15},
        {'field_name': 'total_amount', 'verbose_name': '总金额', 'col_width': 10},
        {'field_name': 'paid_payment_amount', 'verbose_name': '已打金额', 'col_width': 10},
    ]
    payment_export_fields = [
        {'field_name': 'amount', 'verbose_name': '本次打款金额', 'col_width': 12},
        {'field_name': 'expected_at', 'verbose_name': '期望日期', 'col_width': 12},
        {'field_name': 'completed_at', 'verbose_name': '完成日期', 'col_width': 12},
        {'field_name': 'status_display', 'verbose_name': '状态', 'col_width': 12},
        {'field_name': 'contract_name', 'verbose_name': '合同名称', 'col_width': 15},
        {'field_name': 'payee_name', 'verbose_name': '收款人户名', 'col_width': 15},
        {'field_name': 'payee_id_card_number', 'verbose_name': '收款人身份证号码', 'col_width': 15},
        {'field_name': 'payee_phone', 'verbose_name': '收款人手机号', 'col_width': 15},
        {'field_name': 'payee_opening_bank', 'verbose_name': '收款人开户行', 'col_width': 15},
        {'field_name': 'payee_account', 'verbose_name': '收款人收款账号', 'col_width': 15},
        {'field_name': 'remarks', 'verbose_name': '打款备注', 'col_width': 20},
    ]
    sheet_name = "固定工程师合同打款统计"
    export_fields_groups = (developer_export_fields, contract_export_fields, payment_export_fields)
    data_fields = ("regular_contracts", "payments")
    data = new_developers_data
    add_group_workbook_sheet(data, workbook, sheet_name, export_fields_groups, data_fields)

    workbook.save(file_path)  # 保存
    wrapper = FileWrapper(open(file_path, 'rb'))
    download_filename = '工程师打款记录{}.xls'.format(datetime.now().strftime('%Y.%m.%d'))
    if filter_date == 'this_week':
        download_filename = '工程师本周待处理打款记录{}.xls'.format(datetime.now().strftime('%Y.%m.%d'))
    response = FileResponse(wrapper, content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = "attachment; filename*=utf-8''{}".format(escape_uri_path(download_filename))
    response['Access-Control-Expose-Headers'] = 'Content-Disposition'
    return response


# 分层级分组展示  同级合并单元格 层级不限
def add_group_workbook_sheet(data, workbook, sheet_name, export_field_groups, children_fields):
    '''
    分层级的Excel构造  最后一级占一行   父级合并单元格
    一切主旋律都会成为绝唱 一切绝唱曾经都是主旋律
    一切保守的都曾经是激进的 一切激进的都会成为保守的
    一切现在的都诞生在远古 也诞生在未来
    远古的壁画是当时的主旋律意识 现在的主旋律是未来的远古壁画
    :param data:
    :param workbook:
    :param sheet_name:
    :param export_field_groups:
    :param children_fields:
    :return:
    '''
    ws = workbook.add_sheet(sheet_name)  # 创建一个工作表
    # 设置style
    alignment = xlwt.Alignment()  # Create Alignment
    # May be: HORZ_GENERAL, HORZ_LEFT, HORZ_CENTER, HORZ_RIGHT,
    # HORZ_FILLED, HORZ_JUSTIFIED, HORZ_CENTER_ACROSS_SEL, HORZ_DISTRIBUTED
    # alignment.horz = xlwt.Alignment.HORZ_CENTER  # 水平居中
    # May be: VERT_TOP, VERT_CENTER, VERT_BOTTOM, VERT_JUSTIFIED, VERT_DISTRIBUTED
    alignment.vert = xlwt.Alignment.VERT_CENTER  # 垂直居中
    style = xlwt.XFStyle()  # Create Style
    style.alignment = alignment  # Add Alignment to Style

    # 将组的数据只提取出field_name
    field_name_group = []
    export_fields = []
    for field_group in export_field_groups:
        export_fields.extend(field_group)
        field_group_field_names = [item['field_name'] for item in field_group]
        field_name_group.append(field_group_field_names)
    layer_sum = len(export_field_groups)

    # 写表头
    for index_num, field in enumerate(export_fields):
        ws.write(0, index_num, field['verbose_name'], style)
    # 设置表头宽度
    for i in range(len(export_fields)):
        ws.col(i).width = 256 * export_fields[i]['col_width']

    # 取数据 写入表格中
    # 数据分层级 同级合并单元格 层级不限 递归算法
    def write_children_data(parent_data, children_filed_name, top_row, layer_index):
        sum_row_count = 0
        # 第一层的时候 遍历自身 层级不是最后一个层级时 继续往下取  然后本层合并单元格
        if layer_index == 0:
            child_layer_index = layer_index + 1
            child_top_row = top_row
            for child_data in parent_data:
                row_count = write_children_data(child_data, children_fields[layer_index], child_top_row,
                                                child_layer_index)
                child_top_row += row_count
                sum_row_count += row_count
        else:
            # 最后一级 Excel填写数据
            if layer_index == layer_sum - 1:
                # 行
                row_start = top_row
                # 列
                column_start = 0
                for item in field_name_group[0:layer_index]:
                    column_start += len(item)
                # 最后一个层级 Excel填写数据
                for child_data in parent_data[children_filed_name]:
                    # 打款的数据
                    fields_value = []
                    for field_name in field_name_group[layer_index]:
                        fields_value.append(child_data.get(field_name))
                    for field_num, field_value in enumerate(fields_value):
                        field_column_num = column_start + field_num
                        ws.write(row_start, field_column_num, field_value, style)
                    row_start += 1
                    sum_row_count += 1
            else:
                # 层级不是最后一个层级时 继续往下取  然后本层合并单元格
                children = parent_data[children_filed_name]
                gran_child_filed_name = children_fields[layer_index]
                child_layer_index = layer_index + 1
                child_top_row = top_row
                for child_data in children:
                    row_count = write_children_data(child_data, gran_child_filed_name, child_top_row,
                                                    child_layer_index)
                    child_top_row += row_count
                    sum_row_count += row_count

            # 如果子集有数据  写入本层级的数据   并合并单元格
            if sum_row_count:
                fields_value = []
                for field_name in field_name_group[layer_index - 1]:
                    fields_value.append(parent_data.get(field_name, ''))
                # 列
                column_start = 0
                for item in field_name_group[0:layer_index - 1]:
                    column_start += len(item)

                parent_top_row = top_row
                parent_bottom_row = top_row + sum_row_count - 1
                for field_num, field_value in enumerate(fields_value):
                    field_column_num = column_start + field_num
                    ws.write_merge(parent_top_row, parent_bottom_row, field_column_num, field_column_num,
                                   field_value,
                                   style)
        return sum_row_count

    write_children_data(data, None, 1, 0)


@api_view(['GET'])
def export_projects_payments(request):
    filename = 'ProjectClientPaymentStatisticTable.xls'
    file_path = settings.MEDIA_ROOT + filename
    payments = ProjectPayment.objects.all()
    main_status = request.GET.get('main_status', None)
    # 近期收款的项目：    项目中包含进行中收款、 项目未完成
    if main_status == 'ongoing':
        payments = payments.filter(status='process')
    elif main_status == 'closed':
        payments = payments.exclude(status='process')
    payments = payments.order_by('-project_id', 'created_at')
    data_list = ProjectPaymentExportSerializer(payments, many=True).data
    w = Workbook()  # 创建一个工作簿
    ws = w.add_sheet("项目客户收款统计")  # 创建一个工作表
    export_fields = [
        {'field_name': 'status_display', 'verbose_name': '状态', 'col_width': 10},
        {'field_name': 'project_name', 'verbose_name': '项目名称', 'col_width': 18},
        {'field_name': 'contract_name', 'verbose_name': '合同名称', 'col_width': 18},
        {'field_name': 'capital_account', 'verbose_name': '付款账号/公司', 'col_width': 18},
        {'field_name': 'total_amount', 'verbose_name': '合同总额', 'col_width': 10},
        {'field_name': 'invoice_display', 'verbose_name': '需要发票', 'col_width': 10},
    ]
    export_fields_length = len(export_fields)
    export_submodule_fields = [
        {'field_name': 'receivable_amount', 'verbose_name': '收款-{}总金额', 'col_width': 10},
        {'field_name': 'receipted_amount', 'verbose_name': '收款-{}已收金额', 'col_width': 12},
        {'field_name': 'receipted_date', 'verbose_name': '收款-{}收款日期', 'col_width': 12},
        {'field_name': 'invoice_display', 'verbose_name': '收款-{}发票', 'col_width': 12},
    ]
    # 1、写表头
    for index_num, field in enumerate(export_fields):
        ws.write(0, index_num, field['verbose_name'])
        ws.col(index_num).width = 256 * field['col_width']

    # 循环4遍 默认四个阶段
    for i in range(0, 4):
        first_column_index = export_fields_length + i * 4
        for index_num, field in enumerate(export_submodule_fields):
            column_index = first_column_index + index_num
            ws.write(0, column_index, field['verbose_name'].format(i + 1))
            ws.col(column_index).width = 256 * field['col_width']
    # 1、写表头结束

    # 2、写数据
    for index_num, data in enumerate(data_list):
        for field_num, field in enumerate(export_fields):
            field_value = data[field['field_name']]
            ws.write(index_num + 1, field_num, field_value)
        # 写入阶段的列
        stages = data['stages']
        for i, stage in enumerate(stages):
            first_column_index = export_fields_length + i * 4
            for sub_index, field in enumerate(export_submodule_fields):
                column_index = first_column_index + sub_index
                field_value = stage[field['field_name']]
                ws.write(index_num + 1, column_index, field_value)

    w.save(file_path)  # 保存

    wrapper = FileWrapper(open(file_path, 'rb'))
    response = FileResponse(wrapper, content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = "attachment; filename*=utf-8''{}".format(escape_uri_path(filename))
    return response


def export_project_work_hour_data_candle(role, candle_data, work_hour_record):
    candle_data['{}_week_person_days'.format(role)] += Decimal(
        work_hour_record.week_consume_hours / 8).quantize(Decimal("0.1"), rounding="ROUND_HALF_UP")
    candle_data['{}_predict_residue'.format(role)] += work_hour_record.predict_residue_days
    candle_data['total_week_person_days'] += candle_data[
        '{}_week_person_days'.format(role)]
    candle_data['total_predict_residue'] += candle_data[
        '{}_predict_residue'.format(role)]


@api_view(['GET'])
def export_project_work_hour_plans(request):
    start_date_str = request.GET.get('start_date', None)
    end_date_str = request.GET.get('end_date', None)
    if not start_date_str or not end_date_str:
        return api_bad_request('请选择导出起止时间')
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    work_hour_records = WorkHourRecord.objects.filter(statistic_start_date=start_date, statistic_end_date=end_date)
    if not work_hour_records:
        return api_bad_request('没有符合当前所选时间的数据')
    work_hour_plan_data = {}
    for work_hour_record in work_hour_records:
        project = work_hour_record.project_work_hour_plan.project
        contract_names = [p.name for p in project.contracts.all() if p.name]
        contract_name = '，'.join(contract_names)
        work_hour_export_data = {'name': project.name,
                                 'contract_name': contract_name,
                                 'manager': project.manager.username,
                                 'manager_week_person_days': 0,
                                 'manager_predict_residue': 0,
                                 'product_manager_week_person_days': 0,
                                 'product_manager_predict_residue': 0,
                                 'tpm_week_person_days': 0,
                                 'tpm_predict_residue': 0,
                                 'designer_week_person_days': 0,
                                 'designer_predict_residue': 0,
                                 'test_week_person_days': 0,
                                 'test_predict_residue': 0,
                                 'developer_week_person_days': 0,
                                 'developer_predict_residue': 0,
                                 'total_week_person_days': 0,
                                 'total_predict_residue': 0,
                                 'statistic_date': end_date_str,
                                 }
        project_id = project.id
        if project_id not in work_hour_plan_data:
            work_hour_plan_data[project_id] = work_hour_export_data
        candle_data = work_hour_plan_data[project_id]
        export_project_work_hour_data_candle(work_hour_record.project_work_hour_plan.role, candle_data,
                                             work_hour_record)

    data = sorted(work_hour_plan_data.values(), key=lambda x: x['manager'], reverse=True)
    export_fields = [
        {'field_name': 'name', 'verbose_name': '项目名称', 'col_width': 10},
        {'field_name': 'contract_name', 'verbose_name': '合同名称', 'col_width': 10},
        {'field_name': 'manager', 'verbose_name': '项目经理', 'col_width': 10},
        {'field_name': 'manager_week_person_days', 'verbose_name': '周消耗人天(PMO)', 'col_width': 20},
        {'field_name': 'manager_predict_residue', 'verbose_name': '预计剩余人天(PMO)', 'col_width': 20},
        {'field_name': 'product_manager_week_person_days', 'verbose_name': '周消耗人天(PM)', 'col_width': 20},
        {'field_name': 'product_manager_predict_residue', 'verbose_name': '预计剩余人天(PM)', 'col_width': 20},
        {'field_name': 'tpm_week_person_days', 'verbose_name': '周消耗人天(TPM)', 'col_width': 20},
        {'field_name': 'tpm_predict_residue', 'verbose_name': '预计剩余人天(TPM)', 'col_width': 20},
        {'field_name': 'designer_week_person_days', 'verbose_name': '周消耗人天(UI)', 'col_width': 20},
        {'field_name': 'designer_predict_residue', 'verbose_name': '预计剩余人天(UI)', 'col_width': 20},
        {'field_name': 'test_week_person_days', 'verbose_name': '周消耗人天(QA)', 'col_width': 20},
        {'field_name': 'test_predict_residue', 'verbose_name': '预计剩余人天(QA)', 'col_width': 20},
        {'field_name': 'developer_week_person_days', 'verbose_name': '周消耗人天(RD)', 'col_width': 20},
        {'field_name': 'developer_predict_residue', 'verbose_name': '预计剩余人天(RD)', 'col_width': 20},
        {'field_name': 'total_week_person_days', 'verbose_name': '本周已消耗总人天', 'col_width': 20},
        {'field_name': 'total_predict_residue', 'verbose_name': '预计剩余总人天', 'col_width': 20},
        {'field_name': 'statistic_date', 'verbose_name': '统计时间', 'col_width': 20},
    ]
    response = build_excel_response(data, export_fields, 'ProjectWorkHourStatistic', verbose_filename='项目工时统计')

    return response
