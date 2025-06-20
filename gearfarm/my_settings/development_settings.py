import logging.config

from gearfarm.settings import *

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
ALLOWED_HOSTS = ['*']
COMPRESS_ENABLED = False
# run npm install -g yuglify first if you want to enable compress
COMPRESS_JS_FILTERS = ['compressor.filters.yuglify.YUglifyJSFilter']
COMPRESS_YUGLIFY_BINARY = 'node_modules/yuglify/bin/yuglify'

DEVELOPMENT = True
STAGING = False
PRODUCTION = False

# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://localhost:6379/3",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

LOGGING['loggers'] = {
    '': {
        'handlers': ['console'],
        'level': 'INFO',
        'propagate': True,
    },
}

AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend']

logging.config.dictConfig(LOGGING)

# STATIC_ROOT = BASE_DIR + '/static/'
MEDIA_ROOT = BASE_DIR + '/media/'
SASS_PROCESSOR_ENABLED = True
SASS_PROCESSOR_ROOT = BASE_DIR + '/.cache/static/'
COMPRESS_ROOT = BASE_DIR + '/.cache/static/'
# react js编译压缩后输出路径
JS_BUILD_OUTPUT_PATH = "http://localhost:8099"
# Using https or not
USE_HTTPS = False

BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/1'
CELERYBEAT_SCHEDULER = 'djcelery.schedulers.DatabaseScheduler'
CELERY_ENABLE_UTC = False

import djcelery

djcelery.setup_loader()
from celery.schedules import crontab

CELERYBEAT_SCHEDULE = {
    # "定时任务: 每半小时更新项目demo状态": {
    #     "task": "geargitlab.tasks.crawl_farm_projects_recent_half_hour_git_demo_commits",
    #     "schedule": crontab(minute='*/1'),
    #     "args": (),
    # },
}

PROTOTYPE_ROOT = MEDIA_ROOT + 'prototypes/'
QUIPFILE_ROOT = MEDIA_ROOT + "quipfiles/"
PROJECT_DOCUMENTS_ROOT = MEDIA_ROOT + "projects/"

# REPORTS HOST NAME
REPORTS_HOST = ''
PROJECT_DELIVERY_DOCUMENTS_HOST = ""

COMPRESS_PDF = False

RESPONSIBLE_TPM_FOR_PROJECT_JOB_NEEDS = ['李帆平']
RESPONSIBLE_TPM_FOR_DEVOPS = ['李帆平']

SITE_URL = 'http://127.0.0.1:8000'
DEVELOPER_WEB_SITE_URL = 'http://localhost:3001'
CLIENT_WEB_SITE_URL = 'http://localhost:3001'
DOCUMENT_WEB_SITE_URL = ""
# 测试服务
GEAR_TEST_SITE_URL = 'http://localhost:3000'
# 原型评审
GEAR_PROTOTYPE_SITE_URL = 'http://dev.prototype.chilunyc.com'
