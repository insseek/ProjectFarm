# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import logging
from celery import shared_task

from django.contrib.auth.models import User

from farmbase.utils import get_protocol_host
from gearmail.models import EmailRecord
from gearmail.utils import farm_send_email
from notifications.utils import create_notification
from gearfarm.utils.page_path_utils import build_page_path


@shared_task
def send_project_email(user_id, email_record_id, email_signature):
    user = User.objects.get(pk=user_id)
    email_record = EmailRecord.objects.get(pk=email_record_id)
    project = email_record.project
    sent, message = farm_send_email(email_record, email_signature)
    # priority = 'important' if not sent else 'normal'
    content = message
    url = get_protocol_host() + build_page_path("project_view", kwargs={"id": project.id}, params={"anchor": "mails"})
    create_notification(user, content, url, priority='important')
