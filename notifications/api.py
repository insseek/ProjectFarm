from datetime import datetime, timedelta
import json

from django.contrib.auth.models import User, Group
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from developers.models import Developer
from notifications.models import Notification
from notifications.serializers import NotificationSerializer
from notifications.utils import create_notification, create_notification_all, create_notification_group, \
    create_developer_notification, create_top_user_notification
from gearfarm.utils import farm_response, simple_responses
from auth_top.models import TopUser


@api_view(['POST'])
def read(request, notification_id):
    notification = get_object_or_404(Notification, pk=notification_id)
    response_choices = farm_response
    is_testing_app = request.path.startswith('/api/v1/testing')
    if is_testing_app:
        response_choices = simple_responses

    if notification.owner_id != request.top_user.id:
        return response_choices.api_bad_request("不能修改他人消息状态")

    if not notification.read_at:
        notification.read_at = timezone.now()
        notification.is_read = True
        notification.save()
    return response_choices.api_success()


@api_view(['POST'])
def read_my_notifications(request):
    response_choices = farm_response
    is_testing_app = request.path.startswith('/api/v1/testing')

    user = request.user
    priority = request.GET.get('priority', None)
    priority_choices = [codename for codename, name in Notification.PRIORITY_CHOICES]
    if priority and priority not in priority_choices:
        return response_choices.api_bad_request(message="参数priority的可选值为{}".format('，'.join(priority_choices)))

    if is_testing_app:
        unread_notifications = Notification.objects.filter(owner_id=request.top_user.id, is_read=False)
    else:
        unread_notifications = Notification.objects.filter(user_id=user.id, is_read=False)

    if priority:
        unread_notifications = unread_notifications.filter(priority=priority)
    unread_notifications.update(read_at=timezone.now(), is_read=True)
    return response_choices.api_success()


def clean_url_value(url):
    if url and len(url) >= 200:
        return url.split('?')[0]
    return url


@api_view(['POST'])
def send_notifications(request):
    response_choices = farm_response
    is_testing_app = request.path.startswith('/api/v1/testing')
    if is_testing_app:
        response_choices = simple_responses

    content = request.data.get('content', None)
    if not content:
        return response_choices.api_bad_request('请输入消息内容')

    priority = request.data.get('priority', 'normal')
    priority_choices = [codename for codename, name in Notification.PRIORITY_CHOICES]
    if priority and priority not in priority_choices:
        return response_choices.api_bad_request(message="参数priority的可选值为{}".format('，'.join(priority_choices)))

    need_alert = True if request.data.get('need_alert', False) else False

    sender_name = request.top_user.username
    if sender_name not in content:
        content = '{}：{}'.format(sender_name, content)

    url = clean_url_value(request.data.get('url', None))
    farm_url = clean_url_value(request.data.get('farm_url', None))
    developer_url = clean_url_value(request.data.get('developer_url', None))

    all_user = request.data.get('all', None)
    if all_user:
        notification_url = farm_url or url
        create_notification_all(content, notification_url, priority=priority, need_alert=need_alert)
    else:
        top_users = TopUser.objects.none()
        users = User.objects.none()
        developers = Developer.objects.none()

        # 老参数 兼容
        group_names = request.data.get('groups', None)
        user_names = request.data.get('users', None)
        developer_names = request.data.get('developers', None)
        top_user_ids = request.data.get('top_users', None)

        # 接口 未来使用新参数
        group_ids = request.data.get('groups_ids', None)
        user_ids = request.data.get('user_ids', None)
        developer_ids = request.data.get('developer_ids', None)
        top_user_ids = request.data.get('top_user_ids', None) or top_user_ids

        # 内部员工
        if group_names:
            users = User.objects.filter(groups__name__in=group_names, is_active=True)
        if group_ids:
            users = users | User.objects.filter(groups__id__in=group_ids, is_active=True)
        if user_names:
            users = users | User.objects.filter(username__in=users, is_active=True)
        if user_ids:
            users = users | User.objects.filter(id__in=user_ids, is_active=True)
        users = users.distinct()

        # 开发者
        if developer_names:
            developers = Developer.objects.filter(name__in=developer_names, is_active=True)
        if developer_ids:
            developers = developers | Developer.objects.filter(id__in=developer_ids, is_active=True)

        # TopUser   Test系统
        if top_user_ids:
            top_users = TopUser.objects.filter(id__in=top_user_ids)

        app_id = 'gear_test' if is_testing_app else None
        if top_users:
            notification_url = url
            for top_user in users:
                if top_user.is_active:
                    create_top_user_notification(top_user, content, notification_url, priority=priority,
                                                 need_alert=need_alert,
                                                 app_id=app_id)
        if users:
            notification_url = farm_url or url
            for user in users:
                create_notification(user, content, notification_url, priority=priority, need_alert=need_alert)
        if developers:
            notification_url = developer_url or url
            for developer in developers:
                create_developer_notification(developer, content, notification_url, priority=priority,
                                              need_alert=need_alert)
    return response_choices.api_success()


class MyNotificationList(APIView):
    def get(self, request):
        response_choices = farm_response
        is_testing_app = request.path.startswith('/api/v1/testing')
        if is_testing_app:
            response_choices = simple_responses

        user = request.user
        params = request.GET
        priority = params.get('priority', None)
        priority_choices = [codename for codename, name in Notification.PRIORITY_CHOICES]

        if priority and priority not in priority_choices:
            return response_choices.api_bad_request(message="参数priority的可选值为{}".format('，'.join(priority_choices)))

        is_read = None
        need_alert = None
        if "need_alert" in params:
            need_alert = params['need_alert'] in {'true', '1', 'True', 1, True}
            # 如果需要弹框、那默认是未读消息
            if need_alert:
                is_read = False

        if "is_read" in params:
            is_read = params['is_read'] in {'true', '1', 'True', 1, True}

        notifications = Notification.objects.all()
        if is_testing_app:
            notifications = notifications.filter(app_id='gear_test', owner_id=request.top_user.id)
        else:
            notifications = user.notifications.all()

        if need_alert is not None:
            notifications = notifications.filter(need_alert=need_alert)

        if is_read is not None:
            notifications = notifications.filter(is_read=is_read)

        if priority:
            notifications = notifications.filter(priority=priority)

        if is_read is None:
            notifications = notifications.order_by('is_read', '-created_at')
        else:
            notifications = notifications.order_by('-created_at')
        return response_choices.build_pagination_response(request, notifications, NotificationSerializer)


from notifications.pusher import notification_pusher


@api_view(['GET'])
def send_pusher_notifications(request):
    response_choices = farm_response

    data = {
        'channel': 'gear-new-notification-channel',
        'event': 'new-notification',
        'data': {
            'message': {'data': 'my_data'}
        }
    }
    notification_pusher.trigger(
        data['channel'],
        data['event'],
        data['data'],
    )
    return response_choices.api_success(data)
