from __future__ import unicode_literals

from django.db import migrations, models


def data_migrate_old_job_position_contract_payee_data(apps, schema_editor):
    JobContract = apps.get_model("finance", "JobContract")
    payee_fields = ('payee_name', 'payee_id_card_number', 'payee_phone', 'payee_opening_bank', 'payee_account')
    for job_contract in JobContract.objects.filter(is_null_contract=True):
        if job_contract.payee_name:
            continue
        job_position = job_contract.job_position
        developer = job_position.developer
        if developer and developer.payee_name:
            for payee_field in payee_fields:
                setattr(job_contract, payee_field, getattr(developer, payee_field, None))
            job_contract.save()
            continue
        payments = job_contract.payments.order_by('-created_at')
        for payment in payments:
            if payment.bank_info:
                job_contract.payee_opening_bank = payment.bank_info
                job_contract.save()
                break


class Migration(migrations.Migration):
    dependencies = [
        ('finance', '0031_auto_20201218_1324'),
    ]

    operations = [
        migrations.RunPython(data_migrate_old_job_position_contract_payee_data, migrations.RunPython.noop),
    ]
