# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def move_projects_task_to_tasks_task(apps, schema_editor):
    try:
        ProjectsTask = apps.get_model("projects", "Task")
        TasksTask = apps.get_model("tasks", "Task")

        for task in ProjectsTask.objects.all():
            TasksTask.objects.create(
                name=task.name,
                creator=task.creator,
                principal=task.principal,
                expected_at=task.expected_at,
                is_done=task.is_done,
                done_at=task.done_at,
                content_type=task.content_type,
                object_id=task.object_id,
                created_at=task.created_at,
                modified_at=task.modified_at
            )
    except LookupError:
        pass


class Migration(migrations.Migration):
    dependencies = [
        ('tasks', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(move_projects_task_to_tasks_task, migrations.RunPython.noop),
    ]