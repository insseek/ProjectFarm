# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2017-11-28 17:03
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('playbook', '0002_auto_20170628_1138'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='checklistitem',
            options={'ordering': ['position'], 'verbose_name': 'Playbook检查项'},
        ),
    ]
