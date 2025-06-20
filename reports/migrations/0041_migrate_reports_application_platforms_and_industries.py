# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import migrations


def migrate_reports_application_platforms_and_industries(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('reports', '0040_remove_report_tags'),
        ('proposals', '0055_migrate_data_reports_tags'),
    ]
    operations = [
        migrations.RunPython(migrate_reports_application_platforms_and_industries, migrations.RunPython.noop),
    ]
