# Generated by Django 2.0 on 2020-12-18 13:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0030_data_migrate_job_payments_bank_info'),
    ]

    operations = [
        migrations.AlterField(
            model_name='jobcontract',
            name='payee_opening_bank',
            field=models.TextField(blank=True, null=True, verbose_name='收款人开户行'),
        ),
    ]
