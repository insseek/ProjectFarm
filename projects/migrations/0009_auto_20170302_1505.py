# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2017-03-02 07:05
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0008_auto_20170213_1415'),
    ]

    operations = [
        migrations.AlterField(
            model_name='phase',
            name='project',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='phases', to='projects.Project', verbose_name='项目'),
        ),
    ]
