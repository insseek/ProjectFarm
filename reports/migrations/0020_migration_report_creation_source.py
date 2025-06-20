# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import migrations

def migration_report_creation_source(apps, schema_editor):
    Report = apps.get_model("reports", "Report")
    reports = Report.objects.all()
    for report in reports:
        if report.markdown != '':
            report.creation_source = 'markdown'
        elif report.html:
            report.creation_source = 'quip_link'
        else:
            continue
        report.save()


class Migration(migrations.Migration):
    dependencies = [
        ('reports', '0019_auto_20190505_1641'),
    ]
    operations = [
        migrations.RunPython(migration_report_creation_source, migrations.RunPython.noop),
    ]
