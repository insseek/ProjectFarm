# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os

from django.contrib.contenttypes.models import ContentType
from django.db import migrations

from reports import gear_to_farm


def from_gearhome_to_farm(apps, schema_editor):
    if os.environ.get('PROD',0):
        gear_to_farm.import_from_gear()

class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0002_auto_20170727_1237'),
    ]

    operations = [
        migrations.RunPython(from_gearhome_to_farm, migrations.RunPython.noop),
    ]
