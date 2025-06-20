from django.urls import path
from farmbase import open_api
from farmbase import api

app_name = 'farmbase_users_open_api'
urlpatterns = [
    # 根据给gitlab_id获取Farm用户、Farm工程师个人信息 :
    path(r'gitlab/personal', open_api.gitlab_personal_info, name='gitlab_personal_info'),
    path(r'gitlab/dict', open_api.gitlab_users_dict, name='gitlab_users_dict'),
    path(r'login', api.login_handle, name='login')
]
