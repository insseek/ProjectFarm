# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def gen_track_code(apps, schema_editor):
    Project = apps.get_model("projects", "Project")
    for project in Project.objects.all():
        if not project.track_code:
            project.track_code = Project.gen_project_track_code()
            project.save()


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0006_project_track_code'),
    ]

    operations = [
        migrations.RunPython(gen_track_code, migrations.RunPython.noop),
    ]
