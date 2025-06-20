from django.urls import path

from gearmail import api

app_name = 'gearmail_api'
urlpatterns = [
    path(r'templates', api.EmailTemplateList.as_view(),name='templates'),
    path(r'templates/<int:id>', api.EmailTemplateDetail.as_view(), name='template_detail'),
    path(r'records/mine', api.EmailRecordList.as_view(), name='my_records'),
    path(r'records/<int:id>', api.EmailRecordDetail.as_view(), name='record_detail'),
    path(r'records/project/<int:id>', api.ProjectEmailRecordList.as_view(),name='project_records'),
    path(r'send', api.send_email_api, name='send_email')
]