from django.conf import settings
from django.contrib.auth.models import User
from django.utils import six

from notifications.tasks import send_notification, send_feishu_message_to_all, send_feishu_message_to_individual, \
    send_developer_notification, send_top_user_notification, send_feishu_card_message_to_individual
from notifications.models import Notification
from developers.models import Developer


def create_developer_notification(developer, content, url=None, send_pusher=True, send_feishu=True, priority='normal',
                                  is_important=False, need_alert=False, app_id=None):
    if not developer or not developer.is_active:
        return
    if is_important:
        priority = 'important'
    if not priority:
        priority = 'normal'
    notification = Notification(developer=developer, content=content, url=url, priority=priority,
                                need_alert=need_alert)
    if app_id:
        notification.app_id = app_id
    notification.save()
    if send_pusher:
        if settings.DEVELOPMENT:
            send_developer_notification(developer.id, notification.id)
        else:
            send_developer_notification.delay(developer.id, notification.id)
    if settings.PRODUCTION and send_feishu:
        if developer.feishu_user_id:
            send_feishu_message_to_individual.delay(developer.feishu_user_id, content, link=url)


def send_feishu_message_to_user(user, content, url=None):
    if user.profile.feishu_user_id:
        send_feishu_message_to_individual.delay(user.profile.feishu_user_id, content, link=url)


def send_feishu_card_message_to_user(user, content):
    if user.profile.feishu_user_id:
        send_feishu_card_message_to_individual.delay(user.profile.feishu_user_id, content)


def create_notification(user, content, url=None, send_feishu=True, send_pusher=True, priority='normal',
                        is_important=False, need_alert=False, app_id=None):
    if not user or not user.is_active:
        return
    if is_important:
        priority = 'important'
    if not priority:
        priority = 'normal'
    notification = Notification(user=user, content=content, url=url, priority=priority,
                                need_alert=need_alert)
    if app_id:
        notification.app_id = app_id
    notification.save()

    if send_pusher:
        if settings.DEVELOPMENT:
            send_notification(user.id, notification.id)
        else:
            send_notification(user.id, notification.id)

    if settings.PRODUCTION and send_feishu:
        if user.profile.feishu_user_id:
            send_feishu_message_to_individual.delay(user.profile.feishu_user_id, content, link=url)


def create_top_user_notification(top_user, content, url=None, send_feishu=True, send_pusher=True, priority='normal',
                                 is_important=False, need_alert=False, app_id=None):
    if not top_user or not top_user.is_active:
        return
    if is_important:
        priority = 'important'
    if not priority:
        priority = 'normal'
    notification = Notification(owner=top_user, content=content, url=url, priority=priority,
                                need_alert=need_alert)
    if app_id:
        notification.app_id = app_id
    notification.save()

    if send_pusher:
        if settings.DEVELOPMENT:
            send_top_user_notification(notification.id, app_id)
        else:
            send_top_user_notification.delay(notification.id, app_id)
    if settings.PRODUCTION and send_feishu:
        feishu_user_id = None
        if top_user.is_employee:
            feishu_user_id = top_user.user.profile.feishu_user_id
        elif top_user.is_developer:
            feishu_user_id = top_user.developer.feishu_user_id
        if feishu_user_id:
            send_feishu_message_to_individual.delay(feishu_user_id, content, link=url)


def create_notification_all(content, url=None, send_feishu=True, send_pusher=True, priority='normal',
                            is_important=False, need_alert=False):
    users = User.objects.filter(is_active=True)
    for user in users:
        create_notification(user, content, url, send_feishu=False, send_pusher=send_pusher, priority=priority,
                            is_important=is_important, need_alert=need_alert)
    if settings.PRODUCTION and send_feishu:
        send_feishu_message_to_all.delay(content, link=url)


def create_notification_group(group_name, content, url=None, send_feishu=True, send_pusher=True, priority='normal',
                              is_important=False, need_alert=False):
    users = User.objects.filter(groups__name=group_name, is_active=True)
    for user in users:
        create_notification(user, content, url, send_feishu=False, send_pusher=send_pusher, priority=priority,
                            is_important=is_important, need_alert=need_alert)
        if settings.PRODUCTION and send_feishu:
            if user.profile.feishu_user_id:
                send_feishu_message_to_individual.delay(user.profile.feishu_user_id, content, link=url)


def create_notification_to_users(users, content, url=None, send_feishu=True, send_pusher=True, priority='normal',
                                 is_important=False, need_alert=False):
    if isinstance(users, six.string_types):
        users = (users,)
    else:
        users = users
    for user in users:
        create_notification(user, content, url=url, send_feishu=send_feishu, send_pusher=send_pusher, priority=priority,
                            is_important=is_important, need_alert=need_alert)


def create_notification_to_developers(developers, content, url=None, send_pusher=True, send_feishu=True,
                                      priority='normal',
                                      is_important=False, need_alert=False):
    if isinstance(developers, six.string_types):
        developers = (developers,)
    else:
        developers = developers
    for developer in developers:
        create_developer_notification(developer, content, url=url, send_pusher=send_pusher, send_feishu=send_feishu,
                                      priority=priority,
                                      is_important=is_important, need_alert=need_alert)
