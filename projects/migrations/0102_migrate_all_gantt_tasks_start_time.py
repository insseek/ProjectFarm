from __future__ import unicode_literals

from datetime import timedelta

from django.db import migrations


def migrate_all_gantt_topics_start_time(apps, schema_editor):
    GanttTaskTopic = apps.get_model("projects", "GanttTaskTopic")
    gantt_topics = GanttTaskTopic.objects.all()
    for task in gantt_topics:
        if task.only_workday and task.start_time.weekday() >= 5:
            if task.start_time.weekday() == 6:
                task.start_time = task.start_time + timedelta(days=1)
            elif task.start_time.weekday() == 5:
                task.start_time = task.start_time + timedelta(days=2)
            task.save()


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0101_ganttrole_role_type'),
    ]

    operations = [
        migrations.RunPython(migrate_all_gantt_topics_start_time, migrations.RunPython.noop),
    ]
