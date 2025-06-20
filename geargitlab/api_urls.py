from django.urls import path

from . import api

app_name = 'geargitlab_api'
urlpatterns = [
    path(r'projects', api.gitlab_projects_groups, name='gitlab_projects'),
    path(r'users', api.gitlab_users_data, name='gitlab_users'),
    path(r'data/migrate', api.data_migrate, name='gitlab_data_migrate'),
]
