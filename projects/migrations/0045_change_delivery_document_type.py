# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def change_project_delivery_document_type(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0044_auto_20180201_1911'),
    ]
    operations = [
        migrations.RunPython(change_project_delivery_document_type, migrations.RunPython.noop),
    ]
