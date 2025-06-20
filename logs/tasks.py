# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from celery import shared_task
import requests
import logging

from logs.models import BrowsingHistory

LOCAL_HOST = ["127.0.0.1"]


@shared_task
def get_browsing_history_visitor_address(id):
    browsing_history = BrowsingHistory.objects.get(pk=id)
    try:
        if "127.0.0.1" in browsing_history.ip_address:
            browsing_history.address = "本地测试IP"
        else:
            ip_address = browsing_history.ip_address
            url = 'http://ip.taobao.com/service/getIpInfo.php?ip={}&accessKey=alibaba-inc'.format(ip_address)
            data = requests.get(url).json()
            if data['code'] == 0:
                browsing_history.address = data['data']['country'] + data['data']['area'] + data['data']['region'] + \
                                           data['data']['city']
        browsing_history.save()
    except Exception as e:
        logging.getLogger().error(e)
        pass
