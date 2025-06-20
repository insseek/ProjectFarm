# -*- coding:utf-8 -*-
import json
import logging
from base64 import b64decode, b64encode

from django.conf import settings
import requests

from webphone.models import HuaWeiVoiceCallAuth

logger = logging.getLogger()



class HuaWeiVoiceCall(object):
    def __init__(self, app_key=None, username=None, password=None,
                 host=None, port=None, access_token=None, refresh_token=None, bind_number=None,
                 display_number=None, display_callee_number=None,
                 base_url=None, request_timeout=None, request_protocol=None):
        """Constructs a HuaWeiVoiceCall API client.

        If `access_token` is given, all of the API methods in the client
        will work to read and modify HuaWeiVoiceCall documents.

        Otherwise, only `get_authorization_url` and `get_access_token`
        work, and we assume the client is for a server using the HuaWeiVoiceCall API's
        OAuth endpoint.
        """
        self.app_key = app_key if app_key else settings.HUAWEI_VOICE_CALL_APP_KEY
        self.username = username if username else settings.HUAWEI_VOICE_CALL_USERNAME
        self.password = password if password else settings.HUAWEI_VOICE_CALL_PASSWORD
        self.host = host if host else settings.HUAWEI_VOICE_CALL_HOST
        self.port = port if port else settings.HUAWEI_VOICE_CALL_PORT
        self.bind_number = bind_number if bind_number else settings.HUAWEI_VOICE_CALL_BIND_NUMBER
        self.display_number = display_number if display_number else settings.HUAWEI_VOICE_CALL_DISPLAY_NUMBER
        self.display_callee_number = display_callee_number if display_callee_number else settings.HUAWEI_VOICE_CALL_DISPLAY_CALLEE_NUMBER

        self.login_url_template = '/rest/fastlogin/v1.0?app_key={app_key}&username={username}&format=json'
        self.logout_url_template = '/rest/logout/v1.0?app_key={app_key}&access_token={access_token}'
        self.refresh_access_token_url = '/omp/oauth/refresh'
        self.click2call_url_template = '/rest/httpsessions/click2Call/v2.0?app_key={app_key}&access_token={access_token}&format=json'
        self.stop_call_url_template = '/rest/httpsessions/callStop/v2.0?app_key={app_key}&access_token={access_token}&format=json'
        self.record_file_download_url_template = '/rest/provision/voice/record/v1.0?app_key={app_key}&access_token={access_token}&fileName={record_object_name}&recordDomain={record_domain}'

        self.download_record_url_header_content_type = 'application/json;charset=UTF-8'
        self.auth_header_content_type = 'application/x-www-form-urlencoded;charset=UTF-8'
        self.click2call_header_content_type = 'application/json;charset=UTF-8'
        self.request_timeout = request_timeout if request_timeout else 10
        self.request_protocol = request_protocol if request_protocol else 'https'
        self.base_url = base_url if base_url else '{request_protocol}://{host}:{port}'.format(
            request_protocol=self.request_protocol, host=self.host, port=self.port)
        self.status_url = b64encode(
            bytes(settings.SITE_URL + "/api/webphone/call_status_notice", encoding='utf-8')).decode()
        self.fee_url = b64encode(
            bytes(settings.SITE_URL + "/api/webphone/call_fee_notice", encoding='utf-8')).decode()
        self.authorization = self.get_authorization()
        self.access_token = access_token if access_token else (
            self.authorization.access_token if self.authorization else None)
        self.refresh_token = refresh_token if refresh_token else (
            self.authorization.refresh_token if self.authorization else None)

    def get_login_url(self, username=None):
        if not username:
            username = self.username
        """Returns the authorization login url."""
        return self.base_url + self.login_url_template.format(app_key=self.app_key, username=username)

    def get_login_header(self):
        """Returns the authorization login header."""
        header = {'Authorization': self.password, 'content-type': self.auth_header_content_type}
        return header

    def get_access_token(self):
        if not self.access_token:
            self.login_and_get_token_data()
        return self.access_token

    def login_and_get_token_data(self, username=None):
        login_url = self.get_login_url(username)
        login_header = self.get_login_header()
        response = requests.post(login_url, headers=login_header, verify=False)
        data = response.json()
        if data.get('access_token', None):
            self.access_token = data.get('access_token')
            self.refresh_token = data.get('refresh_token')
            return data

    def refresh_and_get_token_data(self, username=None):
        username = username if username else self.username
        login_url = self.get_login_url(username)
        login_header = self.get_login_header()
        response = requests.post(login_url, headers=login_header, verify=False)
        data = response.json()
        if data.get('access_token', None):
            self.access_token = data.get('access_token')
            self.refresh_token = data.get('refresh_token')
            self.update_authorization_token(data)
        return data

    def logout_and_clear_access_token(self, username=None):
        username = username if username else self.username
        login_url = self.get_login_url(username)
        login_header = self.get_login_header()
        response = requests.post(login_url, headers=login_header, verify=False)
        data = response.json()
        return data

    def get_click2call_url(self):
        """Returns the authorization login url."""
        return self.base_url + self.click2call_url_template.format(app_key=self.app_key,
                                                                   access_token=self.access_token)

    def get_click2call_header(self):
        """Returns the authorization login header."""
        header = {'content-type': self.click2call_header_content_type}
        return header

    def get_valid_phone_number(self, number):
        if isinstance(number, str):
            number = '+86' + number if not number.startswith('+86') else number
        return number

    def click2call(self, caller_number=None, callee_number=None, bind_number=None, display_number=None,
                   display_callee_number=None, record_flag=False, user_data='Farm User', record_hint_tone=None):
        caller_number = self.get_valid_phone_number(caller_number)
        callee_number = self.get_valid_phone_number(callee_number)
        bind_number = self.get_valid_phone_number(bind_number if bind_number else self.bind_number)
        display_number = self.get_valid_phone_number(display_number if display_number else self.display_number)
        display_callee_number = self.get_valid_phone_number(
            display_callee_number if display_callee_number else self.display_callee_number)
        click2call_url = self.get_click2call_url()
        click2call_header = self.get_click2call_header()
        if record_flag == 'true' or record_flag == True:
            record_flag = 'true'
        else:
            record_flag = 'false'
        request_data = {"bindNbr": bind_number,  # 按照提供的信息填写
                        "displayNbr": display_number,  # 按照提供的信息填写，若有提供，则为必填参数
                        "callerNbr": caller_number,  # 填写主叫号码
                        "calleeNbr": callee_number,  # 填写被叫号码
                        "displayCalleeNbr": display_callee_number,  # 按照提供的信息填写,若有提供，则为必填参数
                        "statusUrl": self.status_url,
                        "feeUrl": self.fee_url,
                        'maxDuration': settings.HUAWEI_VOICE_MAX_DURATION,
                        'lastMinToUE': "both",
                        'calleeMedia': "all",
                        'recordFlag': record_flag,  # 按照提供的信息填写
                        'userData': user_data}
        if record_flag == 'true' and record_hint_tone == None:
            request_data['recordHintTone'] = settings.HUAWEI_VOICE_RECORD_HINT_TONE
        response = requests.post(click2call_url, data=json.dumps(request_data), headers=click2call_header,
                                 verify=False)
        data = response.json()
        return data

    def stop_call(self, session_id, signal='call_stop'):
        stop_call_url = self.base_url + self.stop_call_url_template.format(app_key=self.app_key,
                                                                           access_token=self.access_token)
        click2call_header = self.get_click2call_header()
        request_data = {"sessionid": session_id,  # 按照提供的信息填写
                        "signal": signal,  # 按照提供的信息填写，若有提供，则为必填参数
                        }
        response = requests.post(stop_call_url, data=json.dumps(request_data),
                                 headers=click2call_header,
                                 verify=False)
        data = response.json()
        return data

    def login_and_update_authorization(self):
        data = self.login_and_get_token_data()
        authorization = self.update_authorization_token(data)
        return authorization

    def update_authorization_token(self, token_data):
        if self.username and self.password:
            authorization, created = HuaWeiVoiceCallAuth.objects.get_or_create(username=self.username,
                                                                               password=self.password)
            if token_data:
                authorization.access_token = token_data['access_token']
                authorization.refresh_token = token_data['refresh_token']
                authorization.expires_in = token_data['expires_in']
                authorization.save()
                self.authorization = authorization
            return authorization

    def get_authorization(self):
        if self.username and self.password:
            authorizations  = HuaWeiVoiceCallAuth.objects.filter(username=self.username)
            if authorizations.exists():
                authorization = authorizations.first()
                if authorization.password != self.password:
                    authorization.password = self.password
                    authorization.save()
            else:
                authorization, created = HuaWeiVoiceCallAuth.objects.get_or_create(username=self.username,
                                                                               password=self.password)
            if not authorization.access_token:
                authorization = self.login_and_update_authorization()
            return authorization

    def record_file_url(self, record_object_name, record_domain):
        url = self.base_url + self.record_file_download_url_template.format(app_key=self.app_key,
                                                                            access_token=self.access_token,
                                                                            record_object_name=record_object_name,
                                                                            record_domain=record_domain)
        return url

    def get_record_file_download_url(self, record_object_name, record_domain, retry=True):
        url = self.record_file_url(record_object_name, record_domain)
        location = None
        click2call_header = self.get_click2call_header()
        try:
            response = requests.get(url, headers=click2call_header,
                                    verify=False, allow_redirects=False)
            if response.status_code == 301:
                location = response.headers.get('location', None)
            elif response.json().get('resultcode', '') == '1010004' and retry:
                self.login_and_update_authorization()
                location = self.get_record_file_download_url(record_object_name, record_domain, retry=False)
            if not location:
                logger.info("获取录音文件下载文件错误：" + str(response.json()))
        except Exception as e:
            logger.error(e)
        return location
