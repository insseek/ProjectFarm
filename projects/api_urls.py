from django.urls import path

from projects import api

app_name = 'projects_api'
urlpatterns = [
    path(r'', api.ProjectList.as_view(), {'proposal_id': None}, name='list'),
    path(r'filter_data', api.project_filter_data, name='filter_data'),

    path(r'simple_list', api.project_simple_list, name='project_simple_list'),
    path(r'ongoing/simple_list', api.ongoing_project_simple_list, name='ongoing_project_simple_list'),

    path(r'ongoing', api.ongoing_projects, name='ongoing_projects'),
    path(r'closed', api.get_closed_projects, name='closed_projects'),
    path(r'ongoing/deployment_servers', api.projects_deployment_servers, {'project_status': 'ongoing'},
         name='ongoing_projects_deployment_servers'),
    path(r'closed/deployment_servers', api.projects_deployment_servers, {'project_status': 'closed'},
         name='closed_projects_deployment_servers'),
    path(r'mobile/list', api.mobile_project_list, name='mobile_project_list'),

    path(r'mine', api.my_projects, name='my_projects'),
    path(r'mine/active_projects', api.my_ongoing_projects, name='my_ongoing_projects'),

    # 项目进度
    path(r'ongoing/schedules', api.ongoing_projects_schedules, name='ongoing_projects_schedules'),

    # 获取项目所有阶段类型分组
    path(r'<int:project_id>/stages_groups', api.get_project_stages_groups, name='get_project_stages_groups'),

    # 项目监督
    path(r'manage/filter_data', api.projects_manage_filter_data, name='projects_manage_filter_data'),
    # 项目监督的项目列表
    path(r'manage/projects', api.projects_manage_ongoing_projects, name='projects_manage_ongoing_projects'),

    path(r'tpm_checkpoints', api.projects_tpm_checkpoints, name='projects_tpm_checkpoints'),
    path(r'tpm_checkpoints/mine', api.my_tpm_checkpoints, name='my_tpm_checkpoints'),
    path(r'technology_checkpoints/<int:checkpoint_id>', api.TechnologyCheckpointDetail.as_view(),
         name='technology_checkpoint_detail'),

    path(r'<int:project_id>/technology_checkpoints', api.project_technology_checkpoints,
         name="project_technology_checkpoints"),

    path(r'mine/simple_list', api.my_project_simple_list, name='my_project_simple_list'),

    path(r'<int:project_id>', api.ProjectDetail.as_view(), name='project_detail'),
    path(r'<int:project_id>/edit_desc', api.edit_project_desc, name='edit_project_desc'),

    path(r'<int:project_id>/links', api.ProjectLinksDetail.as_view(), name='project_links'),
    path(r'<int:project_id>/reminders', api.project_detail_reminders, name='project_detail_reminders'),

    path(r'<int:project_id>/simple', api.project_simple_detail, name='project_simple_detail'),
    path(r'<int:project_id>/done', api.project_done, name='project_done'),
    path(r'<int:project_id>/done/check', api.project_done_check, name='project_done_check'),
    path(r'<int:project_id>/open', api.project_open, name='project_open'),

    path(r'<int:project_id>/comments/read', api.read_project_comments, name='read_project_comments'),
    path(r'<int:project_id>/name', api.project_name, name="project_name"),
    path(r'<int:project_id>/deployment_servers', api.ProjectDeploymentServer.as_view(),
         name="project_deployment_servers"),

    path(r'<int:project_id>/last_email_record', api.project_last_email_record, name='project_last_email_record'),

    path(r'<int:project_id>/quip_tpm_docs', api.project_quip_tpm_docs, name='project_quip_tpm_docs'),

    path(r'<int:project_id>/members', api.ProjectMemberList.as_view(), name='members'),

    # 项目合同
    path(r'contracts', api.ALLProjectWithContract.as_view(), name='all_projects_contracts'),
    path(r'<int:project_id>/contracts', api.ProjectContractList.as_view(), name='project_contracts'),
    path(r'contracts/<int:contract_id>', api.ProjectContractDetail.as_view(), name='contract_detail'),

    # 【code explain】【工程师评分】我的所有项目的职位列表
    path(r'mine/jobs/payments', api.MyProjectJobPositionsPayments.as_view(), name='my_projects_job_payments'),
    # 【code explain】【工程师评分】一个项目的职位列表
    path(r'<int:project_id>/jobs', api.ProjectJobPositionsList.as_view(), name='project_job_positions'),

    path(r'<int:project_id>/jobs/simple_list', api.project_job_positions_simple_list,
         name='project_job_positions_simple_list'),

    path(r'<int:project_id>/jobs/payments/statistic', api.project_jobs_payments_statistic,
         name='project_jobs_payments_statistic'),
    path(r'jobs/<int:position_id>', api.JobPositionDetail.as_view(), name='job_position_detail'),

    path(r'jobs/star_ratings', api.all_positions_star_ratings, name='all_positions_star_ratings'),
    # 【code explain】【工程师评分】
    path(r'jobs/<int:position_id>/job_reference_score', api.JobPositionReferenceScore.as_view(),
         name='job_reference_score'),
    path(r'jobs/<int:position_id>/job_standard_score', api.JobPositionStandardScore.as_view(),
         name='job_standard_score'),
    path(r'jobs/<int:position_id>/all_score', api.all_role_job_score, name='all_role_job_score'),

    path(r'<int:project_id>/schedule', api.ProjectStageDetail.as_view(), name='project_schedule'),
    path(r'<int:project_id>/schedule_remarks/hide', api.hide_schedule_remarks, name='hide_schedule_remarks'),

    # 工程师评分问卷
    path(r'questionnaires', api.QuestionnaireList.as_view(), name='questionnaire_list'),
    path(r'questionnaires/<int:questionnaire_id>', api.QuestionnaireDetail.as_view(), name='get_questionnaires_detail'),
    path(r'questionnaires/online', api.get_questionnaires_online_history, name='get_questionnaires_online_history'),
    path(r'questionnaires/<int:questionnaire_id>/issue', api.issue_questionnaire, name='issue_questionnaire'),
    path(r'jobs/<int:position_id>/grade_staffs', api.get_grade_staffs, name='get_grade_staffs'),
    path(r'jobs/<int:position_id>/staff_questionnaire', api.get_staff_questionnaire, name='get_staff_questionnaire'),
    path(r'jobs/<int:position_id>/questionnaires/submit', api.submit_questionnaire, name='submit_questionnaire'),
    path(r'jobs/<int:position_id>/questionnaires/skip', api.skip_questionnaire, name='skip_questionnaire'),
    path(r'jobs/<int:position_id>/questionnaires/get_final_score', api.get_final_score, name='get_final_score'),
    path(r'jobs/<int:position_id>/questionnaires/submit_final_score', api.submit_final_score,
         name='submit_final_score'),
    path(r'jobs/<int:position_id>/questionnaires/score', api.get_position_score, name='get_position_score'),

    # 项目工时计划
    path(r'<int:project_id>/work_hour_plans', api.ProjectWorkHourPlanList.as_view(),
         name='project_work_hour_plan_list'),
    path(r'<int:project_id>/work_hour_records', api.WorkHourRecordList.as_view(), name='project_work_hour_record_list'),
    path(r'work_hour_plans', api.get_project_work_hour_statistic_data,
         name='get_project_work_hour_statistic_data'),
    path(r'<int:project_id>/work_hour_operation_logs', api.get_project_work_hour_operation_log,
         name='get_project_work_hour_operation_log'),

    # 新接口
    # 交付文档链接、交付文档上传
    path(r'<int:project_id>/delivery_documents', api.ProjectDeliveryDocumentList.as_view(),
         name='project_delivery_documents'),
    path(r'<int:project_id>/delivery_documents/compress', api.compress_documents, name='compress_delivery_documents'),
    path(r'<int:project_id>/delivery_documents/<int:document_id>', api.DeliveryDocumentDetail.as_view(),
         name='delivery_document_detail'),

    path(r'delivery_documents/<str:uid>/download', api.download_delivery_document,
         name='download_delivery_document'),
    path(r'delivery_document_zips/<str:uid>/download', api.download_document_zip,
         name='download_document_zip'),

    path(r'<int:project_id>/prototypes', api.ProjectPrototypeList.as_view(), name='project_prototype'),
    path(r'<int:project_id>/prototypes/last', api.project_last_prototype, name='project_last_prototype'),

    path(r'<int:project_id>/prototypes/browsing_histories', api.prototypes_with_browsing_histories,
         name='prototypes_browsing_histories'),
    path(r'prototypes/<int:prototype_id>', api.ProjectPrototypeDetail.as_view(),
         name='prototype_detail'),

    path(r'prototypes/<int:prototype_id>/public_status', api.PrototypePublicStatus.as_view(),
         name='prototype_public_status'),

    path(r'prototypes/<int:prototype_id>/reset_cipher', api.reset_prototype_cipher,
         name='reset_prototype_cipher'),

    # 原型评论对外开放
    path(r'prototypes/<str:uid>/comment_points', api.PrototypeCommentPointList.as_view(),
         name='prototype_comment_points'),
    path(r'prototypes/<str:uid>/comment_points/all', api.current_prototype_all_comment_points,
         name='prototype_all_comment_points'),

    path(r'prototypes/<str:uid>/content_type', api.prototype_content_type,
         name='prototype_content_type'),

    path(r'prototypes/<str:uid>/access', api.prototype_access_data,
         name='prototype_access_data'),

    path(r'prototypes/<str:uid>/access_token', api.prototype_access_token,
         name='prototype_access_token'),

    path(r'prototypes/comment_points/current_page', api.current_page_comment_points,
         name='current_page_comment_points'),
    path(r'prototypes/comment_points/<int:id>', api.PrototypeCommentPointDetail.as_view(),
         name='prototype_comment_point_detail'),
    # 原型评论对外开放

    path(r'<int:project_id>/gantt_chart', api.ProjectGanttDetail.as_view(), name='gantt_chart_detail'),
    path(r'<int:project_id>/gantt_chart/members', api.project_gantt_chart_members, name='gantt_chart_members'),

    path(r'gantt_chart/<int:gantt_chart_id>/init_template', api.gantt_chart_init_template,
         name='gantt_chart_init_template'),
    path(r'gantt_chart/<int:gantt_chart_id>/update_template', api.gantt_chart_update_template,
         name='gantt_chart_update_template'),

    path(r'gantt_chart/<int:gantt_chart_id>/roles', api.GanttRoleList.as_view(), name='gantt_chart_roles'),
    path(r'gantt_chart/roles/<int:role_id>', api.GanttRoleDetail.as_view(),
         name='gantt_role_detail'),
    path(r'gantt_chart/roles/<int:role_id>/last_edited_task', api.gantt_role_last_edited_task,
         name='role_last_edited_task'),
    path(r'gantt_chart/<int:gantt_chart_id>/tasks', api.project_gantt_tasks, name='project_gantt_tasks'),
    path(r'gantt_chart/<int:gantt_chart_id>/task_catalogues', api.GanttTaskCatalogueList.as_view(),
         name='gantt_task_catalogues'),

    path(r'gantt_chart/task_catalogues/<int:catalogue_id>', api.GanttTaskCatalogueDetail.as_view(),
         name='gantt_task_catalogue_detail'),

    path(r'gantt_chart/task_catalogues/<int:catalogue_id>/name', api.change_catalogue_name,
         name='change_catalogue_name'),

    path(r'gantt_chart/<int:gantt_chart_id>/task_topics', api.GanttTaskTopicList.as_view(),
         name='gantt_task_topics'),
    path(r'gantt_chart/<int:gantt_chart_id>/last_task_topic', api.project_gantt_chart_last_task_topic,
         name='project_gantt_chart_last_task_topic'),
    path(r'gantt_chart/task_topics/<int:topic_id>', api.GanttTaskTopicDetail.as_view(),
         name='gantt_task_topic_detail'),

    path(r'gantt_chart/task_topics/<int:topic_id>/toggle_done', api.gantt_task_toggle_done,
         name='gantt_task_toggle_done'),

    path(r'gantt_chart/task_topics/<int:topic_id>/dev/toggle_done', api.gantt_task_dev_toggle_done,
         name='gantt_task_dev_toggle_done'),

    path(r'gantt_chart/task_catalogues/<int:obj_id>/move_up', api.move_current_gantt_task,
         {'obj_type': 'catalogue', 'move_type': 'move_up'},
         name='gantt_task_catalogue_move_up'),
    path(r'gantt_chart/task_catalogues/<int:obj_id>/move_down', api.move_current_gantt_task,
         {'obj_type': 'catalogue', 'move_type': 'move_down'}, name='gantt_task_catalogue_move_down'),

    path(r'gantt_chart/task_topics/<int:obj_id>/move_up', api.move_current_gantt_task,
         {'obj_type': 'topic', 'move_type': 'move_up'},
         name='gantt_task_topic_move_up'),

    path(r'gantt_chart/task_topics/<int:obj_id>/move_down', api.move_current_gantt_task,
         {'obj_type': 'topic', 'move_type': 'move_down'},
         name='gantt_task_topic_move_down'),

    path(r'gantt_chart/task_catalogues/drag', api.drag_gantt_task_catalogue, name='drag_gantt_task_catalogue'),

    path(r'gantt_chart/task_topics/drag', api.drag_gantt_task_topic, name='drag_gantt_task_topic'),

    path(r'gantt_chart/task_topics/<int:obj_id>/work_date', api.change_current_gantt_task_work_date,
         name='gantt_task_topic_work_date'),
    path(r'gantt_chart/<int:id>/sort', api.sort_project_gantt_chart_topics,
         name='sort_gantt_chart_topics'),
    path(r'gantt_chart/<int:id>/task_topics/delay', api.delay_project_gantt_chart_topics,
         name='delay_gantt_chart_topics'),

    path(r'gantt_chart/test', api.role_gantt_chart, {'role': 'test'}, name='test_gantt_chart'),
    path(r'gantt_chart/test/tasks', api.role_gantt_chart_tasks, {'role': 'test'}, name='test_gantt_chart_tasks'),

    path(r'gantt_chart/design', api.role_gantt_chart, {'role': 'design'}, name='design_gantt_chart'),

    path(r'gantt_chart/design/tasks', api.role_gantt_chart_tasks, {'role': 'design'}, name='design_gantt_chart_tasks'),

    path(r'gantt_chart/tasks/mine', api.my_gantt_chart_tasks, name='my_gantt_chart_tasks'),

    path(r'position_needs/statistic', api.all_project_job_position_needs_statistic,
         name='all_project_job_position_needs_statistic'),
    path(r'position_needs', api.all_project_job_position_needs, name='all_project_job_position_needs'),
    path(r'position_needs/mine/statistic', api.my_project_job_position_needs_statistic,
         name='my_project_job_position_needs_statistic'),
    path(r'position_needs/mine', api.my_project_job_position_needs, name='my_project_job_position_needs'),

    path(r'position_needs/logs', api.position_needs_logs, {'is_mine': False}, name='position_needs_logs'),
    path(r'position_needs/mine/logs', api.position_needs_logs, {'is_mine': True}, name='my_position_needs_logs'),
    path(r'<int:project_id>/position_needs', api.ProjectPositionNeedList.as_view(), name='project_position_needs'),
    path(r'position_needs/<int:position_need_id>', api.JobPositionNeedDetail.as_view(),
         name='position_need_detail'),

    path(r'position_needs/<int:position_need_id>/candidates', api.JobPositionCandidateList.as_view(),
         name='position_candidates'),
    path(r'position_candidates/<int:candidate_id>', api.JobPositionCandidateDetail.as_view(),
         name='position_candidate_detail'),

    path(r'position_candidate/<int:candidate_id>/confirm', api.position_candidate_status, {'type': 'confirm'},
         name='confirm_position_candidate'),
    path(r'position_candidate/<int:candidate_id>/refuse', api.position_candidate_status, {'type': 'refuse'},
         name='refuse_position_candidate'),
    path(r'position_candidate/<int:candidate_id>/contact', api.position_candidate_status, {'type': 'contact'},
         name='contact_position_candidate'),
    path(r'position_candidate/<int:candidate_id>/initial_contact', api.position_candidate_status,
         {'type': 'initial_contact'},
         name='initial_contact_position_candidate'),

    path(r'<int:project_id>/calendars', api.ClientCalendarList.as_view(),
         name='project_calendar'),
    path(r'<int:project_id>/calendars/last', api.project_last_calendar,
         name='project_last_calendar'),
    path(r'<int:project_id>/calendar/create', api.ClientCalendarList.as_view(), {'action': 'create'},
         name='create_calendar'),
    path(r'<int:project_id>/calendar/preview', api.ClientCalendarList.as_view(), {'action': 'preview'},
         name='preview_calendar'),

    path(r'<int:project_id>/calendar/<str:uid>/edit', api.ClientCalendarDetail.as_view(), {'action': 'edit'},
         name='edit_calendar'),
    path(r'<int:project_id>/calendar/<str:uid>/preview', api.ClientCalendarDetail.as_view(), {'action': 'preview'},
         name='preview_edit_calendar'),
    path(r'<int:project_id>/calendar/<str:uid>/delete', api.ClientCalendarDetail.as_view(), name='delete_calendar'),

    path(r'calendar/<str:uid>/public/toggle', api.reset_calendar_public_status,
         name='reset_calendar_public_status'),

    path(r'calendar/<str:uid>/preview', api.ClientCalendarDetail.as_view(), {'type': 'preview'},
         name='calendar_preview'),
    path(r'calendar/<str:uid>', api.ClientCalendarDetail.as_view(), {'type': 'view'}, name='view_calendar'),

    path(r'gitlab/committers', api.projects_gitlab_committers, name='projects_gitlab_committers'),
    path(r'<int:project_id>/gitlab/committers', api.project_gitlab_committers, name='project_gitlab_committers'),

    path(r'test/statistics', api.projects_test_statistics, name='projects_test_statistics'),

    path(r'mine/ongoing/demo/status', api.my_ongoing_projects_demo_status, name='my_ongoing_projects_demo_status'),
    path(r'<int:project_id>/demo/status', api.ProjectDemoStatus.as_view(), name='project_demo_status'),

    path(r'daily_works/projects', api.daily_works_projects, name='daily_works_projects'),
    path(r'daily_works/projects/recent_unread_dict', api.daily_works_projects_recent_unread_dict,
         name='daily_works_projects_recent_unread_dict'),

    path(r'quip_folders', api.quip_folders, name="quip_folders"),
    path(r'quip_engineer_folders', api.quip_engineer_folders, name="quip_engineer_folders"),

    path(r'quip_folder/<str:folder_id>/children_folders', api.quip_folder_children_folders,
         name="quip_folder_children_folders"),

    path(r'data/migrate', api.projects_data_migrate, name='projects_data_migrate'),
]
