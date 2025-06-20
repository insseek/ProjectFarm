# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.management import create_permissions
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import migrations


def init_permissions(apps, schema_editor):
    finance_group, created = Group.objects.get_or_create(name='财务')
    JobPayment = apps.get_model("finance", "JobPayment")

    app_config = apps.get_app_config('finance')
    app_config.models_module = app_config.models_module or True
    create_permissions(app_config, verbosity=0)

    content_type = ContentType.objects.get_for_model(JobPayment)
    job_payment_permissions = Permission.objects.filter(content_type=content_type)

    try:
        permission = job_payment_permissions.get(codename='view_all_payments')
        finance_group.permissions.add(permission)
    except ObjectDoesNotExist:
        pass


class Migration(migrations.Migration):
    dependencies = [
        ('finance', '0002_auto_20171019_1203'),
    ]
    operations = [
        migrations.RunPython(init_permissions, migrations.RunPython.noop),
    ]
