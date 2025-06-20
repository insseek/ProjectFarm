from __future__ import unicode_literals

from django.db import migrations


def migrate_projects_gantt_roles(apps, schema_editor):
    GanttRole = apps.get_model("projects", "GanttRole")
    GanttRole.objects.filter(role_type='csm').update(role_type='cs')
    GanttRole.objects.filter(role_type='pm').update(role_type='manager')


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0136_auto_20191217_1854'),
    ]

    operations = [
        migrations.RunPython(migrate_projects_gantt_roles, migrations.RunPython.noop),
    ]
