# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import migrations


def migrate_developer_role_test(apps, schema_editor):
    Role = apps.get_model("developers", "Role")
    Role.objects.get_or_create(name="测试工程师")


class Migration(migrations.Migration):
    dependencies = [
        ('developers', '0044_developer_avatar_color'),
    ]
    operations = [
        migrations.RunPython(migrate_developer_role_test, migrations.RunPython.noop),
    ]
