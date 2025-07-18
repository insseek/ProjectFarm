# Generated by Django 2.0 on 2020-05-18 14:21

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('proposals', '0060_auto_20200515_1835'),
    ]

    operations = [
        migrations.AddField(
            model_name='proposal',
            name='rebate',
            field=models.CharField(choices=[('0', '渠道介绍，需要分成'), ('1', '内部成员，但需要返点'), ('2', '不需要返点')], max_length=2,
                                   default='2', verbose_name='返点'),
        ),
        migrations.AddField(
            model_name='proposal',
            name='rebate_info',
            field=models.CharField(blank=True, max_length=64, null=True, verbose_name='返点信息'),
        ),
        migrations.AlterField(
            model_name='proposal',
            name='reference',
            field=models.CharField(blank=True, choices=[('0', '参考全部'), ('1', '参考部分页面/流程'), ('2', '其他'), ('3', '无')],
                                   max_length=2, null=True, verbose_name='竞品参考'),
        ),
    ]
