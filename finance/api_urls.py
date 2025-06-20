from django.urls import path

from . import api

app_name = 'finance_api'
urlpatterns = [
    # 项目收款
    path(r'projects/<int:project_id>/payments', api.ProjectPaymentList.as_view(), name='project_payments'),
    path(r'projects/payments/<int:payment_id>', api.ProjectPaymentDetail.as_view(), name='project_payment_detail'),
    path(r'projects/payments/<int:payment_id>/close', api.close_project_payment, name='close_project_payment'),
    path(r'projects/payments/<int:payment_id>/open', api.open_project_payment, name='open_project_payment'),
    path(r'projects/payments/stages/<int:stage_id>', api.ProjectPaymentStageDetail.as_view(),
         name='project_payment_stage_detail'),
    path(r'projects/payments/stages/<int:stage_id>/expected_date', api.project_payment_stage_expected_date,
         name='project_payment_stage_expected_date'),
    path(r'projects/payments/stages/<int:stage_id>/receipt', api.project_payment_stage_receipt,
         name='project_payment_stage_receipt'),

    # 所有项目收款列表
    path(r'projects/payments', api.projects_payments, {'is_mine': False}, name='all_projects_payments'),
    path(r'projects/payments/mine', api.projects_payments, {'is_mine': True},
         name='my_projects_payments'),

    # 工程师合同
    path(r'jobs/contracts', api.JobContractList.as_view(), name='job_contract_list'),
    path(r'jobs/contracts/statistic', api.get_contract_statistic, name='job_contract_statistic'),

    path(r'jobs/contracts/<int:contract_id>', api.JobContractDetail.as_view(), name='job_contract_detail'),
    path(r'jobs/contracts/<int:contract_id>/payments', api.JobContractPaymentList.as_view(),
         name='job_contract_payments'),

    path(r'jobs/contracts/<int:contract_id>/payments/statistics', api.job_contract_payments_statistics,
         name='job_contract_payments_statistics'),

    # 【code review】提交字段和开发者详情的diff接口写一个接口
    path(r'jobs/contracts/<int:contract_id>/diff_developer', api.job_contract_detail_diff_developer,
         name='job_contract_detail_diff_developer'),

    path(r'jobs/contracts/<int:contract_id>/save', api.save_contract, name='save_contract'),
    path(r'jobs/contracts/<int:contract_id>/commit', api.submit_contract, name='submit_job_contract'),
    path(r'jobs/contracts/<int:contract_id>/terminate', api.terminate_job_contract, name='terminate_job_contract'),

    path(r'jobs/contracts/<int:contract_id>/reject', api.reject_contract, name='reject_contract'),
    path(r'jobs/contracts/<int:contract_id>/close', api.close_contract, name='close_contract'),
    path(r'jobs/contracts/<int:contract_id>/preview', api.preview_contract, name='preview_contract'),
    path(r'jobs/contracts/<int:contract_id>/get_signature', api.preview_contract_signature,
         name='preview_contract_signature'),
    path(r'jobs/contracts/download_template', api.download_explain_template, name='download_explain_template'),
    path(r'jobs/contracts/<int:contract_id>/download', api.download_contract, name='download_contract'),
    path(r'jobs/contracts/<int:contract_id>/confidentiality_agreement_preview', api.preview_confidentiality_agreement,
         name='preview_confidentiality_agreement'),
    path(r'jobs/contracts/<int:contract_id>/confidentiality_agreement_download', api.download_confidentiality_agreement,
         name='download_confidentiality_agreement'),
    path(r'jobs/contracts/download_design_template', api.download_design_delivery_list_template,
         name='download_design_delivery_list_template'),
    path(r'jobs/contracts/<int:contract_id>/generate_sign_flow', api.generate_sign_contract,
         name='generate_sign_contract'),
    path(r'jobs/contracts/<int:contract_id>/copy_sign_link', api.get_sign_link,
         name='get_sign_link'),
    path(r'jobs/contracts/call_back', api.call_back_handle,
         name='call_back_handle'),
    # 工程师打款
    path(r'jobs/payments', api.JobPaymentList.as_view(), name='jobs_payments'),
    path(r'jobs/<int:position_id>/payments', api.JobPositionPayments.as_view(), name='job_position_payments'),
    path(r'jobs/payments/<int:id>', api.JobPaymentDetail.as_view(), name='jobs_payment_detail'),
    path(r'jobs/payments/<int:payment_id>/start', api.change_payment_status, {'action_type': 'start'},
         name='start_payment'),
    path(r'jobs/payments/<int:payment_id>/finish', api.change_payment_status, {'action_type': 'finish'},
         name='finish_payment'),
    path(r'jobs/payments/<int:payment_id>/cancel', api.change_payment_status, {'action_type': 'cancel'},
         name='cancel_payment'),
    # 项目工程师款项
    path(r'dev_table/', api.dev_table, name='dev_table'),
]
