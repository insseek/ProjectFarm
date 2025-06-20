# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from django.db import transaction
from django.contrib.contenttypes.models import ContentType


def data_migrate_project_payments(apps, schema_editor):
    with transaction.atomic():
        savepoint = transaction.savepoint()
        try:
            migrate_objs(apps)
        except:
            transaction.savepoint_rollback(savepoint)
            raise


def migrate_objs(apps):
    OriginProjectPayment = apps.get_model("projects", "ProjectPayment")
    ProjectPayment = apps.get_model("finance", "ProjectPayment")
    ProjectPaymentStage = apps.get_model("finance", "ProjectPaymentStage")
    Log = apps.get_model("logs", "Log")
    origin_payment_type = ContentType.objects.get_for_model(OriginProjectPayment)
    payment_type = ContentType.objects.get_for_model(ProjectPayment)
    STATUS_DICT = {
        'ongoing': 'process',
        'finished': 'completed',
        'abend': 'termination'
    }
    stage_fields = {'amount', 'received_amount', 'paid_at', 'has_invoice'}
    stage_prefixs = ('first_stage_', 'second_stage_', 'third_stage_', 'fourth_stage_')
    for origin_payment in OriginProjectPayment.objects.all():
        invoice = 'invoice' if origin_payment.need_invoice else 'none'
        payment = ProjectPayment.objects.create(
            project=origin_payment.project,
            contract_name=origin_payment.name,
            capital_account=origin_payment.payment_account_name,
            total_amount=origin_payment.total_amount,
            invoice=invoice,
            remarks=origin_payment.remarks,
            status=STATUS_DICT[origin_payment.status]
        )
        Log.objects.filter(content_type_id=origin_payment_type.id, object_id=origin_payment.id).update(
            content_type_id=payment_type.id, object_id=payment.id
        )

        new_index = 0
        for stage_prefix in stage_prefixs:
            receivable_amount = getattr(origin_payment, stage_prefix + 'amount', None)
            receipted_amount = getattr(origin_payment, stage_prefix + 'received_amount', None)
            receipted_date = getattr(origin_payment, stage_prefix + 'paid_at', None)
            invoice = 'invoice' if getattr(origin_payment, stage_prefix + 'has_invoice', False) else 'none'
            if any([receivable_amount, receipted_amount]):
                stage = ProjectPaymentStage.objects.create(
                    project_payment=payment,
                    index=new_index,
                    receivable_amount=receivable_amount,
                    receipted_amount=receipted_amount,
                    receipted_date=receipted_date,
                    invoice=invoice
                )
                ProjectPaymentStage.objects.filter(pk=stage.id).update(
                    created_at=origin_payment.created_at,
                    modified_at=origin_payment.modified_at
                )
                new_index += 1
        ProjectPayment.objects.filter(pk=payment.id).update(
            created_at=origin_payment.created_at,
            modified_at=origin_payment.modified_at
        )


class Migration(migrations.Migration):
    dependencies = [
        ('finance', '0015_auto_20201105_1831'),
        ('projects', '0169_auto_20201030_1423'),
        ('logs', '0022_browsinghistory_user'),

    ]

    operations = [
        migrations.RunPython(data_migrate_project_payments, migrations.RunPython.noop),
    ]
