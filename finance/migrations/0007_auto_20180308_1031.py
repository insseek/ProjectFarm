# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2018-03-08 10:31
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0006_permission_assignment'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='jobpayment',
            options={'permissions': (('gear_view_all_payments', '查看全部工程师打款'),), 'verbose_name': '打款记录'},
        ),
    ]
