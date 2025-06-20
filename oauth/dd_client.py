import hashlib
import json
import requests
from django.conf import settings


def get_dd_token():
    res = requests.get("https://oapi.dingtalk.com/gettoken", params={'corpid': settings.DD_CORP_ID,
                                                                     'corpsecret': settings.DD_CORP_SECRET})
    return res.json()['access_token']


def get_dd_jsapi_ticket(token):
    res = requests.get("https://oapi.dingtalk.com/get_jsapi_ticket", params={'access_token': token})
    return res.json()['ticket']


def get_dd_user_info(token, code):
    res = requests.get("https://oapi.dingtalk.com/user/getuserinfo", params={'access_token': token, 'code': code})
    return res.json()


def get_dd_sign(nonce, url, timestamp):
    jsapi_ticket = get_dd_jsapi_ticket(get_dd_token())
    plain = 'jsapi_ticket=' + jsapi_ticket + '&noncestr=' + nonce + '&timestamp=' + timestamp + '&url=' + url
    signature = hashlib.sha1(plain.encode('utf-8')).hexdigest()
    return signature


def dd_send_all(content, url=None):
    token = get_dd_token()
    if url:
        payload = {'touser': '@all', 'agentid': settings.DD_AGENT_ID, 'msgtype': 'link',
                   'link': {'title': content[0:10], 'text': content, 'messageUrl': url, 'picUrl': ''}}
    else:
        payload = {'touser': '@all', 'agentid': settings.DD_AGENT_ID, 'msgtype': 'text', 'text': {'content': content}}
    headers = {'content-type': 'application/json'}
    requests.post("https://oapi.dingtalk.com/message/send", params={'access_token': token}, data=json.dumps(payload),
                  headers=headers)


def dd_send_individual(dd_id, content, url=None):
    token = get_dd_token()
    if url:
        payload = {'touser': dd_id, 'agentid': settings.DD_AGENT_ID, 'msgtype': 'link',
                   'link': {'title': content[0:10], 'text': content, 'messageUrl': url, 'picUrl': ''}}
    else:
        payload = {'touser': dd_id, 'agentid': settings.DD_AGENT_ID, 'msgtype': 'text', 'text': {'content': content}}
    headers = {'content-type': 'application/json'}

    requests.post("https://oapi.dingtalk.com/message/send", params={'access_token': token}, data=json.dumps(payload),
                  headers=headers)
