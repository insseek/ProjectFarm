# Generated by Django 2.0 on 2020-11-11 15:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0011_jobpayment_modified_at'),
    ]

    operations = [
        migrations.AlterField(
            model_name='jobpayment',
            name='status',
            field=models.IntegerField(choices=[(0, '记录'), (1, '启动'), (2, '完成'), (3, '异常')], default=0, verbose_name='状态'),
        ),
    ]
