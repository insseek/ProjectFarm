# -*- coding: utf-8 -*-
from django.db import migrations

def migrate_logs_created_date(apps, schema_editor):
    Log = apps.get_model("logs", "Log")

    for log in Log.objects.all():
        log.created_date = log.created_at
        log.save()

class Migration(migrations.Migration):
    dependencies = [
        ('logs', '0013_log_created_date'),
    ]

    operations = [
        migrations.RunPython(migrate_logs_created_date, migrations.RunPython.noop),
    ]
