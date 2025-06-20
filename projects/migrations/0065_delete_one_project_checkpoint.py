from __future__ import unicode_literals

from django.db import migrations
from projects.models import Project


def delete_one_project_checkpoint(apps, schema_editor):
    # CheckPoint = apps.get_model("projects", "CheckPoint")
    # checkpoints = CheckPoint.objects.all()
    # checkpoints.filter(name="合同").update(is_active=False)
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0064_checkpoint_is_active'),
    ]

    operations = [
        migrations.RunPython(delete_one_project_checkpoint, migrations.RunPython.noop),
    ]
