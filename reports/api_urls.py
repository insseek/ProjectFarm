from django.urls import path

from . import api

app_name = 'reports_api'
urlpatterns = [
    path(r'', api.all_report_list, name='list'),
    path(r'publish_applicant/data/export', api.publish_applicant_data_export, name='publish_applicant_data_export'),
    path(r'leads/reports', api.lead_report_list, name='list'),

    path(r'tags', api.reports_tags, name='tags'),
    path(r'<str:uid>/tags/default', api.ReportTags.as_view(), name='report_tags'),
    path(r'<str:uid>/tags', api.ReportTags.as_view(), name='report_tags'),

    path(r'frame_diagrams', api.FrameDagramList.as_view(), name='frame_diagrams'),
    path(r'frame_diagrams/filter_data', api.frame_diagram_filter_data, name='filter_data'),
    path(r'frame_diagrams/upload', api.upload_frame_diagrams,
         name='upload_frame_diagrams'),
    path(r'mind_maps/upload', api.upload_mind_maps,
         name='upload_mind_maps'),
    path(r'files/upload', api.upload_files,
         name='upload_files'),

    path(r'create/quip', api.create_report_by_quip_url, name='create_by_quip_url'),
    path(r'create/md', api.create_report_by_md, name='create_report_by_md'),

    path(r'create/proposal_report/farm', api.create_proposal_report_by_farm, name='create_proposal_report_by_farm'),
    path(r'create/lead_report/farm', api.create_lead_report_by_farm, name='create_lead_report_by_farm'),

    path(r'<str:uid>/edit', api.ReportDetail.as_view(), name='detail'),

    path(r'<str:uid>/publish', api.publish_report, name='publish_report'),

    path(r'<str:uid>/publish/review', api.publish_review_report, name='publish_review_report'),

    path(r'reviewers', api.report_reviewers, name='report_reviewers'),

    path(r'<str:uid>/extend_expiration', api.extend_expiration, name='extend_expiration'),
    path(r'<str:uid>/expire_now', api.expire_now, name='expire_now'),
    # path(r'<str:uid>/tags', api.ReportTags.as_view(), name='tags'),
    path(r'<str:uid>/histories', api.ReportHistoryList.as_view(),
         name='report_histories'),
    path(r'<str:uid>/histories/<int:id>', api.ReportHistoryDetail.as_view(),
         name='report_history_detail'),
    path(r'<str:uid>/histories/<int:id>/restore', api.restore_report_history,
         name='restore_report_history'),

    path(r'<str:uid>/logs', api.OperatingRecordList.as_view(),
         name='report_operating_records'),

    path(r'<str:uid>/plans', api.ReportQuotationPlanList.as_view(), name='quotation_plans'),
    path(r'<str:uid>/plans/<int:plan_id>', api.ReportQuotationPlanDetail.as_view(), name='quotation_plan_detail'),
    path(r'<str:uid>/plans/<int:plan_id>/move_up', api.move_report_quotation_plan, {'move_type': 'move_up'},
         name='move_up_report_quotation_plan'),
    path(r'<str:uid>/plans/<int:plan_id>/move_down', api.move_report_quotation_plan, {'move_type': 'move_down'},
         name='move_down_report_quotation_plan'),

    path(r'<str:uid>/comment_points', api.ReportCommentPointList.as_view(),
         name='report_comment_points'),

    path(r'comment_points/<str:uid>', api.ReportCommentPointDetail.as_view(),
         name='report_comment_point_detail'),

    path(r'comment_points/<str:uid>/comments', api.ReportCommentPointCommentList.as_view(),
         name='report_comment_point_comments'),

    path(r'pageview/return', api.return_report_page, name='return_report_page'),
    path(r'pageview/leave', api.leave_report_page, name='leave_report_page'),
    path(r'pageview/users', api.report_page_users, name='report_page_users'),

    path(r'<str:report_uid>/evaluations', api.ReportEvaluationList.as_view(),
         name='report_evaluations'),

    path(r'<str:uid>', api.ReportDetail.as_view(), name='detail'),

]
