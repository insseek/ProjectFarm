from __future__ import unicode_literals

from django.db import migrations, models


def data_migrate_old_job_position_confidentiality_agreement_data(apps, schema_editor):
    JobContract = apps.get_model("finance", "JobContract")
    job_contracts = JobContract.objects.filter(status__in=['signed', 'closed'])
    for i in job_contracts:
        i.is_confidentiality_agreement = False
        i.save()


class Migration(migrations.Migration):
    dependencies = [
        ('finance', '0034_jobcontract_is_confidentiality_agreement'),
    ]

    operations = [
        migrations.RunPython(data_migrate_old_job_position_confidentiality_agreement_data, migrations.RunPython.noop),
    ]