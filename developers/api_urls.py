from django.urls import path
from developers import api
from developers import open_api

app_name = 'developers_api'
urlpatterns = [
    path(r'', api.DeveloperList.as_view(), name='list'),
    path(r'active', api.active_developers, name='active_developers'),

    path(r'tags', api.developers_tags, name='tags'),
    path(r'roles', api.RoleList.as_view(), name='roles'),
    path(r'roles/<int:role_id>/developers', api.role_developers, name='role_developers'),
    path(r'<int:developer_id>', api.DeveloperDetail.as_view(), name='detail'),
    path(r'<int:developer_id>/rate', api.developer_rate.as_view(), name='rate'),
    path(r'<int:developer_id>/status', api.developer_status, name='status'),
    path(r'<int:developer_id>/change_id_card', api.change_developer_id_card, name='id_card'),
    path(r'<int:id>/download_id_card/', api.download_developer_id_card_image, name='download_id_card'),
    path(r'<int:id>/private/permission', api.developer_private_permission, name='developer_private_permission'),

    path(r'<int:developer_id>/position_candidates', api.position_candidates, name='position_candidates'),

    # 【code explain】【工程师评分】  工程师的进行中项目职位、已完成项目职位
    path(r'<int:developer_id>/ongoing_projects_jobs', api.ongoing_projects_jobs, name='ongoing_projects_jobs'),
    path(r'<int:developer_id>/closed_projects_jobs', api.closed_projects_jobs, name='closed_projects_jobs'),
    path(r'<int:developer_id>/projects_jobs', api.projects_jobs, name='projects_jobs'),

    path(r'<int:developer_id>/git/projects', api.gitlab_user_projects, name='gitlab_user_projects'),
    path(r'<int:developer_id>/git/block', api.block_gitlab_user, name='block_gitlab_user'),
    path(r'<int:developer_id>/git/unblock', api.unblock_gitlab_user, name='unblock_gitlab_user'),
    path(r'<int:developer_id>/git/unbind', api.unbind_gitlab_user, name='unbind_gitlab_user'),

    path(r'<int:developer_id>/git/projects/all/leave', api.leave_git_groups_projects, {'all': True},
         name='gitlab_user_leave_all_projects'),
    path(r'<int:developer_id>/git/projects/leave', api.leave_git_groups_projects,
         name='gitlab_user_leave_projects'),

    path(r'<int:developer_id>/git/projects/<int:project_id>/leave', api.gitlab_user_leave_project,
         name='gitlab_user_leave_projects'),
    path(r'<int:developer_id>/git/groups/<int:group_id>/leave', api.gitlab_user_leave_group,
         name='gitlab_user_leave_groups'),

    path(r'<int:developer_id>/committers', api.DeveloperCommitters.as_view(),
         name='developer_gitlab_committers'),

    path(r'committers', api.developers_gitlab_committers,
         name='developers_gitlab_committers'),

    path(r'<int:developer_id>/open/authentication_key', api.one_time_authentication_key,
         name='developer_one_time_authentication_key'),

    path(r'projects/<int:project_id>/daily_works/day', open_api.project_day_daily_work,
         name='project_day_daily_work'),
    path(r'projects/<int:project_id>/daily_works/last', open_api.project_developer_last_daily_work,
         name='project_developer_last_daily_work'),

    path(r'projects/<int:project_id>/daily_works/statistics', open_api.project_developer_daily_work_statistics,
         name='project_developer_daily_work_statistics'),

    path(r'projects/<int:project_id>/members', open_api.project_members, name='project_members'),
    path(r'projects/<int:project_id>/developers', open_api.project_developers, name='project_developers'),

    path(r'data/export/', api.export_excel, name='export_excel'),

    path(r'quip_documents', api.quip_developer_documents, name='quip_developer_documents'),
    path(r'documents', api.DocumentList.as_view(), name='developer_documents'),
    path(r'documents/<int:id>', api.DocumentDetail.as_view(), name='developer_document_detail'),
    path(r'documents/<int:id>/version_update', api.update_document_version,
         name='update_document_version'),

    path(r'documents/drag', api.drag_document, name='drag_document'),

    path(r'documents/<int:id>/sync', api.sync_document,
         name='sync_document'),
    path(r'projects/<int:project_id>/documents', api.project_developers_documents, name='project_developers_documents'),

    path(r'projects/documents/skip_sync', api.project_developer_document_skip_sync,
         name='project_developer_document_skip_sync'),

    path(r'<int:developer_id>/documents', api.developer_documents,
         name='developer_documents'),

    path(r'daily_works/message/send', api.daily_works_message, name='daily_works_message'),

    path(r'cache/rebuild', api.cache_rebuild, name='cache_rebuild'),

]
