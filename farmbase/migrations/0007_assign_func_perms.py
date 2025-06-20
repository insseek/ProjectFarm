# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from farmbase.permissions_init import init_func_perms


def assign_func_perms(apps, schema_editor):
    try:
        init_func_perms()
    except:
        pass


class Migration(migrations.Migration):
    dependencies = [
        ('farmbase', '0006_auto_20180511_2131'),
    ]

    operations = [
        migrations.RunPython(assign_func_perms, migrations.RunPython.noop),
    ]
