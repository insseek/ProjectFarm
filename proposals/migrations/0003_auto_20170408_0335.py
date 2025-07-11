# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2017-04-08 03:35
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('proposals', '0002_data_migrate_potential_client'),
    ]

    operations = [
        migrations.AlterField(
            model_name='proposal',
            name='status',
            field=models.IntegerField(choices=[(1, '等待认领'), (2, '等待沟通'), (3, '等待报告'), (4, '进行中'), (5, '成单'), (6, '未成单')], default=1, verbose_name='需求状态'),
        ),
    ]
