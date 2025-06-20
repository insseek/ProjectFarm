from django.urls import path

from . import api

app_name = 'exports_api'
urlpatterns = [
    # 工程师数据统计   添加日期  项目总数  总报酬
    path(r'developers/excel', api.developers_excel, name='developers_excel'),
    # 全部项目列表 项目名 项目经理 项目创建时间 项目完成时间  项目BD
    path(r'projects/excel', api.projects_excel, name='projects_excel'),
    # 线索的导出
    path(r'leads/excel', api.leads_excel, name='leads_excel'),
    # 需求导出
    path(r'proposals/csv', api.proposals_csv, name='proposals_csv'),
    path(r'proposals/excel', api.proposals_excel, name='proposals_excel'),
    # 未评分的项目工程师列表导出
    path(r'unevaluated_jobs/excel', api.unevaluated_jobs_excel, name='unevaluated_jobs_excel'),
    # 未付清的项目工程师列表导出
    path(r'unpaid_jobs/excel', api.unpaid_jobs, name='unpaid_jobs_excel'),

    # 工程师打款页面
    path(r'jobs/payments/export', api.export_job_payments, name='export_job_payments'),

    # 项目收款的导出
    path(r'projects/payments/export', api.export_projects_payments, name='export_projects_payments'),

    # 工时统计的导出
    path(r'projects/work_hour_plans/excel', api.export_project_work_hour_plans, name='export_project_work_hour_plans'),
]
