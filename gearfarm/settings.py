import os
from gearfarm.secret import *

STAGING = PRODUCTION = DEVELOPMENT = False

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '45cbcef9-2bbc-4e67-ad91-79f3fda0d6e5'

ALLOWED_HOSTS = ['www.chilunyc.com', 'chilunyc.com', 'staging.chilunyc.com', 'farm.chilunyc.com',
                 'farm.staging.chilunyc.com', 'developer.chilunyc.com', 'staging.developer.chilunyc.com',
                 'localhost', '127.0.0.1', '0.0.0.0']

# Django debug tool using ips
# INTERNAL_IPS = ["127.0.0.1"]
# Django debug tool JQuery url
JQUERY_URL = '//cdn.bootcss.com/jquery/3.2.1/jquery.js'

# Application definition

INSTALLED_APPS = [
    'django.contrib.admindocs',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'bootstrap3_datepicker',
    'taggit',
    'debug_toolbar',
    'farmbase',
    'projects',
    'developers',
    'clients',
    'comments',
    'crispy_forms',
    'proposals',
    'tasks',
    'logs',
    'playbook',
    'reports',
    'files',
    'storages',
    'compressor',
    'finance',
    'notifications',
    'djcelery',
    'gearmail',
    'corsheaders',
    'webphone',
    'workorder',
    'prototypes',
    'geargitlab',
    'sass_processor',
    'easy_thumbnails',
    'multiselectfield',
    'oauth',
    'auth_top',
    'testing',
    'django_filters',
    'exports',
    'channels',
    # 'silk',
]

MIDDLEWARE = [
    # 'silk.middleware.SilkyMiddleware',
    'crum.CurrentRequestUserMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'gearfarm.utils.csrf_exempt_middleware.CsrfExemptMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'gearfarm.utils.login_required_middleware.RequireLoginMiddleware',
]

CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_CREDENTIALS = True
CORS_ORIGIN_WHITELIST = ()
CORS_URLS_REGEX = r'^/\w*api/.*$'

from corsheaders.defaults import default_headers

CORS_ALLOW_HEADERS = list(default_headers) + [
    'withcredentials'
]

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

ROOT_URLCONF = 'gearfarm.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, "static"),
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    # other finders..
    'compressor.finders.CompressorFinder',
)

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M',
    'DATE_FORMAT': '%Y-%m-%d',
    'TIME_FORMAT': '%H:%M',
}

# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# LOGGING
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '[%(asctime)s] [%(levelname)s] %(module)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
    },
    'handlers': {
        'mail': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'formatter': 'simple',
        },
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
}

# 缩略图
THUMBNAIL_ALIASES = {
    '': {
        'small': {'size': (0, 160)},
        'middle': {'size': (0, 260)},
        'large': {'size': (0, 400)},
    },
}

THUMBNAIL_DEFAULT_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

LANGUAGE_CODE = 'zh-Hans'

TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_L10N = True

USE_TZ = False

STATIC_URL = '/static/'
MEDIA_URL = "/media/"

LOGIN_URL = '/admin/login/'
LOGIN_REDIRECT_URL = '/admin/'

WSGI_APPLICATION = 'gearfarm.wsgi.application'

CRISPY_TEMPLATE_PACK = 'bootstrap3'

TAGGIT_CASE_INSENSITIVE = True

ADMINS = [('Fanping', 'fanping@chilunyc.com'), ('Shoudong', 'shoudong@chilunyc.com')]
MANAGERS = ADMINS

DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

QUIPFILE_URL = MEDIA_URL + "quipfiles/"
PROJECT_DOCUMENTS_URL = MEDIA_URL + "projects/"
PROTOTYPE_URL = MEDIA_URL + "prototypes/"
DATETIME_FORMAT = '%Y-%m-%d %H:%M'
DATETIME_WITH_SECOND_FORMAT = '%Y-%m-%d %H:%M:%S'
DATE_FORMAT = '%Y-%m-%d'
TIME_FORMAT = '%H:%M'
SAMPLE_DATETIME_FORMAT = '%Y.%m.%d %H:%M'
SAMPLE_DATE_FORMAT = '%Y.%m.%d'

# 登录验证URLS
LOGIN_REQUIRED_API_PREFIX = '/api/'
LOGIN_REQUIRED_URLS_EXCEPTIONS = (
    r'/admin/(.*)$',
    r'/static/(.*)$',
    r'/media/(.*)$',

    # 报告脑图
    r'/reports/mindmap/view/(.*)$',
    # 报告详情
    r'/reports/([A-Za-z0-9]{18,})/?$',
)
LOGIN_REQUIRED_API_EXCEPTIONS = (
    r'/api/logs/browsing_histories$',
    r'/api/logs/browsing_histories/(.*)$',
    r'/api/projects/prototypes/(\w+)/perm$',
    r'/api/projects/prototypes/(\w+)/access_token$',
    r'/api/projects/prototypes/(\w+)/access$',
    r'/api/projects/prototypes/(\w+)/content_type',
    r'/api/projects/delivery_document_zips/(\w+)/download',
    r'/api/projects/delivery_documents/(\w+)/download',
    r'/api/users/token$',
    r'/api/users/token/check$',
    r'/api/users/login$',
    r'/api/users/phone/code$',
    r'/api/users/phone/login$',
    r'/api/finance/jobs/contracts/(\w+)/preview$',
    r'/api/finance/jobs/contracts/(\w+)/confidentiality_agreement_preview$',

    r'/api/users/dd_auth/(.*)$',
    r'/api/webphone/call_status_notice$',
    r'/api/projects/prototypes/(\w+)/perm$',

    r'/api/webphone/call_fee_notice$',
    r'/api/ganttcharts/(\w+)/tasks$',
    r'/api/projects/(\w+)/stages_groups',
    r'/api/ganttcharts/(\w+)$',
    r'/api/projects/calendar/(\w+)$',

    r'/api/reports/(\w+)/evaluations',

    r'/api/oauth/gitlab/login/redirect/data$',
    r'/api/oauth/gitlab/login$',

    r'/api/oauth/feishu/login/redirect/data$',
    r'/api/oauth/feishu/login$',

    r'/api/oauth/wechat/sign_data$',

    r'/api/v1/auth_top/sso/phone/code$',
    r'/api/v1/auth_top/sso/phone/login/code$',
    r'/api/v1/auth_top/sso/phone/login/user_types',
    r'/api/v1/auth_top/sso/phone/login$',

    r'/api/v1/auth_top/sso/gitlab/login/oauth_uri$',
    r'/api/v1/auth_top/sso/gitlab/login$',
    r'/api/v1/auth_top/sso/gitlab/login/user_types$',
    r'/api/v1/auth_top/sso/feishu/login/oauth_uri$',
    r'/api/v1/auth_top/sso/feishu/login$',
    r'/api/v1/auth_top/sso/feishu/login/user_types$',

    r'/api/v1/auth_top/sso/ticket/login$',
    r'/api/v1/auth_top/sso/app/data$',

    r'/api/users/func_perms/init_data',  # 获取功能权限列表  只有权限 没有权限分配数据/有权限分配数据
    r'/api/finance/jobs/contracts/call_back'  # E签宝回调接口
)

ONE_TIME_AUTH_OPEN_API_POST_EXCEPTIONS = (
    r'/open_api/v1/developer/login/one_time/authentication$',
    r'/open_api/v1/client/login/one_time/authentication$',
)

LOGIN_REQUIRED_OPEN_API_EXCEPTIONS = (
    r'/open_api/v1/developer/login$',
    r'/open_api/v1/developer/login/one_time/authentication$',
    r'/open_api/v1/developer/phone/code$',

    r'/open_api/v1/developer/oauth/gitlab/login/redirect/data$',
    r'/open_api/v1/developer/oauth/gitlab/login$',
    r'/open_api/v1/developer/gitlab/personal/info$',

    r'/open_api/v1/notifications/(.*)$',

    r'/open_api/v1/projects/deploy/status$',

    r'/open_api/v1/users/gitlab/personal$',
    r'/open_api/v1/users/gitlab/dict$',
    r'/open_api/v1/users/login$',

    r'/open_api/v1/client/phone/login$',
    r'/open_api/v1/client/phone/code',
    r'/open_api/v1/client/login/one_time/authentication$',
    r'/open_api/v1/client/projects/delivery_documents/(\w+)/download'
)

ONE_TIME_AUTH_PREFIX = 'one_time'
IMPERSONATOR_AUTH_PREFIX = 'x_impersonator'

# CSRF_EXEMPT_URLS = (
#     r'/api/users/token$',
#     r'/api/users/token/check$',
#     r'/api/users/login$',
#     r'/api/users/dd_auth/login$',
#     r'/api/users/logout$',
#     r'/api/files/(.*)$',
#     r'/open_api/v1/(.*)$',
#     r'/api/oauth/(.*)$',
# )

INIT_PHASES = ['PRD', '设计', '开发', '测试']
GROUP_NAME_DICT = {
    "project_manager": "项目经理",
    "pm": '产品经理',
    "remote_tpm": '远程TPM',
    "learning_pm": '培训产品经理',
    "tpm": 'TPM',
    "finance": '财务',
    "test": '测试',
    "bd": "BD",
    "designer": "设计",
    "marketing": "市场",
    "sem": 'SEM'
}

# 邮件
DEFAULT_FROM_EMAIL = ''
SERVER_EMAIL = ''
EMAIL_HOST = 'smtp.exmail.qq.com'
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_PORT = 587
EMAIL_USE_TLS = True
CLIENT_CONTACT_EMAIL_HOST_USER = ''
CLIENT_CONTACT_EMAIL_HOST_PASSWORD = ''

# 编译
SASS_PRECISION = 8
SASS_OUTPUT_STYLE = 'compact'
SASS_PROCESSOR_AUTO_INCLUDE = True
SASS_PROCESSOR_INCLUDE_FILE_PATTERN = r'^.+\.scss$'
SASS_PROCESSOR_ROOT = ''
COMPRESS_ROOT = ''
# react js编译压缩后输出路径
JS_BUILD_OUTPUT_PATH = STATIC_URL + "farm_output"
COMPRESS_OFFLINE_CONTEXT = {
    'js_build_output_path': STATIC_URL + "farm_output",
}

# gitlab
GITLAB_ADMIN_PRIVATE_TOKEN = ''

GITLAB_FARM_CLIENT_ID = ''
GITLAB_FARM_CLIENT_SECRET = ''

# 飞书
FEISHU_FARM_APP_ID = ''
FEISHU_FARM_APP_SECRET = ''
FEISHU_ALL_CHAT_ID = ''

# 阿里云
ALIYUN_ACCESS_KEY_ID = ''
ALIYUN_ACCESS_KEY_SECRET = ''
ALIYUN_REAL_NAME_APPCODE = ''

# E签宝
E_SIGN_APP_ID = ''
E_SIGN_APP_SECRET = ''
E_SIGN_DOMAIN = ''
E_SIGN_NOTICE_URL = ''

# quip
QUIP_TOKEN = ''
QUIP_PROPOSAL_FOLDER_ID = ''
QUIP_PROJECT_FOLDER_ID = ''
QUIP_PROJECT_FOLDER_TEMPLATE_ID = ''
QUIP_PROJECT_ENGINEER_FOLDER_ID = ''
QUIP_DEVELOPER_DOCUMENTS_FOLDER_ID = ''

PHANTOMJS_PATH = ''

# 域名配置  与其他服务交互
SITE_URL = ""
DEVELOPER_WEB_SITE_URL = ''
CLIENT_WEB_SITE_URL = 'http://localhost:3001'
DOCUMENT_WEB_SITE_URL = ''
# 测试服务
GEAR_TEST_SITE_URL = ''
SSO_SITE_URL = ''
# 原型评审
GEAR_PROTOTYPE_SITE_URL = 'http://dev.prototype.chilunyc.com'

# X_FRAME_OPTIONS = 'ALLOWALL'

# 与业务相关的配置
PROJECT_MANAGER_PROJECT_CAPACITY = 8
PM_PROJECT_CAPACITY = 8
LEARNING_PM_PROJECT_CAPACITY = 4
TPM_PROJECT_CAPACITY = 8
TEST_PROJECT_CAPACITY = 6
DESIGNER_PROJECT_CAPACITY = 3
# 负责工程师需求的人
RESPONSIBLE_TPM_FOR_PROJECT_JOB_NEEDS = []
RESPONSIBLE_TPM_FOR_DEVOPS = []
# 法务 负责工程师合同的人
LEGAL_PERSONNEL = []
DEVELOPMENT_DD_CODE = '666888'

# 原型OSS开始
PROTOTYPE_OSS_BUCKET = "gear-prototypes-dev"
PROTOTYPE_OSS_REGION = "oss-cn-beijing"
PROTOTYPE_OSS_ENDPOINT = 'oss-cn-beijing.aliyuncs.com'
PROTOTYPE_OSS_ACCESS_KEY_ID = ""
PROTOTYPE_OSS_ACCESS_KEY_SECRET = ""

# 原型OSS结束

DESIGNER_PRINCIPAL = '翟西文'

from gearfarm.secret import *

# 【channels】（第3步）设置为指向路由对象作为根应用程序
ASGI_APPLICATION = "gearfarm.routing.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("localhost", 6379)],
        },
    },
}
