# Generated by Django 2.0 on 2020-12-10 12:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0025_jobcontract_committed_at'),
    ]

    operations = [
        migrations.RenameField(
            model_name='projectpayment',
            old_name='close_reason',
            new_name='close_remarks',
        ),
        migrations.AddField(
            model_name='projectpayment',
            name='termination_reason',
            field=models.CharField(blank=True, choices=[('contract_termination', '合同终止'), ('fill_error', '填写错误')], max_length=10, null=True, verbose_name='终止原因'),
        ),
    ]
