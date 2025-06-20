import time
import random
import string
import hashlib
from wechat_sdk import WechatConf

from django.conf import settings


class Sign:
    def __init__(self, jsapi_ticket, url):
        self.ret = {
            'nonceStr': self.__create_nonce_str(),
            'jsapi_ticket': jsapi_ticket,
            'timestamp': self.__create_timestamp(),
            'url': url
        }

    def __create_nonce_str(self):
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(15))

    def __create_timestamp(self):
        return int(time.time())

    def sign(self):
        sign_string = '&'.join(['%s=%s' % (key.lower(), self.ret[key]) for key in sorted(self.ret)])
        encoded = sign_string.encode('utf-8')
        self.ret['signature'] = hashlib.sha1(encoded).hexdigest()
        return self.ret


def get_config(url, appid=None, appsecret=None):
    conf = WechatConf(
        # token='your_token',
        appid=appid or settings.WECHAT_APPID,
        appsecret=appsecret or settings.WECHAT_SECRET,
        # encrypt_mode='safe',  # 可选项：normal/compatible/safe，分别对应于 明文/兼容/安全 模式
        # encoding_aes_key='your_encoding_aes_key'  # 如果传入此值则必须保证同时传入 token, appid
    )
    ticket_dict = conf.get_jsapi_ticket()
    # ticket_dict =  json.loads(ticketJson)
    ticket = ticket_dict['jsapi_ticket']
    return Sign(ticket, url).sign()


def get_default_sign_data(url):
    appid = settings.WECHAT_APPID
    appsecret = settings.WECHAT_SECRET,
    ret = get_config(url, appid=appid, appsecret=appsecret)
    signature = ret['signature']
    ts = ret['timestamp']
    nonce_str = ret['nonceStr']
    data = {'appId': appid, 'signature': signature, 'timestamp': ts, 'nonceStr': nonce_str}
    return data
