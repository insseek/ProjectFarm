from __future__ import unicode_literals

from django.db import migrations, models


def data_migrate_job_contract_payment_developer(apps, schema_editor):
    JobContract = apps.get_model("finance", "JobContract")
    contracts = JobContract.objects.all()
    for contract in contracts:
        if contract.job_position:
            contract.developer = contract.job_position.developer
            contract.save()

    JobPayment = apps.get_model("finance", "JobPayment")
    payments = JobPayment.objects.all()
    for payment in payments:
        if payment.position:
            payment.developer = payment.position.developer
            payment.save()


class Migration(migrations.Migration):
    dependencies = [
        ('finance', '0043_auto_20210325_1911'),
    ]

    operations = [
        migrations.RunPython(data_migrate_job_contract_payment_developer, migrations.RunPython.noop),
    ]
