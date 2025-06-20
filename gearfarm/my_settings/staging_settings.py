from gearfarm.my_settings.production_settings import *

STAGING = True
PRODUCTION = False
DEVELOPMENT = False

AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend']
ADMINS = [('Fanping', 'fanping@chilunyc.com'), ('Shoudong', 'shoudong@chilunyc.com'), ('Shoudong', '470385810@qq.com')]

BROKER_URL = 'redis://localhost:6379/10'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/11'
CELERYBEAT_SCHEDULER = 'djcelery.schedulers.DatabaseScheduler'
CELERY_ENABLE_UTC = False

import djcelery

djcelery.setup_loader()
from celery.schedules import crontab

CELERYBEAT_SCHEDULE = {
    "定时任务: 每天4点从正式环境同步权限配置": {
        "task": "farmbase.tasks.sync_permissions_groups_from_production_env",
        "schedule": crontab(minute=0, hour=4),
        "args": (),
    },
}

RESPONSIBLE_TPM_FOR_PROJECT_JOB_NEEDS = ['鄢波']
# REPORTS HOST NAME
REPORTS_HOST = 'https://farm.staging.chilunyc.com'
PROJECT_DELIVERY_DOCUMENTS_HOST = 'https://farm.staging.chilunyc.com'

SITE_URL = 'https://farm.staging.chilunyc.com'
DEVELOPER_WEB_SITE_URL = "https://staging.developer.chilunyc.com"
CLIENT_WEB_SITE_URL = "https://staging.client.chilunyc.com"
DOCUMENT_WEB_SITE_URL = "https://staging.document.chilunyc.com"

SSO_SITE_URL = "https://sso.staging.chilunyc.com"
# 测试服务
GEAR_TEST_SITE_URL = 'https://test.staging.chilunyc.com'
# 原型评审
GEAR_PROTOTYPE_SITE_URL = 'http://staging.prototype.chilunyc.com'

PHANTOMJS_PATH = '/home/deployer/browser-driver/phantomjs-2.1.1-linux-x86_64/bin/phantomjs'

# 跳到前端登录
LOGIN_URL = '/login/ticket/'
