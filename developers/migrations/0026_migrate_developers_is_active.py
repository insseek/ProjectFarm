# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import migrations


def migrate_developers_is_active(apps, schema_editor):
    Developer = apps.get_model("developers", "Developer")
    Developer.objects.filter(status='0').update(is_active=False)


class Migration(migrations.Migration):
    dependencies = [
        ('developers', '0025_auto_20191105_0157'),
    ]
    operations = [
        migrations.RunPython(migrate_developers_is_active, migrations.RunPython.noop),
    ]
