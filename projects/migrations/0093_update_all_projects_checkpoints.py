from __future__ import unicode_literals

from django.db import migrations


def update_all_projects_checkpoints_name_position(apps, schema_editor):
    pass
    # CheckPoint = apps.get_model("projects", "CheckPoint")
    # checkpoints = CheckPoint.objects.all()
    # checkpoints.filter(name="交付代码审核").update(name="验收代码审核")
    # checkpoints.filter(name="交付初稿版本").update(name="验收初稿版本")
    # checkpoints.filter(name="中期审核").update(name="中期代码审核")


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0092_merge_20190122_1651'),
    ]

    operations = [
        migrations.RunPython(update_all_projects_checkpoints_name_position, migrations.RunPython.noop),
    ]
