# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import migrations


def create_schedule_for_previous_projects(apps, schema_editor):
    Schedule = apps.get_model("projects", "Schedule")
    Project = apps.get_model("projects", "Project")

    projects = Project.objects.all()

    for project in projects:
        schedule = getattr(project, "schedule", None)
        if schedule == None:
            start_at = getattr(project, 'start_at', None)
            expected_at = getattr(project, 'expected_at', None)
            Schedule.objects.create(project=project, start_time=start_at, delivery_time=expected_at)

class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0033_checkpoint_schedule'),
    ]

    operations = [
        migrations.RunPython(create_schedule_for_previous_projects, migrations.RunPython.noop),
    ]