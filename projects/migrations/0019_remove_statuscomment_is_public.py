# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2017-05-12 11:11
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0018_data_migrate_status_comments_to_comments'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='statuscomment',
            name='is_public',
        ),
    ]
