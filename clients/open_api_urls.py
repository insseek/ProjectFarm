from django.urls import path
from clients import open_api
from auth_top import api as sso_api

app_name = 'clients_open_api'
urlpatterns = [
    path(r'me', open_api.MyInfo.as_view(), name='my_info'),

    path(r'phone/code', sso_api.phone_code, name='phone_code'),

    path(r'phone/change/code', sso_api.phone_change_code, name='phone_change_code'),
    path(r'me/phone/change', sso_api.change_my_phone, name='change_my_phone'),

    path(r'phone/login', sso_api.phone_login, name='phone_login'),

    path(r'login/one_time/authentication', open_api.one_time_authentication_login,
         name='one_time_authentication_login'),

    # 项目
    path(r'projects/mine', open_api.my_projects, name='my_projects'),

    path(r'phone/check', open_api.client_phone_check, name='client_phone_check'),

    path(r'projects/delivery_documents/<str:uid>/download', open_api.download_delivery_document,
         name='download_delivery_document'),

    path(r'projects/delivery_documents/signature', open_api.download_delivery_document_signature,
         name='download_delivery_document_signature'),

    path(r'projects/<int:project_id>', open_api.project_detail, name='project_detail'),

    path(r'projects/<int:project_id>/permissions', open_api.project_my_permissions, name='project_my_permissions'),

    path(r'projects/<int:project_id>/clients', open_api.project_clients, name='project_clients'),
    path(r'projects/<int:project_id>/clients/add', open_api.add_project_client, name='add_project_client'),
    path(r'projects/<int:project_id>/clients/<int:client_id>', open_api.ProjectClientDetail.as_view(),
         name='project_client_detail'),

    path(r'projects/<int:project_id>/design', open_api.project_design, name='project_design'),
    path(r'projects/<int:project_id>/designs', open_api.project_designs, name='project_designs'),
    path(r'projects/<int:project_id>/members', open_api.project_members, name='project_members'),
    path(r'projects/<int:project_id>/prototypes', open_api.project_prototypes, name='project_prototypes'),
    path(r'projects/<int:project_id>/calendar', open_api.project_last_calendar,
         name='project_last_calendar'),

    path(r'projects/<int:project_id>/calendars', open_api.project_calendars,
         name='project_calendars'),

    path(r'projects/<int:project_id>/email_records', open_api.project_email_records,
         name='project_email_records'),

    path(r'projects/<int:project_id>/deployment_servers', open_api.project_deployment_servers,
         name="project_deployment_servers"),
    path(r'projects/<int:project_id>/delivery_documents', open_api.project_delivery_documents,
         name="project_delivery_documents")
]
