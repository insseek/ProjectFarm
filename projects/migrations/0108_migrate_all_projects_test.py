from __future__ import unicode_literals
from django.db import migrations


def migrate_all_projects_test(apps, schema_editor):
    Project = apps.get_model("projects", "Project")
    projects = Project.objects.all()
    for project in projects:
        if project.test_engineer_id:
            project.test_id = project.test_engineer_id
            project.save()

class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0107_auto_20190711_1816'),
    ]

    operations = [
        migrations.RunPython(migrate_all_projects_test, migrations.RunPython.noop),
    ]
