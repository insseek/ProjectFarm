# Generated by Django 2.0 on 2019-08-27 11:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0018_requirementinfo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lead',
            name='search_engine_type',
            field=models.CharField(blank=True, choices=[('toutiao', '今日头条'), ('sougou', '搜狗'), ('shenma', '神马'), ('360', '360 SEM'), ('baidu', '百度SEM'), ('phone', '400电话'), ('website', '官网'), ('mini_program', '微信小程序')], max_length=15, null=True, verbose_name='搜索引擎类型'),
        ),
    ]
