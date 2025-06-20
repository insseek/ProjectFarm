# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.management import create_permissions
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import migrations


def permission_assignment(apps, schema_editor):
    tmp_group, created = Group.objects.get_or_create(name='TPM')
    test_group, created = Group.objects.get_or_create(name='测试')
    csm_group, created = Group.objects.get_or_create(name='客户成功')
    pm_group, created = Group.objects.get_or_create(name='产品经理')

    app_config = apps.get_app_config('projects')
    app_config.models_module = app_config.models_module or True
    create_permissions(app_config, verbosity=0)

    Project = apps.get_model("projects", "Project")
    content_type = ContentType.objects.get_for_model(Project)
    project_permissions = Permission.objects.filter(content_type=content_type)

    try:
        permission = project_permissions.get(codename='gear_view_project_track_progress')
        tmp_group.permissions.add(permission)
        csm_group.permissions.add(permission)
        test_group.permissions.add(permission)
        pm_group.permissions.add(permission)
    except ObjectDoesNotExist:
        pass


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0036_auto_20180116_1136'),
    ]
    operations = [
        migrations.RunPython(permission_assignment, migrations.RunPython.noop),
    ]
