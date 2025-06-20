"""
ASGI入口点，运行Django，然后运行在settings.py ASGI_APPLICATION 中定义的应用程序
安装：pip install daphne
运行：daphne -p 8001 ITNest.asgi:application
"""

import os
import django
from channels.routing import get_default_application

import os

STAGING = PRODUCTION = DEVELOPMENT = False

if os.environ.get('PROD', 0):
    if os.environ.get('STAGING', 0):
        STAGING = True
    else:
        PRODUCTION = True
else:
    DEVELOPMENT = True

if PRODUCTION:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gearfarm.my_settings.production_settings")
if STAGING:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gearfarm.my_settings.staging_settings")
if DEVELOPMENT:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gearfarm.my_settings.development_settings")
django.setup()
application = get_default_application()