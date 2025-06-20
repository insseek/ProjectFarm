# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.management import create_permissions
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import migrations


def permission_assignment(apps, schema_editor):
    pm_group, created = Group.objects.get_or_create(name='产品经理')
    intern_pm_group, created = Group.objects.get_or_create(name='培训产品经理')

    app_config = apps.get_app_config('reports')
    app_config.models_module = app_config.models_module or True
    create_permissions(app_config, verbosity=0)

    Report = apps.get_model("reports", "Report")
    content_type = ContentType.objects.get_for_model(Report)
    report_permissions = Permission.objects.filter(content_type=content_type)

    try:
        permission = report_permissions.get(codename='gear_view_all_reports')
        pm_group.permissions.add(permission)
        intern_pm_group.permissions.add(permission)
    except ObjectDoesNotExist:
        pass


class Migration(migrations.Migration):
    dependencies = [
        ('reports', '0008_auto_20171227_0005'),
    ]
    operations = [
        migrations.RunPython(permission_assignment, migrations.RunPython.noop),
    ]
