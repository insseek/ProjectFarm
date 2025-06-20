# -*- coding: utf-8 -*-
from django.contrib.contenttypes.models import ContentType
from django.db import migrations
from proposals.models import Proposal


def migrate_existing_proposal_playbook_data(apps, schema_editor):
    proposal_type = ContentType.objects.get(app_label="proposals", model="proposal")

    Proposal = apps.get_model("proposals", "Proposal")
    Stage = apps.get_model("playbook", "Stage")

    InfoItem = apps.get_model("playbook", "InfoItem")
    ChecklistItem = apps.get_model("playbook", "ChecklistItem")

    PROJECT_STAGES = (
    (1, '等待认领'), (2, '等待沟通'), (4, '进行中'), (5, '商机阶段'), (6, '成单交接'), (10, '成单'), (11, '未成单'))
    # 更新所有原项目playbook结构
    for proposal in Proposal.objects.all():
        checklist_items = ChecklistItem.objects.filter(content_type_id=proposal_type.id, object_id=proposal.id).all()
        info_items = InfoItem.objects.filter(content_type_id=proposal_type.id, object_id=proposal.id).all()
        for position, (status, stage_name) in enumerate(PROJECT_STAGES):
            stage, created = Stage.objects.get_or_create(status=status, name=stage_name,
                                                         content_type_id=proposal_type.id,
                                                         object_id=proposal.id, position=position)
            checklist_items.filter(status__isnull=False, status=status).update(stage=stage)
            info_items.filter(status__isnull=False, status=status).update(stage=stage)


class Migration(migrations.Migration):
    dependencies = [
        ('playbook', '0007_auto_20190108_1209'),
        ('proposals', '0040_auto_20190320_1427'),
    ]

    operations = [
        migrations.RunPython(migrate_existing_proposal_playbook_data, migrations.RunPython.noop),
    ]
