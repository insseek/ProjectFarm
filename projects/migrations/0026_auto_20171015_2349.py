# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2017-10-15 23:49
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0025_data_init_permissions'),
    ]

    operations = [
        migrations.AlterField(
            model_name='task',
            name='content_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='contenttypes.ContentType'),
        ),
        migrations.AlterField(
            model_name='task',
            name='object_id',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
