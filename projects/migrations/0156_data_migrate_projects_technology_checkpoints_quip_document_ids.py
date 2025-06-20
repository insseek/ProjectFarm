from __future__ import unicode_literals
import json

from django.db import migrations


def data_migrate_projects_technology_checkpoints_quip_document_ids(apps, schema_editor):
    TechnologyCheckpoint = apps.get_model("projects", "TechnologyCheckpoint")
    checkpoints = TechnologyCheckpoint.objects.filter(quip_document_id__isnull=False)
    for checkpoint in checkpoints:
        if checkpoint.quip_document_id:
            quip_document_ids = [checkpoint.quip_document_id]
            checkpoint.quip_document_ids = json.dumps(quip_document_ids, ensure_ascii=False)
            checkpoint.save()


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0155_technologycheckpoint_quip_document_ids'),
    ]

    operations = [
        migrations.RunPython(data_migrate_projects_technology_checkpoints_quip_document_ids, migrations.RunPython.noop),
    ]
