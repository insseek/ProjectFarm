from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from . import api

app_name = 'dashboard_api'
urlpatterns = [
    path(r'modules', api.modules, name='modules'),
    path(r'statistics', api.my_undone_work_dashboard_statistics, name='my_undone_work_dashboard_statistics'),
    path(r'tasks', api.undone_tasks, name='undone_tasks'),
    path(r'gantt_chart/tasks', api.undone_gantt_chart_tasks, name='undone_gantt_chart_tasks'),
    path(r'playbook/tasks', api.undone_playbook_tasks, name='undone_playbook_tasks'),
    path(r'tpm_checkpoints', api.undone_tpm_checkpoints, name='undone_tpm_checkpoints'),

    path(r'projects/ongoing', api.ongoing_projects, name='ongoing_projects'),
    path(r'projects/<int:project_id>', api.project_detail, name='project_detail'),

]
