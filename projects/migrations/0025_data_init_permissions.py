# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.management import create_permissions
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import migrations


def init_permissions(apps, schema_editor):
    pm_group, created = Group.objects.get_or_create(name='产品经理')
    marketing_group, created = Group.objects.get_or_create(name='市场')

    app_config = apps.get_app_config('projects')
    app_config.models_module = app_config.models_module or True
    create_permissions(app_config, verbosity=0)

    Project = apps.get_model("projects", "Project")
    content_type = ContentType.objects.get_for_model(Project)
    project_permissions = Permission.objects.filter(content_type=content_type)

    try:
        permission = project_permissions.get(codename='view_playbook')
        pm_group.permissions.add(permission)
        permission = project_permissions.get(codename='view_job_positions')
        pm_group.permissions.add(permission)
        permission = project_permissions.get(codename='view_all_projects')
        pm_group.permissions.add(permission)
        permission = project_permissions.get(codename='view_project_finished_in_60_days')
        marketing_group.permissions.add(permission)
    except ObjectDoesNotExist:
        pass

class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0024_auto_20170802_1515'),
    ]
    operations = [
        migrations.RunPython(init_permissions, migrations.RunPython.noop),
    ]
