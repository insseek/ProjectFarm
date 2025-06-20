from __future__ import unicode_literals
from datetime import datetime, timedelta
from django.db import migrations


def migrate_projects_shedules(apps, schema_editor):
    Schedule = apps.get_model("projects", "Schedule")
    schedules = Schedule.objects.all()
    for schedule in schedules:
        if schedule.prd_confirmation_time:
            schedule.ui_start_time = schedule.prd_confirmation_time + timedelta(days=1)
        if schedule.dev_completion_time:
            schedule.test_start_time = schedule.dev_completion_time + timedelta(days=1)
        if schedule.delivery_time:
            schedule.test_completion_time = schedule.delivery_time - timedelta(days=1)
        schedule.save()


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0126_auto_20191120_1810'),
    ]

    operations = [
        migrations.RunPython(migrate_projects_shedules, migrations.RunPython.noop),
    ]
