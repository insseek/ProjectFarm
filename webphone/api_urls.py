from django.urls import path

from . import api

app_name = 'webphone_api'
urlpatterns = [
    path(r'token', api.get_token, name='token'),
    path(r'click2call', api.click2call, name='click2call'),
    path(r'stop_call', api.stop_call, name='stop_call'),
    path(r'call_status_notice', api.call_status_notice, name='call_status_notice'),
    path(r'call_fee_notice', api.call_fee_notice, name='call_fee_notice'),
    path(r'call_records', api.call_records, name='call_records'),
    path(r'call_records/mine', api.my_call_records, name='my_call_records'),
    path(r'call_records/users', api.call_record_users, name='call_record_users'),
    path(r'call_records/<int:id>', api.call_record_detail, name='call_record_detail'),

    path(r'records/<str:uid>/download/', api.download_call_record, name='download_call_record'),
]
