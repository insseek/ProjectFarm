# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2017-11-22 13:24
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('developers', '0007_auto_20171108_1238'),
    ]

    operations = [
        migrations.AddField(
            model_name='developer',
            name='fulltime_status',
            field=models.CharField(choices=[('A', '未填写'), ('B', '全职'), ('C', '半全职'), ('D', '兼职')], default='A', max_length=2, verbose_name='工作时间'),
        ),
    ]
