import json
import logging

from django.conf import settings

from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest

logger = logging.getLogger()


class AliyunApi(object):

    def __init__(self, access_key_id=None, access_key_secret=None):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.client = AcsClient(self.access_key_id, self.access_key_secret, 'cn-hangzhou')

    def send_login_check_code_sms(self, phone, code, product=''):
        template_code = "SMS_67670105"
        template_param = {"code": code, "product": product}
        self.send_sms(phone, template_code, template_param)

    def send_app_bug_sms(self, phone, content, app_name='', env=''):
        template_code = "SMS_187952586"
        template_param = {"content": content[:19], "product": app_name, "appName": app_name, 'env': env}
        self.send_sms(phone, template_code, template_param)

    def send_project_cicd_sms(self, phone, app_name, branch, stage, group, project, job_id):

        template_code = "SMS_193235768"
        template_param = {'app_name': app_name, "branch": branch, "stage": stage, 'group': group, "project": project,
                          'job_id': job_id}
        self.send_sms(phone, template_code, template_param)

    def send_project_cicd_passed_sms(self, phone, app_name, branch, group, project, pipeline_id):
        template_code = "SMS_201652046"
        template_param = {'app_name': app_name, "branch": branch, 'group': group, "project": project,
                          'pipeline_id': pipeline_id}
        self.send_sms(phone, template_code, template_param)

    def send_sms(self, phone, template_code, template_param):
        request = CommonRequest(domain="dysmsapi.aliyuncs.com", version='2017-05-25', action_name='SendSms')
        request.set_accept_format('json')
        request.set_method('POST')
        request.set_protocol_type('https')  # https | htt
        query_params = {
            'RegionId': "cn-hangzhou",
            'PhoneNumbers': phone,
            'SignName': "齿轮易创",
            'TemplateCode': template_code,
            'TemplateParam': json.dumps(template_param, ensure_ascii=False)
        }
        for key, value in query_params.items():
            request.add_query_param(key, value)
        response_data = self.client.do_action_with_exception(request)
        response_data = json.loads(response_data.decode(encoding='utf-8'))
        if response_data.get('Code') == 'OK':
            return True
        else:
            logger.error(response_data.get('Code') + ": " + response_data.get("Message"))
