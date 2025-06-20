from django.urls import include, path

from projects import open_api

app_name = 'projects_open_api'
urlpatterns = [
    path(r'deploy/status', open_api.project_deploy_status, name='project_deploy_status'),
]
