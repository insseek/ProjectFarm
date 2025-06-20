from __future__ import unicode_literals

from django.db import migrations


def update_all_projects_checkpoints_name_position(apps, schema_editor):
    pass
    # CheckPoint = apps.get_model("projects", "ProjectPrototype")
    # Project = apps.get_model("projects", "Project")
    # update_all_projects_checkpoints(Project=Project, CheckPoint=CheckPoint)


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0075_auto_20180907_1046'),
    ]

    operations = [
        migrations.RunPython(update_all_projects_checkpoints_name_position, migrations.RunPython.noop),
    ]
