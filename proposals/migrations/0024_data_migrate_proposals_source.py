# -*- coding:utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def migrate_proposal_source(apps, schema_editor):
    Proposal = apps.get_model("proposals", "Proposal")

    proposals = Proposal.objects.all()
    proposals.filter(source=8).update(source=3)
    proposals.filter(source=6).update(source=5)
    proposals.filter(source=4).update(source=1, source_remark='原朋友')


class Migration(migrations.Migration):
    dependencies = [
        ('proposals', '0023_auto_20181030_1306'),
    ]

    operations = [
        migrations.RunPython(migrate_proposal_source, migrations.RunPython.noop),
    ]
