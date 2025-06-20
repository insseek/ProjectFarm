# -*- coding: utf-8 -*-
from django.db import migrations

def migrate_browsing_histories_created_date(apps, schema_editor):
    Log = apps.get_model("logs", "BrowsingHistory")

    for log in Log.objects.all():
        log.created_date = log.created_at
        log.save()

class Migration(migrations.Migration):
    dependencies = [
        ('logs', '0015_browsinghistory_created_date'),
    ]

    operations = [
        migrations.RunPython(migrate_browsing_histories_created_date, migrations.RunPython.noop),
    ]
