from django.urls import include, path

from notifications import api

app_name = 'notifications_api'

urlpatterns = [
    path(r'mine', api.MyNotificationList.as_view(), name='mine'),
    path(r'mine/read', api.read_my_notifications, name='read_my_notifications'),
    path(r'<int:notification_id>/read', api.read, name='read'),
    path(r'send', api.send_notifications, name='send'),

    path(r'pusher/send/test', api.send_pusher_notifications, name='send_pusher_notifications'),
]