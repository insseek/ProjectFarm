# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import migrations


def migration_report_published_at(apps, schema_editor):
    Report = apps.get_model("reports", "Report")
    reports = Report.objects.exclude(creation_source='farm')

    for report in reports:
        if report.is_public and not report.published_at:
            report.published_at = report.created_at
            report.save()


class Migration(migrations.Migration):
    dependencies = [
        ('reports', '0025_report_main_content_text'),
    ]
    operations = [
        migrations.RunPython(migration_report_published_at, migrations.RunPython.noop),
    ]
