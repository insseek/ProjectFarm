from django.urls import path

from auth_top import api

app_name = 'auth_top_api'
urlpatterns = [
    path(r'sso/app/data', api.app_data, name='app_data'),

    path(r'sso/phone/code', api.phone_code, name='phone_code'),

    path(r'sso/phone/login/code', api.phone_login_code, name='phone_login_code'),
    path(r'sso/phone/login/user_types', api.phone_login_user_types, name='phone_login_user_types'),
    path(r'sso/phone/login', api.phone_login, name='phone_login'),

    path(r'sso/gitlab/login/oauth_uri', api.gitlab_login_oauth_uri,
         name='gitlab_login_oauth_uri'),
    path(r'sso/gitlab/login/user_types', api.gitlab_login_user_types, name='gitlab_login_user_types'),
    path(r'sso/gitlab/login', api.gitlab_login, name='gitlab_login'),

    path(r'sso/feishu/login/oauth_uri', api.feishu_login_oauth_uri,
         name='feishu_login_oauth_uri'),
    path(r'sso/feishu/login/user_types', api.feishu_login_user_types, name='feishu_login_user_types'),
    path(r'sso/feishu/login', api.feishu_login, name='feishu_login'),

    path(r'sso/ticket', api.sso_ticket, name='sso_ticket'),
    path(r'sso/ticket/login', api.sso_ticket_login,
         name='sso_ticket_login'),

    path(r'sso/logout', api.sso_logout,
         name='sso_logout'),

    path(r'sso/me', api.my_info, name='my_info'),

    path(r'sso/me/perms', api.my_perms, name='my_perms'),
]
