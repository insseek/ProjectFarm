from __future__ import unicode_literals

from django.db import migrations


def update_all_projects_checkpoints_name_position(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0095_checkpoint_is_confirmed'),
    ]

    operations = [
        migrations.RunPython(update_all_projects_checkpoints_name_position, migrations.RunPython.noop),
    ]
