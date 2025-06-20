from django.db import migrations
from itertools import chain

from django.db.models import Case, IntegerField, Q, Sum, When, F
from playbook.tasks import rebuild_playbook_template_cache_data


def migrate_playbook_stage(apps, schema_editor):
    Stage = apps.get_model("playbook", "Stage")
    TemplateStage = apps.get_model("playbook", "TemplateStage")

    TemplateStage.objects.filter(stage_code='completion').delete()
    Stage.objects.filter(stage_code='completion').delete()

    rebuild_playbook_template_cache_data()


class Migration(migrations.Migration):
    dependencies = [
        ('playbook', '0024_auto_20210302_1702'),
    ]

    operations = [
        migrations.RunPython(migrate_playbook_stage, migrations.RunPython.noop),
    ]
