# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import logging
from django.core.cache import cache
from celery import shared_task
import xlrd

from farmbase.utils import get_md5
from clients.models import TrackCodeFile, LeadTrack

logger = logging.getLogger(__name__)


@shared_task
def extract_lead_track_data_from_excel(track_id):
    track_file = TrackCodeFile.objects.filter(pk=track_id)
    if track_file.exists():
        track_file = track_file.first()
        file_path = track_file.output_path
        wb = xlrd.open_workbook(filename=file_path)  # 打开文件
        sheet1 = wb.sheet_by_index(0)  # 通过索引获取表格

        # excel文件中对应的字段
        field_names = ['channel', 'media', 'account', 'plan', 'unit', 'keywords', 'device', 'url', 'track_url',
                       'track_code', 'md5_hash']
        for rx in range(1, sheet1.nrows):
            origin_data = sheet1.row_values(rx)[:11]
            track_data = [str(int(filed_value) if isinstance(filed_value, float) else filed_value).strip() for
                          filed_value in origin_data]

            url = track_data[7]
            track_url = track_data[8]
            track_code = track_data[9]
            md5_hash = track_data[10]
            if not md5_hash:
                md5_hash = get_md5(''.join(track_data[:7]))
            track_data_dict = dict(zip(field_names[:7], track_data))
            lead_trace, created = LeadTrack.objects.get_or_create(**track_data_dict)
            lead_trace.url = url
            lead_trace.track_code = track_code
            lead_trace.md5_hash = md5_hash
            lead_trace.track_url = track_url
            lead_trace.save()
