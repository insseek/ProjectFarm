from django.urls import path

from oauth import api

app_name = 'oauth_api'
urlpatterns = [
    path(r'gitlab/bind/redirect/data', api.gitlab_bind_redirect_data, name='gitlab_bind_redirect_data'),
    path(r'gitlab/bind', api.gitlab_bind, name='gitlab_bind'),

    path(r'gitlab/login/redirect/data', api.gitlab_login_redirect_data, name='gitlab_login_redirect_data'),
    path(r'gitlab/login', api.gitlab_login, name='gitlab_login'),

    path(r'gitlab/unbind', api.gitlab_oauth_unbind, name='gitlab_oauth_unbind'),

    path(r'feishu/bind/redirect/data', api.feishu_bind_redirect_data, name='feishu_bind_redirect_data'),
    path(r'feishu/bind', api.feishu_bind, name='feishu_bind'),
    path(r'feishu/unbind', api.feishu_unbind, name='feishu_unbind'),

    path(r'feishu/login/redirect/data', api.feishu_login_redirect_data, name='feishu_login_redirect_data'),
    path(r'feishu/login', api.feishu_login, name='feishu_login'),

    path(r'feishu/users', api.feishu_users, name='feishu_users'),

    path(r'wechat/sign_data', api.wechat_sign_data, name='wechat_sign_data'),

]
