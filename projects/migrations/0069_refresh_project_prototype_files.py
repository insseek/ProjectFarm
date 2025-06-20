# -*- coding:utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def refresh_prototype_files(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0068_prototypecommentpoint'),
    ]

    operations = [
        migrations.RunPython(refresh_prototype_files, migrations.RunPython.noop),
    ]
