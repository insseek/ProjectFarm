from pprint import pprint
from django.conf import settings
from django.utils.http import urlquote
from copy import deepcopy
from django.core.mail import send_mail

import requests


class FeiShuException(Exception):
    pass


def get_token_first(func):
    def new_func(self, *args, **kwargs):
        _ = self.tenant_access_token
        __ = self.app_access_token
        return func(self, *args, **kwargs)

    return new_func


def get_own_department_first(func):
    def new_func(self, *args, **kwargs):
        department_id = self.own_department
        if department_id is None:
            raise FeiShuException(
                "you must overwrite get_own_department method")
        return func(self, *args, **kwargs)

    return new_func


class FeiShu(object):
    _tenant_access_token = None
    _app_access_token = None
    _own_department_id = None

    def __init__(self, app_id=None, app_secret=None, tenant_access_token=None, app_access_token=None):
        self.app_id = app_id or settings.FEISHU_FARM_APP_ID
        self.app_secret = app_secret or settings.FEISHU_FARM_APP_SECRET
        self._tenant_access_token = tenant_access_token
        self._app_access_token = tenant_access_token

    def _get_app_access_token(self):
        uri = "https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal/"
        headers = {'Content-Type': 'application/json'}
        response = requests.post(uri, headers=headers, json={"app_id": self.app_id, "app_secret": self.app_secret})
        self._app_access_token = response.json()["app_access_token"]

    def _get_tenant_access_token(self):
        uri = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/"
        headers = {'Content-Type': 'application/json'}
        response = requests.post(uri, headers=headers, json={"app_id": self.app_id, "app_secret": self.app_secret})
        self._tenant_access_token = response.json()["tenant_access_token"]

    @property
    def tenant_access_token(self):
        if self._tenant_access_token is None:
            self._get_tenant_access_token()
        return self._tenant_access_token

    @property
    def app_access_token(self):
        if self._app_access_token is None:
            self._get_app_access_token()
        return self._app_access_token

    def get_oauth_url(self, redirect_uri):
        redirect_uri = urlquote(redirect_uri)
        url_temp = 'https://open.feishu.cn/open-apis/authen/v1/index?redirect_uri={redirect_uri}&app_id={app_id}'
        return url_temp.format(app_id=self.app_id, redirect_uri=redirect_uri)

    def get_user_access_token(self, code):
        token_url = 'https://open.feishu.cn/open-apis/authen/v1/access_token'
        request_data = {
            "app_access_token": self.app_access_token,
            "grant_type": "authorization_code",
            "code": code
        }
        response = requests.post(token_url, json=request_data)
        if response.status_code == 200:
            if "data" in response.json():
                data = response.json()['data']
                access_token = data.get('access_token')
                return access_token
            else:
                send_mail(
                    'Feishu AccessToken Error',
                    str(response.json()),
                    settings.DEFAULT_FROM_EMAIL,
                    ["fanping@chilunyc.com", ])

    @get_token_first
    def get_user_detail_by_token(self, user_access_token):
        uri = "https://open.feishu.cn/open-apis/authen/v1/user_info"
        headers = {'Content-Type': 'application/json'}
        headers.update({"Authorization": "Bearer {}".format(user_access_token)})
        data = requests.get(uri, headers=headers).json()
        return data['data']

    def get_app_auth_headers(self):
        return {"Authorization": "Bearer {}".format(self.app_access_token)}

    def get_tenant_auth_headers(self):
        return {"Authorization": "Bearer {}".format(self.tenant_access_token)}

    @get_token_first
    def get_chats(self, page=1, page_size=100):
        '''
        群列表
        :return:
        '''
        uri = "https://open.feishu.cn/open-apis/chat/v4/list"
        headers = {'Content-Type': 'application/json'}
        headers.update(self.get_tenant_auth_headers())
        params = {'page_size': page_size, 'page': page}
        response = requests.get(uri, headers=headers, params=params)
        return response.json()

    @get_token_first
    def get_contact(self):
        '''
        通讯录范围
        :return:
        '''
        uri = "https://open.feishu.cn/open-apis/contact/v1/scope/get"
        headers = {'Content-Type': 'application/json'}
        headers.update(self.get_tenant_auth_headers())
        response = requests.get(uri, headers=headers)
        return response.json()

    @get_token_first
    def get_users_by_mobiles_or_emails(self, mobiles=[], emails=[]):
        if isinstance(mobiles, str):
            mobiles = (mobiles,)
        else:
            mobiles = mobiles

        if isinstance(emails, str):
            emails = (emails,)
        else:
            emails = emails

        uri = "https://open.feishu.cn/open-apis/user/v1/batch_get_id"
        headers = self.get_tenant_auth_headers()
        params = {'mobiles': mobiles, 'emails': emails}
        response = requests.get(uri, headers=headers, params=params)
        return response.json()

    @get_token_first
    def send_message_to_user(self, user_id, message, link=None):
        url = 'https://open.feishu.cn/open-apis/message/v4/send/'
        headers = {'Content-Type': 'application/json'}
        headers.update(self.get_tenant_auth_headers())
        msg_type = 'text'
        content = {"text": message}
        if link and link.strip() and link.startswith("http"):
            msg_type = 'post'
            content = {
                "post": {
                    "zh_cn": {
                        "title": '',
                        'content': [
                            [
                                {
                                    "tag": "text",
                                    "un_escape": True,
                                    "text": message + '&nbsp;\n'
                                },
                                {
                                    "tag": "a",
                                    "text": "查看详情",
                                    "href": link
                                },
                            ]]
                    }
                }
            }
        data = {"user_id": user_id, "msg_type": msg_type, "content": content}
        response = requests.post(url, headers=headers, json=data)
        return response.json()

    @get_token_first
    def send_message_to_chat(self, chat_id, message, link=None, at_user_ids=[]):
        url = 'https://open.feishu.cn/open-apis/message/v4/send/'
        headers = {'Content-Type': 'application/json'}
        headers.update(self.get_tenant_auth_headers())
        if link:
            text_tag = {"tag": "text", "un_escape": True, "text": message + '&nbsp;\n'}
            link_tag = {"tag": "a", "text": "点击查看\n", "href": link}
            content_list = [text_tag, link_tag]
            for user_id in at_user_ids:
                content_list.append({"tag": "at", "user_id": user_id})
            msg_type = 'post'
            content = {"post": {"zh_cn": {"title": '', 'content': [content_list]}}}
        else:
            at_user_str = ''
            for user_id in at_user_ids:
                at_user_str = at_user_str + '<at user_id="{user_id}"></at> '.format(user_id=user_id)
            msg_type = 'text'
            content = {"text": message + at_user_str}
        data = {"chat_id": chat_id, "msg_type": msg_type, "content": content}
        response = requests.post(url, headers=headers, json=data)
        return response.json()

    @get_token_first
    def get_auth_departments(self, department_id=0):
        uri = "https://open.feishu.cn/open-apis/contact/v1/department/list"
        params = {'department_id': department_id}
        return requests.get(uri, headers=self.get_tenant_auth_headers(), params=params).json()

    @get_token_first
    def get_department_info(self, department_id):
        '''
        部门
        :param department_id:
        :return:
        '''
        uri = "https://open.feishu.cn/open-apis/contact/v1/department/info/get"
        params = {'department_id': department_id}
        return requests.get(uri, headers=self.get_tenant_auth_headers(), params=params).json()

    @get_token_first
    def get_department_users(self, department_id, page_size=100, offset=0):
        uri = "https://open.feishu.cn/open-apis/contact/v1/department/user/list"
        params = {'department_id': department_id, 'page_size': page_size, 'offset': offset, 'fetch_child': True}
        return requests.get(uri, headers=self.get_tenant_auth_headers(), params=params).json()

    @property
    def own_department(self):
        if self._own_department_id is None:
            self.get_own_department()
        return self._own_department_id

    def get_own_department(self):
        department_id = self.get_contact(
        )["data"]["authed_departments"][0]
        self.set_own_department(department_id)

    def set_own_department(self, department_id):
        self._own_department_id = department_id

    @get_token_first
    @get_own_department_first
    def get_own_deparment_info(self):
        return self.get_department_info(self._own_department_id)

    @get_token_first
    @get_own_department_first
    def get_own_department_users(self, page_size=100, offset=0):
        return self.get_department_users(self._own_department_id,
                                         page_size=page_size,
                                         offset=offset)

    @get_token_first
    @get_own_department_first
    def get_own_department_user_by_name(self, name):
        users = self.get_own_department_users()
        for user in users["data"]["user_list"]:
            if user["name"] == name:
                return user
        return {}

    @get_token_first
    def get_users_detail(self, open_ids=[], employee_ids=[]):
        uri = "https://open.feishu.cn/open-apis/contact/v1/user/batch_get"
        params = {'open_ids': open_ids, 'employee_ids': employee_ids}
        return requests.get(uri, headers=self.get_tenant_auth_headers(), params=params).json()

    @get_token_first
    @get_own_department_first
    def get_own_deparment_user_detail_by_name(self, name):
        user = self.get_own_department_user_by_name(name)
        if user:
            return self.get_users_detail(open_ids=[user["open_id"]])
        return {}

    @get_token_first
    def get_all_users(self):
        all_users = []
        authed_departments = self.get_auth_departments()["data"]["departments_list"]
        for department_id in authed_departments:
            user_list = self.get_department_users(department_id)["data"]["user_list"]
            all_users.extend(deepcopy(user_list))
        return all_users

    @get_token_first
    def get_all_users_detail(self):
        all_users = self.get_all_users()
        employee_ids = [u['employee_id'] for u in all_users]
        result_data = self.get_users_detail(employee_ids=employee_ids)
        return result_data['data']['user_infos']

    @get_token_first
    def get_chat_info(self, chat_id):
        uri = "https://open.feishu.cn/open-apis/chat/v4/info"
        headers = {'Content-Type': 'application/json'}
        headers.update(self.get_tenant_auth_headers())
        params = {'chat_id': chat_id}
        response = requests.get(uri, headers=headers, params=params)
        return response.json()

    @get_token_first
    def get_chat_members(self, chat_id):
        chat_info = self.get_chat_info(chat_id)
        members = chat_info['data']["members"]
        employee_ids = [member['user_id'] for member in members]
        return self.get_users_detail(employee_ids=employee_ids)

    @get_token_first
    def send_card_message_to_user(self, user_id, card_message):
        data = {
            "user_id": user_id,
            "msg_type": "interactive",
            "card": card_message
        }
        url = 'https://open.feishu.cn/open-apis/message/v4/send/'
        headers = {'Content-Type': 'application/json'}
        headers.update(self.get_tenant_auth_headers())
        response = requests.post(url, headers=headers, json=data)
        return response.json()

    def build_card_message(self, title=None, text=None, fields=None, fields_groups=None, link=None, template='blue'):
        #  title 标题  template为卡片支持的模板 值有限
        # https://open.feishu.cn/document/ukTMukTMukTM/ukTNwUjL5UDM14SO1ATN
        # text 单文本   文本集合    多组文本集合
        # link 连接
        ''' 标题：需求报告审核提醒（title）

            我是单文本（text）

            需求名称：【120】北京大成律师（fields）
            申请人：鄢波
            申请时间：2019.9.9  13:00

            需求名称：【120】北京大成律师（fields_group[0]）
            申请人：鄢波
            申请时间：2019.9.9  13:00

            需求名称：【120】北京大成律师（fields_group[1]）
            申请人：鄢波
            申请时间：2019.9.9  13:00

            查看详情（link）
        '''
        data = deepcopy(
            {
                "config": {
                    "wide_screen_mode": True
                },
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": title
                    },
                    "template": template
                },
                "elements": [
                ]
            }
        )

        elements = data['elements']
        if text:
            element = {
                "tag": "div",
                "text": {
                    "tag": "plain_text",
                    "content": text
                }
            }
            elements.append(element)
        if fields:
            element = {
                "tag": "div",
                "fields": [
                ],
            }
            for text in fields:
                element['fields'].append(
                    {
                        "is_short": False,
                        "text": {
                            "tag": "plain_text",
                            "content": text
                        }
                    }
                )
            elements.append(element)
        if fields_groups:
            for fields in fields_groups:
                element = {
                    "tag": "div",
                    "fields": [
                    ],
                }
                for text in fields:
                    element['fields'].append(

                        {
                            "is_short": False,
                            "text": {
                                "tag": "plain_text",
                                "content": text
                            }
                        }
                    )

                elements.append(element)

        if link:
            element = {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {
                            "tag": "lark_md",
                            "content": "查看详情"
                        },
                        "url": link,
                        "type": "primary"
                    },
                ]
            }
            elements.append(element)
        return data

    def get_card_message_demo(self):
        data = {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "需求报告审核提醒"
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "plain_text",
                        "content": "Content module"
                    }
                },

                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": False,
                            "text": {
                                "tag": "plain_text",
                                "content": "需求名称：【120】北京大成律师"
                            }
                        },
                        {
                            "is_short": False,
                            "text": {
                                "tag": "plain_text",
                                "content": "申请人：鄢波"
                            }
                        },
                        {
                            "is_short": False,
                            "text": {
                                "tag": "plain_text",
                                "content": "申请时间：2019.9.9  13:00"
                            }
                        }
                    ],
                },
                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": False,
                            "text": {
                                "tag": "plain_text",
                                "content": "需求名称：【120】北京大成律师"
                            }
                        },
                        {
                            "is_short": False,
                            "text": {
                                "tag": "plain_text",
                                "content": "申请人：鄢波"
                            }
                        },
                        {
                            "is_short": False,
                            "text": {
                                "tag": "plain_text",
                                "content": "申请时间：2019.9.9  13:00"
                            }
                        }
                    ],
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "lark_md",
                                "content": "查看详情"
                            },
                            "url": "https://open.feishu.cn/document",
                            "type": "primary"
                        },
                    ]
                }
            ]
        }
        return data

# feishu = FeiShu()
#
# data = {'title': '需求报告审核提醒',
#         'fields': ['需求【22 需求名称 】', '报告【报告名称 项目反馈报告】', '申请人：新用户', '申请时间：2020-09-11 18:12',
#                    '备注：1'],
#         "link": settings.SITE_URL + '/mp/reports/detail/edit/?uid={}'.format('r200911dAhVn7cvEq4nyXGU')}
# message = feishu.build_card_message(
#     **data
# )
# print(message)
# pprint(message)
# feishu.send_card_message_to_user("19g2g639", message)
