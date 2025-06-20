# -*- coding:utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def migrate_lead_created_date(apps, schema_editor):
    Lead = apps.get_model("clients", "Lead")
    leads = Lead.objects.all()
    for lead in leads:
        lead.created_date = lead.created_at
        lead.save()

class Migration(migrations.Migration):
    dependencies = [
        ('clients', '0015_lead_created_date'),
    ]

    operations = [
        migrations.RunPython(migrate_lead_created_date, migrations.RunPython.noop),
    ]
