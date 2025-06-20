from __future__ import absolute_import, unicode_literals
from datetime import datetime

from django.conf import settings
from celery import Celery

app = Celery('gearfarm')
app.now = datetime.now
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)