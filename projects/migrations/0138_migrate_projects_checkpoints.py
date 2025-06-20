from __future__ import unicode_literals

from django.db import migrations


def migrate_projects_checkpoints(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0137_migrate_projects_gantt_role'),
    ]

    operations = [
        migrations.RunPython(migrate_projects_checkpoints, migrations.RunPython.noop),
    ]
