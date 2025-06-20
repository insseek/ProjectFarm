# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import migrations


def migration_frame_diagrams(apps, schema_editor):
    FrameDiagram = apps.get_model("reports", "FrameDiagram")

    FrameDiagramTag = apps.get_model("reports", "FrameDiagramTag")

    FrameDiagram.objects.filter(is_standard=True).delete()
    FrameDiagramTag.objects.all().delete()

class Migration(migrations.Migration):
    dependencies = [
        ('reports', '0026_migration_report_published_at'),
    ]
    operations = [
        migrations.RunPython(migration_frame_diagrams, migrations.RunPython.noop),
    ]
