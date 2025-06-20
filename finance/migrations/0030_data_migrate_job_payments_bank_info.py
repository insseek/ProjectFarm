from __future__ import unicode_literals

from django.db import migrations, models


def data_migrate_job_payments_bank_info(apps, schema_editor):
    JobPayment = apps.get_model("finance", "JobPayment")

    payments = JobPayment.objects.all()
    for payment in payments:
        if payment.bank_info and not payment.payee_opening_bank:
            payment.payee_opening_bank = payment.bank_info
            payment.save()


class Migration(migrations.Migration):
    dependencies = [
        ('finance', '0029_auto_20201216_0312'),
    ]

    operations = [
        migrations.RunPython(data_migrate_job_payments_bank_info, migrations.RunPython.noop),
    ]
