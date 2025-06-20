# -*- coding:utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def migrate_migrate_proposals_closed_reason(apps, schema_editor):
    Proposal = apps.get_model("proposals", "Proposal")
    no_deal_proposals = Proposal.objects.filter(status__lt=11)
    no_deal_proposals.update(closed_reason=None, closed_reason_comment=None)

class Migration(migrations.Migration):
    dependencies = [
        ('proposals', '0043_auto_20190326_1912'),
    ]

    operations = [
        migrations.RunPython(migrate_migrate_proposals_closed_reason, migrations.RunPython.noop),
    ]
