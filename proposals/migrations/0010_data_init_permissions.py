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

    app_config = apps.get_app_config('proposals')
    app_config.models_module = app_config.models_module or True
    create_permissions(app_config, verbosity=0)

    Proposal = apps.get_model("proposals", "Proposal")
    content_type = ContentType.objects.get_for_model(Proposal)
    proposal_permissions = Permission.objects.filter(content_type=content_type)

    try:
        permission = proposal_permissions.get(codename='view_playbook')
        pm_group.permissions.add(permission)
        permission = proposal_permissions.get(codename='view_calculator')
        pm_group.permissions.add(permission)
        permission = proposal_permissions.get(codename='view_created_in_90_days')
        pm_group.permissions.add(permission)
        permission = proposal_permissions.get(codename='view_created_in_30_days')
        marketing_group.permissions.add(permission)
    except ObjectDoesNotExist:
        pass

class Migration(migrations.Migration):
    dependencies = [
        ('proposals', '0009_auto_20170808_2029'),
    ]
    operations = [
        migrations.RunPython(init_permissions, migrations.RunPython.noop),
    ]
