# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2016-11-22 10:36
from __future__ import unicode_literals

from django.db import migrations
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone


def data_migrate_test_case_execution_count(apps, schema_editor):
    # 通过get_model获取的Model是当执行脚本时前数据库的model 不是代码中最新的model
    from testing.models import ProjectTestCase

    for obj in ProjectTestCase.objects.all():
        obj.execution_count = obj.build_execution_count()
        obj.save()


class Migration(migrations.Migration):
    dependencies = [
        ('testing', '0011_projecttestcase_execution_count'),
    ]

    operations = [
        migrations.RunPython(data_migrate_test_case_execution_count, migrations.RunPython.noop),
    ]
