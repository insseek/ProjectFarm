# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import Group
from django.db import migrations

def create_group(apps, schema_editor):
    group, created = Group.objects.get_or_create(name='需求分配')

class Migration(migrations.Migration):
    dependencies = [
        ('proposals', '0010_data_init_permissions'),
    ]
    operations = [
        migrations.RunPython(create_group, migrations.RunPython.noop),
    ]
