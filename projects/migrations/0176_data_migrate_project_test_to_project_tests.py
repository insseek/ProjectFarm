from __future__ import unicode_literals

from django.db import migrations


def data_migrate_project_test_to_project_tests(apps, schema_editor):
    Project = apps.get_model("projects", "Project")
    ProjectTest = apps.get_model("projects", "ProjectTest")
    queryset = Project.objects.all()
    for obj in queryset:
        if obj.test_id:
            ProjectTest.objects.get_or_create(project_id=obj.id, test_id=obj.test_id)


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0175_merge_20210104_1753'),
    ]

    operations = [
        migrations.RunPython(data_migrate_project_test_to_project_tests, migrations.RunPython.noop),
    ]
