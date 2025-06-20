# -*- coding:utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from proposals.models import Proposal


def migrate_proposal_status(apps, schema_editor):
    Proposal.objects.filter(status=3).update(status=4)

class Migration(migrations.Migration):
    dependencies = [
        ('proposals', '0033_auto_20190222_1741'),
    ]

    operations = [
        migrations.RunPython(migrate_proposal_status, migrations.RunPython.noop),
    ]
