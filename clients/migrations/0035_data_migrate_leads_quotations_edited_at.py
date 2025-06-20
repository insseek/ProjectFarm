from __future__ import unicode_literals

from django.db import migrations


def migrate_lead_quotations(apps, schema_editor):
    LeadQuotation = apps.get_model("clients", "LeadQuotation")
    quotations = LeadQuotation.objects.all()
    for quotation in quotations:
        quotation.edited_at = quotation.created_at
        quotation.edited_date = quotation.created_date
        quotation.editor = quotation.creator
        quotation.save()


class Migration(migrations.Migration):
    dependencies = [
        ('clients', '0034_auto_20200306_2224'),
    ]

    operations = [
        migrations.RunPython(migrate_lead_quotations, migrations.RunPython.noop),
    ]
