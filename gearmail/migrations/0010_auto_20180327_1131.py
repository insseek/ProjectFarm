# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2018-03-27 11:31
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gearmail', '0009_data_migrate_mail_template_subject_to_title'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='emailrecord',
            options={'ordering': ['-created_at'], 'permissions': (('gear_use_farm_send_email', '使用Farm发送邮件'),), 'verbose_name': '邮件记录'},
        ),
    ]
