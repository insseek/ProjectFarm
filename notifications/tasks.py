from __future__ import absolute_import, unicode_literals
import logging

from django.conf import settings
from django.contrib.auth.models import User
from celery import shared_task

from notifications.pusher import notification_pusher
from notifications.serializers import NotificationSerializer
from notifications.models import Notification
from oauth.utils import get_feishu_client
from auth_top.models import TopUser
from auth_top.utils import get_top_user_data


@shared_task
def send_pusher_message(channel, event, data, operator_id=None):
    operator = get_top_user_data(top_user=TopUser.objects.get(pk=operator_id)) if operator_id else None
    try:
        notification_pusher.trigger(channel, event,
                                    {'message': {'operator': operator, 'data': data}})
    except Exception as e:
        logger = logging.getLogger()
        logger.error(e)


@shared_task
def send_developer_notification(developer_id, notification_id):
    try:
        notification = Notification.objects.get(pk=notification_id, developer_id=developer_id)
        data = NotificationSerializer(notification).data
        notification_pusher.trigger('developer-notifications', 'new-notification',
                                    {'message': {'receiver': developer_id, 'data': data}})
    except Exception as e:
        logger = logging.getLogger()
        logger.error(e)


@shared_task
def send_notification(user_id, notification_id):
    try:
        notification = Notification.objects.get(pk=notification_id)
        data = NotificationSerializer(notification).data
        notification_pusher.trigger('new-notification-channel', 'new-notification',
                                    {
                                        'message': {'receiver': user_id, 'data': data}
                                    })
    except Exception as e:
        logger = logging.getLogger()
        logger.error(e)


@shared_task
def send_top_user_notification(notification_id, app_id=None):
    try:
        notification = Notification.objects.get(pk=notification_id)
        data = NotificationSerializer(notification).data
        channel_name = 'new-notification-channel'
        if app_id:
            channel_name = app_id + '-' + channel_name
        notification_pusher.trigger(channel_name, 'new-notification',
                                    {
                                        'message': {'receiver': data['owner'], 'data': data}
                                    })
    except Exception as e:
        logger = logging.getLogger()
        logger.error(e)


@shared_task
def send_report_new_comment(id, author_id):
    from reports.models import Report
    try:
        report = Report.objects.get(pk=id)
        notification_pusher.trigger('report-{id}-channel'.format(id=id),
                                    'new-comment',
                                    {
                                        'message': {'report': report.id, 'report_uid': report.uid,
                                                    'author_id': author_id}
                                    })
    except Exception as e:
        logger = logging.getLogger()
        logger.error(e)


@shared_task
def send_report_new_log(id):
    from reports.models import Report
    try:
        report = Report.objects.get(pk=id)
        notification_pusher.trigger('report-{id}-channel'.format(id=id),
                                    'new-log',
                                    {
                                        'message': {'report': report.id, 'report_uid': report.uid}
                                    })
    except Exception as e:
        logger = logging.getLogger()
        logger.error(e)


@shared_task
def send_report_editable_data_update_reminder(id):
    from reports.models import Report
    try:
        report = Report.objects.get(pk=id)
        notification_pusher.trigger('report-{id}-channel'.format(id=id),
                                    'editable_data_update',
                                    {
                                        'message': {'report': report.id, 'report_uid': report.uid}
                                    })
    except Exception as e:
        logger = logging.getLogger()
        logger.error(e)


@shared_task
def send_report_update_reminder(id, user_id, page_view_uuid=None):
    from reports.models import Report
    try:
        report = Report.objects.get(pk=id)
        notification_pusher.trigger('report-{id}-channel'.format(id=id),
                                    'content-update',
                                    {
                                        'message': {'report_id': report.id, 'report_uid': report.uid,
                                                    'editing_user_id': user_id, 'page_view_uuid': page_view_uuid}
                                    })
    except Exception as e:
        logger = logging.getLogger()
        logger.error(e)


@shared_task
def send_document_data(user_id, data):
    try:
        notification_pusher.trigger('{}-channel'.format(user_id),
                                    'delivery-documents-create-success', {
                                        'message': data
                                    })
    except Exception as e:
        logger = logging.getLogger()
        logger.error(e)


@shared_task
def send_task_auto_update_reminder(type_name, object_id):
    try:
        notification_pusher.trigger('{}-{}-channel'.format(type_name, object_id),
                                    'task_auto_update', {
                                        'message': {"result": True}
                                    })
    except Exception as e:
        logger = logging.getLogger()
        logger.error(e)


@shared_task
def send_project_schedule_update_reminder(type_name, object_id):
    try:
        notification_pusher.trigger('{}-{}-channel'.format(type_name, object_id),
                                    'project_schedule_update', {
                                        'message': {"result": True}
                                    })
    except Exception as e:
        logger = logging.getLogger()
        logger.error(e)


@shared_task
def send_project_playbook_update_reminder(object_id):
    try:
        notification_pusher.trigger('playbook-update-channel',
                                    'project_playbook_update', {
                                        'message': {"result": True, 'object_id': object_id}
                                    })
    except Exception as e:
        logger = logging.getLogger()
        logger.error(e)


@shared_task
def send_project_job_position_update_reminder(object_id):
    try:
        notification_pusher.trigger('project-update-channel'.format(object_id),
                                    'project_job_position_update', {
                                        'message': {"result": True,
                                                    "project_id": object_id}
                                    })
    except Exception as e:
        logger = logging.getLogger()
        logger.error(e)


@shared_task
def send_project_status_update_reminder(object_id):
    try:
        notification_pusher.trigger('project-update-channel',
                                    'project-status-update', {
                                        'message': {"result": True,
                                                    "project_id": object_id}
                                    })
    except Exception as e:
        logger = logging.getLogger()
        logger.error(e)


@shared_task
def send_project_data_update_reminder(object_id):
    try:
        notification_pusher.trigger('project-{}-update-channel'.format(object_id),
                                    'project-data-update', {
                                        'message': {"result": True,
                                                    "project_id": object_id}
                                    })
    except Exception as e:
        logger = logging.getLogger()
        logger.error(e)


@shared_task
def send_proposal_status_update_reminder(object_id):
    try:
        notification_pusher.trigger('proposal-update-channel',
                                    'proposal-status-update', {
                                        'message': {"result": True,
                                                    "proposal_id": object_id}
                                    })
    except Exception as e:
        logger = logging.getLogger()
        logger.error(e)


@shared_task
def send_tasks_update_to_principal(user_id):
    try:
        notification_pusher.trigger('{}-channel'.format(user_id),
                                    'tasks_update', {
                                        'message': {"result": True}
                                    })
    except Exception as e:
        logger = logging.getLogger()
        logger.error(e)


@shared_task
def send_call_status_notice(content, session_id):
    try:
        notification_pusher.trigger('call-{}'.format(session_id),
                                    'call_status_notice', {
                                        'message': content
                                    })
    except Exception as e:
        logger = logging.getLogger()
        logger.error(e)


@shared_task
def send_feishu_message_to_individual(feishu_user_id, message, link=None):
    client = get_feishu_client()
    client.send_message_to_user(feishu_user_id, message, link=link)


@shared_task
def send_feishu_card_message_to_individual(feishu_user_id, message):
    client = get_feishu_client()
    card_message = client.build_card_message(**message)
    client.send_card_message_to_user(feishu_user_id, card_message)


@shared_task
def send_feishu_message_to_group(group_name, message, link=None):
    users = User.objects.filter(groups__name=group_name, is_active=True)
    for user in users:
        feishu_user_id = user.profile.feishu_user_id
        if feishu_user_id:
            send_feishu_message_to_individual(feishu_user_id, message, link=link)


@shared_task
def send_feishu_message_to_all(message, link=None):
    client = get_feishu_client()
    all_chat_id = settings.FEISHU_ALL_CHAT_ID
    client.send_message_to_chat(all_chat_id, message, link=link)
