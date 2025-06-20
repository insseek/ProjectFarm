from __future__ import unicode_literals
from django.db import migrations


def migrate_all_projects_payments_total_amount(apps, schema_editor):
    ProjectPayment = apps.get_model("projects", "ProjectPayment")

    payments = ProjectPayment.objects.all()
    for payment in payments:
        finance_fields = {'first_stage_amount', 'second_stage_amount', 'third_stage_amount',
                          'fourth_stage_amount'}
        if payment.total_amount and not any([getattr(payment, field) for field in finance_fields]):
            payment.first_stage_amount = payment.total_amount
            payment.save()
            continue

        if not payment.total_amount and any([getattr(payment, field) for field in finance_fields]):
            total_amount = sum([getattr(payment, field) for field in finance_fields if getattr(payment, field)])
            payment.total_amount = total_amount
            payment.save()


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0104_migrate_all_projects_payments_need_invoice_and_status_data'),
    ]

    operations = [
        migrations.RunPython(migrate_all_projects_payments_total_amount, migrations.RunPython.noop),
    ]
