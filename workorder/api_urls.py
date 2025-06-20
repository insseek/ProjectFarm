from django.urls import path

from . import api

app_name = 'workorder_api'
urlpatterns = [
    path(r'sources', api.work_order_sources, name='sources'),
    path(r'statistics', api.work_orders_statistics, name='statistics'),
    path(r'', api.CommonWorkOrderList.as_view(), name='common_work_order'),
    path(r'<int:id>', api.CommonWorkOrderDetail.as_view(), name='common_work_order_detail'),
    path(r'<int:work_order_id>/status/change', api.change_common_work_order_status, name='change_work_order_status'),
    path(r'<int:id>/reassign', api.common_reassign, name="work_order_reassign"),
    path(r'<int:work_order_id>/modify_expected_at', api.modify_work_order_expected_at,
         name="modify_work_order_expected_at"),
    path(r'<int:work_order_id>/operation_logs', api.operation_logs, name="work_order_operation_logs"),
    path(r'<int:work_order_id>/comment', api.comments, name="work_order_comment"),
    path(r'<int:id>/priority', api.common_work_order_priority, name="common_work_order_priority"),
    path(r'users', api.common_work_orders_users, name='common_work_orders_users'),
]
