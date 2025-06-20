# -*- coding:utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from django.utils import timezone
from proposals.models import Proposal

PROPOSAL_STATUS_DICT = Proposal.PROPOSAL_STATUS_DICT

def migrate_migrate_proposals_expired_at(apps, schema_editor):
    Proposal = apps.get_model("proposals", "Proposal")
    no_deal_proposals = Proposal.objects.filter(status=PROPOSAL_STATUS_DICT['no_deal']['status'])
    for proposal in no_deal_proposals:
        reports = proposal.reports.all()
        for report in reports:
            if report.is_public and report.expired_at and report.expired_at > timezone.now():
                report.expired_at = timezone.now()
                report.save()

class Migration(migrations.Migration):
    dependencies = [
        ('proposals', '0046_auto_20190702_1217'),
    ]

    operations = [
        migrations.RunPython(migrate_migrate_proposals_expired_at, migrations.RunPython.noop),
    ]
