from __future__ import unicode_literals

from django.db import migrations


def update_all_projects_checkpoints_name_position(apps, schema_editor):
    pass
    # CheckPoint = apps.get_model("projects", "CheckPoint")
    # checkpoints = CheckPoint.objects.all()
    # checkpoints.filter(name="kick off meeting").update(name="kickoff meeting")
    # checkpoints.filter(name="代码审核").update(name="交付代码审核")
    # checkpoints.filter(name="交付审核").update(name="交付文档审核")

class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0062_permission_assignment'),
    ]

    operations = [
        migrations.RunPython(update_all_projects_checkpoints_name_position, migrations.RunPython.noop),
    ]
