from __future__ import unicode_literals
from django.db import migrations


def migrate_all_projects_payments_need_invoice_and_status_data(apps, schema_editor):
    ProjectPayment = apps.get_model("projects", "ProjectPayment")

    payments = ProjectPayment.objects.all()
    for payment in payments:
        finance_fields = {'total_amount', 'first_stage_amount', 'second_stage_amount', 'third_stage_amount',
                          'fourth_stage_amount'}
        if not any([getattr(payment, field) for field in finance_fields]):
            payment.delete()
            continue
        if payment.first_stage_amount and payment.first_stage_paid_at:
            payment.first_stage_received_amount = payment.first_stage_amount
        if payment.second_stage_amount and payment.second_stage_paid_at:
            payment.second_stage_received_amount = payment.second_stage_amount
        if payment.third_stage_amount and payment.third_stage_paid_at:
            payment.third_stage_received_amount = payment.third_stage_amount
        if payment.fourth_stage_amount and payment.fourth_stage_paid_at:
            payment.fourth_stage_received_amount = payment.fourth_stage_amount
        is_finished = get_is_finished(payment)
        if is_finished:
            payment.status = 'finished'
        payment.save()


def is_fully_paid(payment):
    if not payment.total_amount:
        return True
    paid_total_amount = 0
    amount_list = [payment.first_stage_received_amount, payment.second_stage_received_amount,
                   payment.third_stage_received_amount, payment.fourth_stage_received_amount]
    if any(amount_list):
        paid_total_amount = sum([amount for amount in amount_list if amount])
    return payment.total_amount == paid_total_amount


def get_is_finished(payment):
    if not is_fully_paid(payment):
        return False
    if payment.first_stage_amount:
        if payment.first_stage_amount != payment.first_stage_received_amount:
            return False
        if payment.need_invoice and not payment.first_stage_has_invoice:
            return False
    if payment.second_stage_amount:
        if payment.second_stage_amount != payment.second_stage_received_amount:
            return False
        if payment.need_invoice and not payment.second_stage_has_invoice:
            return False
    if payment.third_stage_amount:
        if payment.third_stage_amount != payment.third_stage_received_amount:
            return False
        if payment.need_invoice and not payment.third_stage_has_invoice:
            return False
    if payment.fourth_stage_amount:
        if payment.fourth_stage_amount != payment.fourth_stage_received_amount:
            return False
        if payment.need_invoice and not payment.fourth_stage_has_invoice:
            return False
    return True


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0103_auto_20190612_1721'),
    ]

    operations = [
        migrations.RunPython(migrate_all_projects_payments_need_invoice_and_status_data, migrations.RunPython.noop),
    ]
