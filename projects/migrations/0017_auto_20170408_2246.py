# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2017-04-08 22:46
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0016_remove_task_project'),
    ]

    operations = [
        migrations.AlterField(
            model_name='project',
            name='status',
            field=models.IntegerField(choices=[(5, 'PRD'), (6, '设计'), (7, '开发'), (8, '测试'), (9, '交付'), (10, '完成')], default=1, verbose_name='项目状态'),
        ),
    ]
