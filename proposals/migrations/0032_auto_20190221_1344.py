# Generated by Django 2.0 on 2019-02-21 13:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('proposals', '0031_handoverreceipt'),
    ]

    operations = [
        migrations.AlterField(
            model_name='handoverreceipt',
            name='addressee_address',
            field=models.CharField(max_length=150, verbose_name='邮寄收件人地址'),
        ),
        migrations.AlterField(
            model_name='handoverreceipt',
            name='addressee_name',
            field=models.CharField(max_length=20, verbose_name='邮寄收件人姓名'),
        ),
        migrations.AlterField(
            model_name='handoverreceipt',
            name='addressee_phone_number',
            field=models.CharField(max_length=30, verbose_name='邮寄收件人联系方式'),
        ),
        migrations.AlterField(
            model_name='handoverreceipt',
            name='invoice_mode',
            field=models.CharField(choices=[('invoice_first', '先票后款'), ('payment_first', '先款后票')], max_length=20, verbose_name='开票方式'),
        ),
        migrations.AlterField(
            model_name='handoverreceipt',
            name='invoice_period',
            field=models.CharField(choices=[('one-off', '所有款项金额统一开票'), ('periodic', '一期一开')], max_length=20, verbose_name='开票周期'),
        ),
        migrations.AlterField(
            model_name='handoverreceipt',
            name='invoice_type',
            field=models.CharField(choices=[('plain', '增值税普票'), ('special', '增值税专票')], max_length=20, verbose_name='开票类型'),
        ),
        migrations.AlterField(
            model_name='handoverreceipt',
            name='op_invoice_mode',
            field=models.CharField(blank=True, choices=[('invoice_first', '先票后款'), ('payment_first', '先款后票')], max_length=20, null=True, verbose_name='运维开票方式'),
        ),
        migrations.AlterField(
            model_name='handoverreceipt',
            name='op_payment_mode',
            field=models.CharField(blank=True, choices=[('monthly', '按月'), ('quarterly', '按季度'), ('yearly', '按年')], max_length=20, null=True, verbose_name='运维支付类型'),
        ),
    ]
