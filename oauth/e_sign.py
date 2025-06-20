import json
import logging

from django.conf import settings
from django.core.cache import cache
import requests

logger = logging.getLogger(__name__)


class ESign(object):
    """
    E签宝的类用于调用第三方E签宝的API完成工程师合同签署流程
    """
    app_id = settings.E_SIGN_APP_ID
    app_secret = settings.E_SIGN_APP_SECRET
    # sandbox = 'https://smlopenapi.esign.cn'
    # official = 'https://openapi.esign.cn'
    domain = settings.E_SIGN_DOMAIN
    get_token_api = domain + '/v1/oauth2/access_token'
    # 创建个人账户
    create_person_account_api = domain + '/v1/accounts/createByThirdPartyUserId'
    # 获取签署文件上传地址
    get_upload_url_and_fileid_api = domain + '/v1/files/getUploadUrl'
    # 一步发起签署
    one_step_initiation_signature_api = domain + '/api/v2/signflows/createFlowOneStep'
    # 获取签署链接
    get_signature_url_api = domain + '/v1/signflows/{flowId}/executeUrl'
    # PDF验签
    PDF_verify_api = domain + '/v1/documents/{fileId}/verify'
    # 撤销签署流程
    revoke_signature_flow_api = domain + '/v1/signflows/{flowId}/revoke'
    # 签署流程查询
    sign_flow_query_api = domain + '/v1/signflows/{flowId}'
    # 签署文件下载
    download_contract_documents_api = domain + '/v1/signflows/{flowId}/documents'
    # 获取个人实名认证地址
    personage_real_name_authentication_api = domain + '/v2/identity/auth/web/{accountId}/indivIdentityUrl'

    def __init__(self):
        pass

    @classmethod
    def get_oauth2_token(cls):
        """
        获取OAuth2.0 token
        """
        token = cache.get('e_sign_token', None)
        if not token:
            token = cls.refresh_oauth2_token()
        return token

    @classmethod
    def refresh_oauth2_token(cls):
        token = cls.create_oauth2_token()
        if not token:
            token = cls.create_oauth2_token()
        if token:
            cache.set('e_sign_token', token, 60 * 110)
        return token

    @classmethod
    def create_oauth2_token(cls):
        """
        获取OAuth2.0 token
        """
        params = {
            "appId": cls.app_id,
            "secret": cls.app_secret,
            "grantType": "client_credentials"
        }
        ret = requests.get(url=cls.get_token_api, params=params)
        data = json.loads(ret.text)
        if data['code'] == 0:
            token = data['data']['token']
            return token
        else:
            logger.info("获取ESign失败, 错误码: {}, 错误信息: {}".format(data['code'], data['message']))

    @classmethod
    def generate_header(cls):
        """
        生成 headers
        """
        headers = {
            'X-Tsign-Open-App-Id': cls.app_id,
            'X-Tsign-Open-Token': cls.get_oauth2_token(),
            'Content-Type': 'application/json'
        }
        return headers

    @classmethod
    def create_person_account(cls, user_id, name, id_card_number, mobile, email, retry=True):
        """
        创建签署人的账户
        """
        params = {
            "thirdPartyUserId": user_id,
            "name": name,
            "idType": "CRED_PSN_CH_IDCARD",
            "idNumber": id_card_number,
            "mobile": mobile,
            "email": email
        }
        ret = requests.post(url=cls.create_person_account_api, data=json.dumps(params), headers=cls.generate_header())
        data = json.loads(ret.text)
        account_id = None
        if data['code'] == 0:
            ret_msg = '获取成功'
            account_id = data['data']['accountId']
        else:
            if data['code'] == 401:
                cls.refresh_oauth2_token()
            if retry:
                return cls.create_person_account(user_id, name, id_card_number, mobile, email, retry=False)
            ret_msg = "创建失败, 错误码: {}, 错误信息: {}".format(data['code'], data['message'])
        return data['code'], ret_msg, account_id

    @classmethod
    def get_upload_url(cls, content_md5, file_name, file_size):
        """
        获取上传PDF的上传链接和文件的 file_id
        """
        params = {
            "contentMd5": content_md5,
            "contentType": 'application/pdf',
            "convert2Pdf": False,
            "fileName": file_name,
            "fileSize": file_size
        }
        ret = requests.post(url=cls.get_upload_url_and_fileid_api, data=json.dumps(params),
                            headers=cls.generate_header())
        data = json.loads(ret.text)
        upload_url = None
        file_id = None
        if data['code'] == 0:
            ret_msg = '获取成功'
            upload_url = data['data']['uploadUrl']
            file_id = data['data']['fileId']
        else:
            if data['code'] == 401:
                cls.refresh_oauth2_token()
            ret_msg = "获取失败, 错误码: {}, 错误信息: {}".format(data['code'], data['message'])
        return data['code'], ret_msg, upload_url, file_id

    @classmethod
    def upload_contract_pdf(cls, upload_url, content_md5, file):
        """
        上传合同文件到E签宝
        """
        headers = {
            "Content-MD5": content_md5,
            "Content-Type": "application/pdf"
        }
        ret = requests.put(url=upload_url, data=file, headers=headers)
        data = json.loads(ret.text)
        if data['errCode'] == 0:
            ret_msg = '上传成功'
        else:
            if data['code'] == 401:
                cls.refresh_oauth2_token()
            ret_msg = "上传失败, 错误码: {}, 错误信息: {}".format(data['errCode'], data['msg'])
        return data['errCode'], ret_msg

    @classmethod
    def one_step_create_sign_flow(cls, file_id, file_name, account_id, contract_name, company_coordinate,
                                  user_coordinate):
        """
        一步发起签署，创建签署流程
        """
        params = {
            "docs": [
                {
                    "fileId": file_id,
                    "fileName": file_name
                }
            ],
            "flowInfo": {
                "autoArchive": True,
                "autoInitiate": True,
                "businessScene": contract_name,
                "flowConfigInfo": {
                    "noticeDeveloperUrl": settings.E_SIGN_NOTICE_URL,
                    "redirectUrl": "",
                    "signPlatform": "1"
                }
            },
            "signers": [
                {
                    "platformSign": True,
                    "signOrder": 1,
                    "signfields": [
                        {
                            "autoExecute": True,
                            "actorIndentityType": 2,
                            "fileId": file_id,
                            "posBean": {
                                "posPage": company_coordinate['page'],
                                "posX": company_coordinate['x'],
                                "posY": company_coordinate['y']
                            }
                        }
                    ]
                },
                {
                    "platformSign": False,
                    "sealType": "0",
                    "signerAccount": {
                        "signerAccountId": account_id
                    },
                    "signfields": [
                        {
                            "autoExecute": False,
                            "fileId": file_id,
                            "posBean": {
                                "posPage": user_coordinate['page'],
                                "posX": user_coordinate['x'],
                                "posY": user_coordinate['y']
                            }
                        }
                    ]
                }
            ]
        }
        ret = requests.post(url=cls.one_step_initiation_signature_api, data=json.dumps(params),
                            headers=cls.generate_header())
        data = json.loads(ret.text)
        flow_id = None
        if data['code'] == 0:
            ret_msg = '创建流程成功'
            flow_id = data['data']['flowId']
        else:
            if data['code'] == 401:
                cls.refresh_oauth2_token()
            ret_msg = "创建流程失败, 错误码: {}, 错误信息: {}".format(data['code'], data['message'])
        return data['code'], ret_msg, flow_id

    @classmethod
    def get_sign_url(cls, account_id, flow_id):
        """
        获取签署的链接
        """
        params = {
            "accountId": account_id
        }
        ret = requests.get(url=cls.get_signature_url_api.format(flowId=flow_id), params=params,
                           headers=cls.generate_header())
        data = json.loads(ret.text)
        sign_url = None
        if data['code'] == 0:
            ret_msg = '获取成功'
            sign_url = data['data']['shortUrl']
        else:
            if data['code'] == 401:
                cls.refresh_oauth2_token()
            ret_msg = "获取失败, 错误码: {}, 错误信息: {}".format(data['code'], data['message'])
        return data['code'], ret_msg, sign_url

    @classmethod
    def pdf_verify(cls, file_id, flow_id):
        """
        签署完成后的PDF验签
        """
        params = {
            "flowId": flow_id
        }
        ret = requests.get(url=cls.PDF_verify_api.format(fileId=file_id), params=params, headers=cls.generate_header())
        data = json.loads(ret.text)
        if data['code'] == 0:
            ret_msg = '验签成功'
        else:
            if data['code'] == 401:
                cls.refresh_oauth2_token()
            ret_msg = "验签失败, 错误码: {}, 错误信息: {}".format(data['code'], data['message'])
        return data['code'], ret_msg

    @classmethod
    def revoke_signature_flow(cls, flow_id, revoke_reason='撤销'):
        """
        撤销签署
        """
        params = {
            "revokeReason": revoke_reason
        }
        ret = requests.put(url=cls.revoke_signature_flow_api.format(flowId=flow_id), data=json.dumps(params),
                           headers=cls.generate_header())
        data = json.loads(ret.text)
        if data['code'] == 0:
            ret_msg = '撤销签署流程成功'
        else:
            if data['code'] == 401:
                cls.refresh_oauth2_token()
            ret_msg = "撤销签署流程失败, 错误码: {}, 错误信息: {}".format(data['code'], data['message'])
        return data['code'], ret_msg

    @classmethod
    def sign_flow_query(cls, flow_id):
        """
        合同的签署流程状态查询
        """
        ret = requests.get(url=cls.sign_flow_query_api.format(flowId=flow_id), headers=cls.generate_header())
        data = json.loads(ret.text)
        if data['code'] == 0:
            ret_msg = '获取成功'
        else:
            if data['code'] == 401:
                cls.refresh_oauth2_token()
            ret_msg = "获取失败, 错误码: {}, 错误信息: {}".format(data['code'], data['message'])
        return data['code'], ret_msg, data['data']

    @classmethod
    def download_contract_documents(cls, flow_id):
        """
        下载签署成功的合同文件
        """
        ret = requests.get(url=cls.download_contract_documents_api.format(flowId=flow_id),
                           headers=cls.generate_header())
        data = json.loads(ret.text)
        file_url = None
        if data['code'] == 0:
            ret_msg = '获取成功'
            file_url = data['data']['docs'][0]['fileUrl']
        else:
            if data['code'] == 401:
                cls.refresh_oauth2_token()
            ret_msg = "获取失败, 错误码: {}, 错误信息: {}".format(data['code'], data['message'])
        return data['code'], ret_msg, file_url

    @classmethod
    def get_personage_real_name_authentication_url(cls, account_id, name, id_card_number, mobile):
        params = {
            "authType": "PSN_TELECOM_AUTHCODE",
            "availableAuthTypes": ["PSN_TELECOM_AUTHCODE", "PSN_BANK4_AUTHCODE", "PSN_FACEAUTH_BYURL"],
            "authAdvancedEnabled": [],
            "receiveUrlMobileNo": mobile,
            "contextInfo": {
                # "contextId": "57cc9602-d1b6-48bd-bdbb-61e9f8443955",
                "notifyUrl": "",
                "origin": "BROWSER",
                "redirectUrl": "",
                "showResultPage": True
            },
            "indivInfo": {
                "name": name,
                "certType": "INDIVIDUAL_CH_IDCARD",
                "certNo": id_card_number,
                "mobileNo": mobile,
                # "bankCardNo": ""
            },
            "configParams": {
                "indivUneditableInfo": ["name", "certNo", "mobileNo", "bankCardNo"]
            },
            "repeatIdentity": True
        }
        ret = requests.post(url=cls.personage_real_name_authentication_api.format(accountId=account_id),
                            data=json.dumps(params), headers=cls.generate_header())
        data = json.loads(ret.text)
        short_link = None
        if data['code'] == 0:
            ret_msg = '获取认证链接成功'
            short_link = data['data']['shortLink']
        else:
            if data['code'] == 401:
                cls.refresh_oauth2_token()
            ret_msg = "获取失败, 错误码: {}, 错误信息: {}".format(data['code'], data['message'])
        return data['code'], ret_msg, short_link
