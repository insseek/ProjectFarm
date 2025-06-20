import logging.config

from gearfarm.settings import *

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DEVELOPMENT = False
STAGING = False
PRODUCTION = True

DEBUG = False

COMPRESS_ENABLED = True
COMPRESS_OFFLINE = True
# if you wanto enable compress, run "npm install babel-cli babel-preset-env" first
COMPRESS_PRECOMPILERS = (
    ('text/babel', 'cat {infile} | $NODE_PATH/node_modules/.bin/babel --presets react > {outfile}'),
)

USE_HTTPS = True

# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'farm',  # Or path to database file if using sqlite3.
        # The following settings are not used with sqlite3:
        'USER': 'postgres',
        'PASSWORD': 'geargear',
        'HOST': '127.0.0.1',
        # Empty for localhost through domain sockets or           '127.0.0.1' for localhost through TCP.
        'PORT': '',
    }
}

LOGGING['handlers']['file'] = {
    'level': 'INFO',
    'class': 'logging.handlers.RotatingFileHandler',
    'filename': '/home/deployer/farm/sys_logs/info.log',
    'maxBytes': 1024 * 1024 * 5,
    'backupCount': 5,
    'mode': 'a',
    'formatter': 'simple',
}
LOGGING['loggers'] = {
    '': {
        'handlers': ['file', 'mail', 'console'],
        'level': 'INFO',
        'propagate': True,
    },
}

logging.config.dictConfig(LOGGING)

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": 'redis://localhost:6379/9',
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

STATIC_ROOT = '/home/deployer/farm/static/'
MEDIA_ROOT = "/home/deployer/farm/media/"
SASS_PROCESSOR_ROOT = STATIC_ROOT
COMPRESS_ROOT = STATIC_ROOT

BROKER_URL = 'redis://localhost:6379/10'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/11'
CELERYBEAT_SCHEDULER = 'djcelery.schedulers.DatabaseScheduler'
CELERY_ENABLE_UTC = False

import djcelery
from datetime import timedelta

djcelery.setup_loader()
from celery.schedules import crontab

CELERYBEAT_SCHEDULE = {
    "定时任务: 每天早上7点更新工程师接单状态": {
        "task": "farmbase.tasks.change_developer_status",
        "schedule": crontab(minute=0, hour=7),
        "args": (),
    },
    "定时任务: 每天早上7点更新工程师缓存数据": {
        "task": "developers.tasks.update_active_developers_cache_data",
        "schedule": crontab(minute=20, hour=7),
        "args": (),
    },
    "定时任务: 每天下午5点发送处理未完成任务提醒给个人": {
        "task": "farmbase.tasks.send_task_reminder_to_individual",
        "schedule": crontab(minute=0, hour=17),
        "args": (),
    },
    "定时任务: 工作日每天下午7点发送Farm当日未完成任务统计数据给所有人": {
        "task": "farmbase.tasks.send_task_reminder_to_all",
        "schedule": crontab(minute=0, hour=19, day_of_week='mon-fri'),
        "args": (),
    },
    "定时任务: 每天下午8点发送工程师日报": {
        "task": "developers.tasks.send_project_developer_daily_works_to_manager_and_tpm",
        "schedule": crontab(minute=0, hour=20),
        "args": (),
    },
    "定时任务: 每天下午7点发送写日报提醒": {
        "task": "developers.tasks.send_project_developer_daily_works_to_developers",
        "schedule": crontab(minute=0, hour=19),
        "args": (),
    },
    "定时任务: 每天下午10点发送写日报提醒": {
        "task": "developers.tasks.send_project_developer_daily_works_to_developers",
        "schedule": crontab(minute=0, hour=22),
        "args": (),
    },
    "定时任务: 每天下午7点发送项目未关闭bug通知给项目经理/测试": {
        "task": "testing.tasks.send_project_undone_bugs_notification_to_manager_and_test",
        "schedule": crontab(minute=0, hour=19),
        "args": (),
    },
    "定时任务: 每天上午10点发送项目未关闭bug个负责人": {
        "task": "testing.tasks.send_project_undone_bugs_notification_to_assignee",
        "schedule": crontab(minute=0, hour=10),
        "args": (),
    },
    "定时任务: 每天凌晨2点清理无效的项目标签": {
        "task": "testing.tasks.clear_invalid_project_tags",
        "schedule": crontab(minute=0, hour=2),
        "args": (),
    },
    "定时任务: 每周四下午7点30分创建给客户发进度报告的任务": {
        "task": "farmbase.tasks.create_friday_tasks",
        "schedule": crontab(minute=30, hour=19, day_of_week='thu'),
        "args": (),
    },
    "定时任务: 每一小时更新需求Quip文件夹数据": {
        "task": "farmbase.tasks.crawl_quip_proposals_folders",
        "schedule": crontab(minute=0, hour='*/1'),
        "args": (),
    },
    "定时任务: 每一小时更新项目Quip文件夹数据": {
        "task": "farmbase.tasks.crawl_quip_projects_folders",
        "schedule": crontab(minute=0, hour='*/1'),
        "args": (),
    },
    "定时任务: 每一小时更新项目Quip工程师文件夹数据": {
        "task": "farmbase.tasks.crawl_quip_projects_engineer_folders",
        "schedule": crontab(minute=0, hour='*/1'),
        "args": (),
    },
    "定时任务: 每天凌晨0点10分爬取需求Quip电话需求文档": {
        "task": "farmbase.tasks.craw_ongoing_proposals_quip_contract_doc",
        "schedule": crontab(minute=10, hour=0),
        "args": (),
    },
    "定时任务: 每半天更新一次项目quip模版数据": {
        "task": "farmbase.tasks.rebuild_project_quip_folder_template",
        "schedule": crontab(minute=0, hour='*/12'),
        "args": (),
    },
    "定时任务: 每半天更新一次项目quip的TPM产出物": {
        "task": "farmbase.tasks.crawl_ongoing_projects_tpm_folder_docs",
        "schedule": crontab(minute=0, hour='*/12'),
        "args": (),
    },
    "定时任务: 每2小时更新工程师沟通文档": {
        "task": "farmbase.tasks.crawl_projects_engineer_folders_docs",
        "schedule": crontab(minute=0, hour='*/2'),
        "args": (),
    },
    "定时任务: 每半小时更新项目demo状态": {
        "task": "geargitlab.tasks.crawl_farm_projects_recent_half_hour_git_demo_commits",
        "schedule": crontab(minute='*/30'),
        "args": (),
    },
    "定时任务: 每天更新所有gitlab活跃用户": {
        "task": "geargitlab.tasks.crawl_all_gitlab_active_users",
        "schedule": crontab(minute=30, hour=4),
        "args": (),
    },
    "定时任务: 每三小时更新最近更新的gitlab项目": {
        "task": "geargitlab.tasks.crawl_recent_updated_gitlab_projects",
        "schedule": crontab(minute=0, hour='*/3'),
        "args": (),
    },
    "定时任务: 每7天更新进行中项目commit数据": {
        "task": "geargitlab.tasks.crawl_farm_projects_recent_days_git_commits",
        "schedule": crontab(minute=10, hour=3, day_of_week='sun'),
        "args": (),
    },
    "定时任务: 每一个小时更新Farm项目当天commit": {
        "task": "geargitlab.tasks.crawl_farm_projects_today_git_commits",
        "schedule": crontab(minute=0, hour='*/1'),
        "args": (),
    },

    "定时任务: 每一个小时更新进行中项目开发者近7天的gitlab commit数据": {
        "task": "dashboard.tasks.rebuild_ongoing_projects_developers_recent_seven_days_gitlab_commits_cache_data",
        "schedule": crontab(minute=0, hour='*/1'),
        "args": (),
    },

    "定时任务: 每一个小时更新进行中项目开发者今日打卡数据": {
        "task": "dashboard.tasks.rebuild_ongoing_projects_developers_today_daily_works_cache_data",
        "schedule": crontab(minute=0, hour='*/1'),
        "args": (),
    },

    "定时任务: 每天凌晨0点30分构建进行中项目工程师日报缺卡数据": {
        "task": "developers.tasks.build_yesterday_daily_work_absence_statistics",
        "schedule": crontab(minute=30, hour=0),
        "args": (),
    },
    "定时任务: 每天凌晨3点0分构建工程师昨天日报中commits数据": {
        "task": "developers.tasks.build_yesterday_daily_work_gitlab_commits",
        "schedule": crontab(minute=0, hour=3),
        "args": (),
    },
    "定时任务: 每天早上1点更新Farm项目昨天commits数据": {
        "task": "geargitlab.tasks.crawl_farm_projects_yesterday_git_commits",
        "schedule": crontab(minute=30, hour=1),
        "args": (),
    },
    "定时任务: 每天凌晨3点更新报告缓存数据": {
        "task": "reports.tasks.rebuild_all_proposal_lead_report_group_list_cache",
        "schedule": crontab(minute=0, hour=3),
        "args": (),
    },
    "定时任务: 每天凌晨4点更新原型评论点数据": {
        "task": "farmbase.tasks.clear_prototype_comment_points",
        "schedule": crontab(minute=0, hour=4),
        "args": (),
    },
    "定时任务: 每周六凌晨0点更新项目甘特图缓存数据": {
        "task": "farmbase.tasks.build_all_project_gantt_cache_data",
        "schedule": crontab(minute=0, hour=0, day_of_week='sat'),
        "args": (),
    },
    "定时任务: 每周日凌晨2点重置进行中项目playbook中每周任务": {
        "task": "farmbase.tasks.update_ongoing_project_playbook_weekly_task",
        "schedule": crontab(minute=0, hour=2, day_of_week='sun'),
        "args": (),
    },
    "定时任务: 每天凌晨2点半重置用例排序": {
        "task": "farmbase.tasks.rebuild_test_cases_index",
        "schedule": crontab(minute=30, hour=2),
        "args": (),
    },
    "定时任务: 每天凌晨1点构造自动任务": {
        "task": "tasks.tasks.build_auto_tasks",
        "schedule": crontab(minute=30, hour=3),
        "args": (),
    },
    "定时任务: 每天凌晨1点计算前一天BUG与项目用例的情况": {
        "task": "testing.tasks.build_yesterday_test_statistics",
        "schedule": crontab(minute=0, hour=1),
        "args": (),
    },
    "定时任务: 每月一日凌晨1点计算上个月BUG与项目用例的情况": {
        "task": "testing.tasks.build_last_month_test_statistics",
        "schedule": crontab(day_of_month=1, minute=0, hour=1),
        "args": (),
    },
    "定时任务: 每两个小时计算当天的测试数据": {
        "task": "testing.tasks.build_today_test_statistics",
        "schedule": crontab(minute=0, hour='*/2'),
        "args": (),
    },
    "定时任务: 每天晚上11点统计当天bug数": {
        "task": "testing.tasks.build_today_pending_bugs_statistics",
        "schedule": crontab(minute=0, hour=23),
        "args": (),
    },
    "定时任务: 每一小时查询更新合同签署状态": {
        "task": "finance.tasks.query_sign_result",
        "schedule": crontab(minute=0, hour='*/1'),
        "args": (),
    },

}
# 跳到前端登录
LOGIN_URL = '/login/ticket/'

PROTOTYPE_ROOT = MEDIA_ROOT + 'prototypes/'
QUIPFILE_ROOT = MEDIA_ROOT + "quipfiles/"
PROJECT_DOCUMENTS_ROOT = MEDIA_ROOT + "projects/"

REPORTS_HOST = 'https://chilunyc.com'
PROJECT_DELIVERY_DOCUMENTS_HOST = 'https://chilunyc.com'

COMPRESS_PDF = False

RESPONSIBLE_TPM_FOR_PROJECT_JOB_NEEDS = ['亓鹏飞']
# 运维人员
RESPONSIBLE_TPM_FOR_DEVOPS = ['冯超能']
# 法务 负责工程师合同的
LEGAL_PERSONNEL = ['刘雨佳']

SITE_URL = "https://farm.chilunyc.com"
DEVELOPER_WEB_SITE_URL = "https://developer.chilunyc.com"
CLIENT_WEB_SITE_URL = "https://client.chilunyc.com"
DOCUMENT_WEB_SITE_URL = "https://document.chilunyc.com"

SSO_SITE_URL = "https://sso.chilunyc.com"
# 测试服务
GEAR_TEST_SITE_URL = 'https://test.chilunyc.com'
# 原型评审
GEAR_PROTOTYPE_SITE_URL = 'http://prototype.chilunyc.com'

PHANTOMJS_PATH = '/home/deployer/browser-driver/phantomjs-2.1.1-linux-x86_64/bin/phantomjs'
