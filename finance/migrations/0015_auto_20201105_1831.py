# Generated by Django 2.0 on 2020-11-05 18:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0014_projectpayment_close_reason'),
    ]

    operations = [
        migrations.AlterField(
            model_name='projectpayment',
            name='invoice',
            field=models.CharField(choices=[('general', '普票'), ('special', '专票'), ('none', '不需要'), ('invoice', '需要')], default='none', max_length=50, verbose_name='发票'),
        ),
        migrations.AlterField(
            model_name='projectpaymentstage',
            name='invoice',
            field=models.CharField(choices=[('general', '普票'), ('special', '专票'), ('invoice', '已开'), ('none', '未开')], default='none', max_length=15, verbose_name='发票'),
        ),
    ]
