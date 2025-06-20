from __future__ import unicode_literals

from django.db import migrations
from django.contrib.auth.models import Group


def migrate_projects_product_manager_project_manager(apps, schema_editor):
    Project = apps.get_model("projects", "Project")
    projects = Project.objects.all()
    for project in projects:
        if project.manager:
            project.product_manager = project.manager
            project.save()
    pass
    # cs_group, created = Group.objects.get_or_create(name='客户成功')
    # project_manager_group, created = Group.objects.get_or_create(name='项目经理')
    # CheckPoint = apps.get_model("projects", "CheckPoint")
    # checkpoints = CheckPoint.objects.all()
    # checkpoints.filter(post_id=cs_group.id).update(post_id=project_manager_group.id)


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0141_auto_20200311_1819'),
    ]

    operations = [
        migrations.RunPython(migrate_projects_product_manager_project_manager, migrations.RunPython.noop),
    ]
