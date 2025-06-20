from __future__ import unicode_literals

from django.db import migrations, models


def data_migrate_contract_pay_way(apps, schema_editor):
    JobContract = apps.get_model("finance", "JobContract")
    contracts = JobContract.objects.all()
    for contract in contracts:
        if contract.status == 'uncommitted':
            continue
        if contract.status == 'waiting':
            contract.status = 'un_generate'
        else:
            contract.is_esign_contract = False
        contract.save()


class Migration(migrations.Migration):
    dependencies = [
        ('finance', '0041_auto_20210312_1530'),
    ]

    operations = [
        migrations.RunPython(data_migrate_contract_pay_way, migrations.RunPython.noop),
    ]