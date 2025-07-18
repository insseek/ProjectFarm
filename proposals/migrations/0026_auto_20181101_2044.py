# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2018-11-01 20:44
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('proposals', '0025_auto_20181030_1317'),
    ]

    operations = [
        migrations.AddField(
            model_name='proposal',
            name='biz_opp_created_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='商机创建时间'),
        ),
        migrations.AddField(
            model_name='proposal',
            name='budget',
            field=models.FloatField(blank=True, null=True, verbose_name='预算 单位:万'),
        ),
        migrations.AddField(
            model_name='proposal',
            name='decision_makers',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='决策层'),
        ),
        migrations.AddField(
            model_name='proposal',
            name='decision_time',
            field=models.DateField(blank=True, null=True, verbose_name='决策时间'),
        ),
    ]
