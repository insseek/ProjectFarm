from django.db import migrations
from itertools import chain

from django.db.models import Case, IntegerField, Q, Sum, When, F
from playbook.tasks import rebuild_playbook_template_cache_data


def migrate_playbook_check_items(apps, schema_editor):
    CheckItem = apps.get_model("playbook", "CheckItem")
    TemplateCheckItem = apps.get_model("playbook", "TemplateCheckItem")

    TemplateCheckItem.objects.filter(period='sprint').update(period='once')
    CheckItem.objects.filter(period='sprint').update(period='once')

    TemplateCheckItem.objects.filter(expected_date_base='sprint_start_date').update(
        expected_date_base='stage_start_date')
    CheckItem.objects.filter(expected_date_base='sprint_start_date').update(expected_date_base='stage_start_date')

    TemplateCheckItem.objects.filter(expected_date_base='sprint_end_date').update(expected_date_base='stage_end_date')
    CheckItem.objects.filter(expected_date_base='sprint_end_date').update(expected_date_base='stage_end_date')

    rebuild_playbook_template_cache_data()


class Migration(migrations.Migration):
    dependencies = [
        ('playbook', '0026_auto_20210315_1255'),
    ]

    operations = [
        migrations.RunPython(migrate_playbook_check_items, migrations.RunPython.noop),
    ]
