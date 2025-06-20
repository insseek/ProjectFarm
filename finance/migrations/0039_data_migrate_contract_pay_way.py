from __future__ import unicode_literals

from django.db import migrations, models


def data_migrate_contract_pay_way(apps, schema_editor):
    JobContract = apps.get_model("finance", "JobContract")
    contracts = JobContract.objects.filter(status__in=['signed', 'closed'])
    for contract in contracts:
        pay_way = 'installments'
        if contract.pay_way == 'disposable':
            pay_way = 'one_off'
        contract.pay_way = pay_way
        contract.save()


class Migration(migrations.Migration):
    dependencies = [
        ('finance', '0038_auto_20210220_1708'),
    ]

    operations = [
        migrations.RunPython(data_migrate_contract_pay_way, migrations.RunPython.noop),
    ]
