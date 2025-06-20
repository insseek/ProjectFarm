# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import logging
import os

from django.core.files.base import ContentFile
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta

from celery import shared_task
import requests
import audioread
from mutagen.mp4 import MP4
from mutagen.mp3 import MP3

from proposals.models import Proposal
from notifications.tasks import send_call_status_notice
from farmbase.utils import gen_uuid, seconds_to_format_str

logger = logging.getLogger()


@shared_task
def download_call_record_file(call_record_id, re_download=False):
    from webphone.models import CallRecord
    from webphone.huawei_viocecall import HuaWeiVoiceCall
    record = CallRecord.objects.get(pk=call_record_id)
    if re_download or not record.file:
        if not record.record_file_download_url or (
                record.download_url_updated_at and record.download_url_updated_at < timezone.now() - timedelta(
            minutes=30)):
            if record.record_domain and record.record_object_name:
                logger.info(
                    '开始获取需求【{}】，通话记录【{}】录音文件下载连接'.format(record.proposal if record.proposal else '', record.id))
                voice_call = HuaWeiVoiceCall()
                record_file_download_url = voice_call.get_record_file_download_url(
                    record_object_name=record.record_object_name,
                    record_domain=record.record_domain)
                if record_file_download_url:
                    logger.info(
                        '获取需求【{}】，通话记录【{}】录音文件下载连接成功'.format(record.proposal if record.proposal else '', record.id))
                    record.record_file_download_url = record_file_download_url
                    record.download_url_updated_at = timezone.now()
                    record.save()
                else:
                    logger.info(
                        '获取需求【{}】，通话记录【{}】录音文件下载连接失败'.format(record.proposal if record.proposal else '', record.id))

        if record.record_file_download_url:
            record_object_name = record.record_object_name
            file_suffix = record_object_name.rsplit(".", 1)[1]
            caller_name = record.caller.username if record.caller_id and User.objects.filter(
                pk=record.caller_id).exists() else ''
            if record.proposal_id and Proposal.objects.filter(
                    pk=record.proposal_id).exists():
                proposal_name = "【{}】{}".format(record.proposal_id, record.proposal.name)
            else:
                proposal_name = '个人'
            record_date = record.record_date.strftime("%y%m%d") if record.record_date else timezone.now().strftime(
                "%Y%m%d")
            file_name = "{caller}-{proposal}-{record_date}{id}.{file_suffix}".format(caller=caller_name,
                                                                                     proposal=proposal_name,
                                                                                     record_date=record_date,
                                                                                     id=record.id,
                                                                                     file_suffix=file_suffix)
            content = requests.get(record.record_file_download_url, verify=False).content
            record_file = ContentFile(content, file_name)
            record.file = record_file
            record.file_size = str(record_file.size)
            record.file_suffix = file_suffix
            record.filename = file_name
            record.record_flag = 1
            record.save()
            notice_data = {}
            notice_data["eventType"] = 'download_file'
            notice_data["message"] = "当前通话录音文件已生成"
            try:
                send_call_status_notice(notice_data, record.session_id)
            except Exception as e:
                logger.error(e)


@shared_task
def get_call_record_callee_duration(call_record_id):
    from webphone.models import CallRecord
    record = CallRecord.objects.get(pk=call_record_id)
    if record.file and not record.call_duration:
        download_record_file_to_local_server(record)
        total_seconds = 0
        file_path = call_record_path(record)
        if record.file_suffix == 'mp3' or record.filename.endswith('mp3'):
            audio = MP3(file_path)
            total_seconds = audio.info.length
        if record.file_suffix == 'm4a' or record.filename.endswith('m4a'):
            audio = MP4(file_path)
            total_seconds = audio.info.length
        if record.file_suffix == 'wav' or record.filename.endswith('wav'):
            with audioread.audio_open(file_path) as f:
                total_seconds = f.duration
        logger.info('{}, {}'.format(file_path, total_seconds))
        if total_seconds:
            call_duration = seconds_to_format_str(total_seconds)
            logger.info('{}, {}'.format(file_path, call_duration))
            record.call_duration = call_duration
            record.save()
            os.remove(file_path)
            return record.call_duration


def call_record_path(record):
    suffix = record.file_suffix if record.file_suffix else (record.filename.rsplit('.', 1))[1]
    return settings.MEDIA_ROOT + 'call_records/{}-{}.{suffix}'.format(record.proposal_id, record.id, suffix=suffix)


def download_record_file_to_local_server(record):
    if record.file:
        file_path = call_record_path(record)
        if not os.path.isfile(file_path):
            if not os.path.exists(os.path.dirname(file_path)):
                os.makedirs(os.path.dirname(file_path))
            with open(file_path, 'wb') as file:
                content = record.file.file.read()
                file.write(content)
