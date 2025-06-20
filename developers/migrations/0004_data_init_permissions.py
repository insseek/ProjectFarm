# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.management import create_permissions
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import migrations


def init_permissions(apps, schema_editor):
    pm_group, created = Group.objects.get_or_create(name='pm')
    Developer = apps.get_model("developers", "Developer")

    app_config = apps.get_app_config('developers')
    app_config.models_module = app_config.models_module or True
    create_permissions(app_config, verbosity=0)

    content_type = ContentType.objects.get_for_model(Developer)
    developer_permissions = Permission.objects.filter(content_type=content_type)
    try:
        permission = developer_permissions.get(codename='view_all_developers')
        pm_group.permissions.add(permission)
    except ObjectDoesNotExist:
        pass
     

class Migration(migrations.Migration):
    dependencies = [
        ('developers', '0003_auto_20170808_1551'),
    ]
    operations = [
        migrations.RunPython(init_permissions, migrations.RunPython.noop),
    ]
