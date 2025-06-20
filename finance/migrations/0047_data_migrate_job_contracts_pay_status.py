from __future__ import unicode_literals

from django.db import migrations, models


def data_migrate_job_contract_pay_status(apps, schema_editor):
    from finance.models import JobContract
    for obj in JobContract.objects.all():
        obj.save()


class Migration(migrations.Migration):
    dependencies = [
        ('finance', '0046_auto_20210408_1606'),
    ]

    operations = [
        migrations.RunPython(data_migrate_job_contract_pay_status, migrations.RunPython.noop),
    ]
