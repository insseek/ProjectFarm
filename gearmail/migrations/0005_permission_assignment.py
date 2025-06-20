# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.management import create_permissions
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import migrations


def permission_assignment(apps, schema_editor):

    pm_group, created = Group.objects.get_or_create(name='产品经理')
    tmp_group, created = Group.objects.get_or_create(name='TPM')
    csm_group, created = Group.objects.get_or_create(name='客户成功')

    EmailRecord = apps.get_model("gearmail", "EmailRecord")

    app_config = apps.get_app_config('gearmail')
    app_config.models_module = app_config.models_module or True
    create_permissions(app_config, verbosity=0)

    content_type = ContentType.objects.get_for_model(EmailRecord)
    email_record_permissions = Permission.objects.filter(content_type=content_type)

    try:
        permission = email_record_permissions.get(codename='gear_use_farm_send_email')
        pm_group.permissions.add(permission)
        tmp_group.permissions.add(permission)
        csm_group.permissions.add(permission)
    except ObjectDoesNotExist:
        pass


class Migration(migrations.Migration):
    dependencies = [
        ('gearmail', '0004_auto_20171227_0005'),
    ]
    operations = [
        migrations.RunPython(permission_assignment, migrations.RunPython.noop),
    ]
