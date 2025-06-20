from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from farmbase import api

app_name = 'user_api'
urlpatterns = [
    path(r'', api.UserList.as_view(), name='user_list'),

    path(r'active', api.active_users, name='active_users'),
    path(r'undone_works/mine/statistics', api.my_undone_work_statistics, name='my_undone_work_statistics'),
    path(r'me/pages/undone_works', api.my_pages_undone_works,
         name='my_pages_undone_works'),

    path(r'<int:user_id>', api.UserDetail.as_view(), name='user_detail'),
    path(r'<int:user_id>/ongoing_works', api.user_ongoing_works, name='user_ongoing_works'),

    path(r'phone/code', api.phone_code, name='phone_code'),
    path(r'phone/login', csrf_exempt(api.phone_login), name='phone_login'),

    path(r'token', csrf_exempt(api.FarmAuthToken.as_view()), name='auth_token'),
    path(r'csrftoken', api.get_csrftoken, name='csrftoken'),
    path(r'token/check', csrf_exempt(api.user_token_check), name='check_token'),
    path(r'login', csrf_exempt(api.login_handle), name='login'),

    path(r'logout', api.logout_handle, name='logout'),
    path(r'me/password', api.change_my_password, name='change_my_password'),

    path(r'me', api.UserInfo.as_view(), name='my_info'),
    path(r'me/perms', api.my_perm_data, name='my_perms'),

    path(r'me/perms/view_proposals_projects', api.my_view_proposals_projects_perm_data,
         name='my_view_proposals_projects_perm_data'),

    path(r'me/perms/view_multi_objs', api.my_view_multi_objs,
         name='my_view_multi_objs'),

    path(r'groups', api.GroupList.as_view(), name='group_list'),
    path(r'groups/func_perms', api.groups_func_perms, name='groups_func_perms'),
    path(r'func_perms', api.FunctionPermissionList.as_view(), name='func_perms'),

    path(r'perms/data', api.perms_data, name='perms_data'),
    path(r'func_perms/data', api.func_perms_data, name='func_perms_data'),

    # staging  develop从正式环境同步权限使用
    path(r'func_perms/init_data', api.func_perms_init_data, name='func_perms_init_data'),

    path(r'func_perms/perms', api.func_perms_perms, name='func_perms_perms'),

    path(r'func_perms/funcs', api.FunctionModuleList.as_view(), name='func_perm_funcs'),
    path(r'func_perms/funcs/<int:id>', api.FunctionModuleDetail.as_view(), name='func_perm_func_detail'),
    path(r'func_perms/<int:id>', api.FunctionPermissionDetail.as_view(), name='func_perm_detail'),
    path(r'func_perms/<int:id>/group_toggle', api.func_perm_group_toggle,
         name='func_perm_group_toggle'),
    path(r'func_perms/mine', api.my_func_perms, name='my_func_perms'),
    path(r'func_perm/users', api.get_users_by_func_perm, name='get_users_by_func_perm'),

    path(r'<int:user_id>/func_perms', api.UserFunctionPermissionList.as_view(),
         name='user_func_perms'),
    path(r'me/has_func_perms', api.judge_user_func_perms, {'user_id': None},
         name='judge_my_func_perms'),
    path(r'<int:user_id>/has_func_perms', api.judge_user_func_perms,
         name='judge_user_func_perms'),
    path(r'change_user_capacity', api.change_user_capacity, name='change_user_capacity'),

    path(r'perms/limit', api.SpecialPermissionList.as_view(), name='special_permissions'),
    path(r'impersonate', api.impersonate_auth, name='impersonate_auth'),
    path(r'impersonate/exit', api.impersonate_auth_exit, name='impersonate_auth_exit'),

    path(r'committers', api.users_gitlab_committers,
         name='users_gitlab_committers'),

    path(r'<int:user_id>/committers', api.UserCommitters.as_view(),
         name='user_gitlab_committers'),

    path(r'me/one_time/authentication_key', api.my_one_time_authentication_key,
         name='my_one_time_authentication_key'),

    path(r'guidance/status', api.guidance_status, name='guidance_status'),
    path(r'guidance/done', api.guidance_done, name='guidance_done'),

    path(r'teams', api.TeamList.as_view(), name='team_list'),
    path(r'teams/<int:team_id>', api.TeamDetail.as_view(), name='team_detail'),

    path(r'documents', api.DocumentList.as_view(), {'is_mine': False}, name='documents'),
    path(r'documents/mine', api.DocumentList.as_view(), {'is_mine': True}, name='my_documents'),

    path(r'stats/new_demand', api.get_new_demand_chart_data, name='get_new_demand_chart_data'),
    path(r'stats/recent_30', api.get_recent_30_data, name='get_recent_30_data'),
    path(r'stats/pms', api.get_pms_data, name='get_pms_data'),
    path(r'stats/bds', api.get_bds_data, name='get_bds_data'),

    path(r'capacity/', api.capacity, name='capacity'),
]
