# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2018-10-30 13:06
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workorder', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='workorder',
            options={'ordering': ['-created_at'], 'verbose_name': '工单'},
        ),
    ]
