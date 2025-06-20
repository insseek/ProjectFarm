# -*- coding:utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def migrate_lead_proposal_time(apps, schema_editor):
    Proposal = apps.get_model("proposals", "Proposal")
    Lead = apps.get_model("clients", "Lead")
    leads = Lead.objects.exclude(status__in=['contact', 'invalid'])
    proposals = Proposal.objects.all()

    for lead in leads:
        proposal = proposals.filter(lead_id=lead.id)
        if proposal.exists():
            proposal = proposal.first()
            lead.proposal_created_at = proposal.created_at
            lead.proposal_closed_at = proposal.closed_at
            lead.save()


class Migration(migrations.Migration):
    dependencies = [
        ('clients', '0013_auto_20190509_2038'),
    ]

    operations = [
        migrations.RunPython(migrate_lead_proposal_time, migrations.RunPython.noop),
    ]
