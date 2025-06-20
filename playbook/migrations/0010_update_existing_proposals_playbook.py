# -*- coding: utf-8 -*-
import re
from django.db import migrations


def migrate_existing_proposal_playbook(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('playbook', '0009_extract_links_from_proposal_playbook_item'),
    ]

    operations = [
        migrations.RunPython(migrate_existing_proposal_playbook, migrations.RunPython.noop),
    ]
