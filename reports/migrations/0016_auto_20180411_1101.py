# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2018-04-11 11:01
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0015_auto_20180403_1744'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='report',
            options={'ordering': ['-created_at', 'title'], 'permissions': (('gear_view_all_reports', '查看全部报告'),), 'verbose_name': '报告'},
        ),
    ]
