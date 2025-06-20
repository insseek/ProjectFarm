# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import migrations


def init_industry_classification_technology_type_data(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('reports', '0012_report_description'),
    ]
    operations = [
        migrations.RunPython(init_industry_classification_technology_type_data, migrations.RunPython.noop),
    ]
