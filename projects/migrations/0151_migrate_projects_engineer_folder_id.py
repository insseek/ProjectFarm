from __future__ import unicode_literals

from django.db import migrations


def migrate_projects_quip_engineer_folder_id(apps, schema_editor):
    ProjectLinks = apps.get_model("projects", "ProjectLinks")
    projects = ProjectLinks.objects.filter(engineer_contact_folder__isnull=False)
    for project in projects:
        if project.engineer_contact_folder:
            split_list = project.engineer_contact_folder.replace('://', "").split('/')
            if len(split_list) >= 2:
                folder_id = split_list[1].strip()
                project.quip_engineer_folder_id = folder_id
                project.save()


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0150_auto_20200514_1107'),
    ]

    operations = [
        migrations.RunPython(migrate_projects_quip_engineer_folder_id, migrations.RunPython.noop),
    ]
