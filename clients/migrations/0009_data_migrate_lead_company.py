# -*- coding:utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def migrate_lead_company(apps, schema_editor):
    Lead = apps.get_model("clients", "Lead")
    LeadOrganization = apps.get_model("clients", "LeadOrganization")

    leads = Lead.objects.filter(company_name__isnull=False, company_id__isnull=True)
    for lead in leads:
        company_name = lead.company_name
        if company_name:
            organization = LeadOrganization.objects.filter(name=company_name).first()
            if not organization:
                organization = LeadOrganization.objects.create(name=company_name, creator=lead.creator)

            lead.company = organization
            lead.save()


class Migration(migrations.Migration):
    dependencies = [
        ('clients', '0008_auto_20190318_2118'),
    ]

    operations = [
        migrations.RunPython(migrate_lead_company, migrations.RunPython.noop),
    ]
