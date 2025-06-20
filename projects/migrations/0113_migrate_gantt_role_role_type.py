from __future__ import unicode_literals
from django.db import migrations


def migrate_gantt_role_role_type(apps, schema_editor):
    GanttRole = apps.get_model("projects", "GanttRole")
    GanttRole.objects.filter(name__icontains='设计').update(role_type='设计师')


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0112_auto_20190731_1313'),
    ]

    operations = [
        migrations.RunPython(migrate_gantt_role_role_type, migrations.RunPython.noop),
    ]
