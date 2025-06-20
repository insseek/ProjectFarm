# -*- coding: utf-8 -*-
from django.contrib.contenttypes.models import ContentType
from django.db import migrations


def migrate_existing_project_playbook_data(apps, schema_editor):
    project_type = ContentType.objects.get(app_label="projects", model="project")
    Stage = apps.get_model("playbook", "Stage")
    PROJECT_STAGES = ((5, '原型阶段'), (6, '设计阶段'), (7, '开发阶段'), (8, '测试阶段'), (9, '验收阶段'), (10, '完成'))
    Project = apps.get_model("projects", "Project")
    InfoItem = apps.get_model("playbook", "InfoItem")
    ChecklistItem = apps.get_model("playbook", "ChecklistItem")
    # 更新所有原项目playbook结构
    for project in Project.objects.all():
        checklist_items = ChecklistItem.objects.filter(content_type_id=project_type.id, object_id=project.id).all()
        info_items = InfoItem.objects.filter(content_type_id=project_type.id, object_id=project.id).all()
        for position, (status, stage_name) in enumerate(PROJECT_STAGES):
            stage, created = Stage.objects.get_or_create(status=status, name=stage_name,
                                                         content_type_id=project_type.id,
                                                         object_id=project.id, position=position)
            checklist_items.filter(status=status).update(stage=stage)
            info_items.filter(status=status).update(stage=stage)


class Migration(migrations.Migration):
    dependencies = [
        ('playbook', '0004_auto_20190108_1207'),
        ('projects', '0088_auto_20190104_1645'),
    ]

    operations = [
        migrations.RunPython(migrate_existing_project_playbook_data, migrations.RunPython.noop),
    ]
