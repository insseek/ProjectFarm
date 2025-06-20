# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import migrations
from farmbase.permissions_init import init_func_perms


def set_func_perms(apps, schema_editor):
    init_func_perms()


class Migration(migrations.Migration):
    dependencies = [
        ('farmbase', '0015_profile_avatar_color'),
    ]

    operations = [
        migrations.RunPython(set_func_perms, migrations.RunPython.noop),
    ]
