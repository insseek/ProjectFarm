# -*- coding:utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def migrate_proposal_sources(apps, schema_editor):
    Proposal = apps.get_model("proposals", "Proposal")
    RELIABILITY_MIGRATION_DICT = {
        1: 'low',
        2: 'general',
        3: 'major'
    }
    SOURCE_MIGRATION_DICT = {
        1: 'other',
        2: 'search_engine',
        3: 'client_referral',
        4: 'client_repurchase',
        5: 'strategy_cooperation',
        6: 'rebate_cooperation',
        7: 'activity',
        9: 'oneself',
    }

    for old_value, new_value in RELIABILITY_MIGRATION_DICT.items():
        Proposal.objects.filter(reliability=old_value).update(reliability=new_value)

    for old_value, new_value in SOURCE_MIGRATION_DICT.items():
        Proposal.objects.filter(source=old_value).update(source=new_value)


class Migration(migrations.Migration):
    dependencies = [
        ('proposals', '0036_auto_20190307_1508'),
    ]

    operations = [
        migrations.RunPython(migrate_proposal_sources, migrations.RunPython.noop),
    ]
