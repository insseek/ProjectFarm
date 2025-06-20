# -*- coding:utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def migrate_proposal_status(apps, schema_editor):
    Proposal = apps.get_model("proposals", "Proposal")

    proposals = Proposal.objects.all()
    proposals.filter(status=5, closed_at__isnull=False).update(status=10)
    proposals.filter(status=6, closed_at__isnull=False).update(status=11)
    proposals.filter(status=4, biz_opp_created_at__isnull=False).update(status=5)


class Migration(migrations.Migration):
    dependencies = [
        ('proposals', '0029_auto_20190215_1726'),
    ]

    operations = [
        migrations.RunPython(migrate_proposal_status, migrations.RunPython.noop),
    ]
