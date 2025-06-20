# -*- coding:utf-8 -*-

# 本地开发 本地文件存储: DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
# 线上 AWS S3 文件存储：DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
# AWS S3的文件存储配置
AWS_ACCESS_KEY_ID = "xxx"
AWS_SECRET_ACCESS_KEY = "xxx"
AWS_STORAGE_BUCKET_NAME = "farm"
AWS_S3_REGION_NAME = 'cn-north-1'
AWS_DEFAULT_ACL = None
AWS_BUCKET_ACL = None

# 邮件后端配置
DEFAULT_FROM_EMAIL = 'serverlogger@chilunyc.com'
SERVER_EMAIL = 'serverlogger@chilunyc.com'  # 发送服务报错信息
EMAIL_HOST = 'smtp.exmail.qq.com'
EMAIL_HOST_USER = 'serverlogger@chilunyc.com'
EMAIL_HOST_PASSWORD = 'xxx'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
# 给客户发送邮件使用的账户密码
CLIENT_CONTACT_EMAIL_HOST_USER = ''
CLIENT_CONTACT_EMAIL_HOST_PASSWORD = ''

# quip 爬取 客户/需求、客户/项目、项目文件夹标准模版、项目工程师沟通文件夹、远程工程师须知文档
# 获取token的地址https://quip.com/dev/automation/documentation#authentication-personal
QUIP_TOKEN = ''
QUIP_PROPOSAL_FOLDER_ID = ''  # 所有需求目录
QUIP_PROJECT_FOLDER_ID = ''  # 所有项目目录
QUIP_PROJECT_FOLDER_TEMPLATE_ID = ''  # 项目目录模版
QUIP_PROJECT_ENGINEER_FOLDER_ID = ''  # 所有项目工程师沟通目录
QUIP_DEVELOPER_DOCUMENTS_FOLDER_ID = ''  # 工程师须知文档目录

# 微信分享
WECHAT_APPID = ''
WECHAT_SECRET = ''

# Gitlab爬取数据、Gitlab第三方登录
GITLAB_ADMIN_PRIVATE_TOKEN = ''
GITLAB_FARM_CLIENT_ID = ''
GITLAB_FARM_CLIENT_SECRET = ''

# 飞书消息推送
FEISHU_FARM_APP_ID = ''
FEISHU_FARM_APP_SECRET = ''
FEISHU_ALL_CHAT_ID = ''

# 阿里云短信
ALIYUN_ACCESS_KEY_ID = ''
ALIYUN_ACCESS_KEY_SECRET = ''
# 阿里云 实名认证校验 https://market.aliyun.com/products/57000002/cmapi00037883.html#sku=yuncode31883000010
ALIYUN_REAL_NAME_APPCODE = ''

# 项目原型OSS存储配置
PROTOTYPE_OSS_BUCKET = ""
PROTOTYPE_OSS_REGION = "oss-cn-beijing"
PROTOTYPE_OSS_ENDPOINT = 'http://oss-cn-beijing.aliyuncs.com'
PROTOTYPE_OSS_ACCESS_KEY_ID = ""
PROTOTYPE_OSS_ACCESS_KEY_SECRET = ""
# 原型OSS结束

# E签宝 合同签约
E_SIGN_APP_ID = ''
E_SIGN_APP_SECRET = ''
E_SIGN_DOMAIN = ''
E_SIGN_NOTICE_URL = ''

# 根据自己系统下载后，配置一下路径 下载地址http://phantomjs.org/download.html
# 后台Headless,无界面浏览器 进行报告截图
PHANTOMJS_PATH = ''
