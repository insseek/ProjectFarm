# -*- coding:utf-8 -*-
from __future__ import unicode_literals
from django.db import migrations


def set_view_pm_statistical_data_perm(apps, schema_editor):
    FunctionModule = apps.get_model("farmbase", "FunctionModule")
    FunctionPermission = apps.get_model("farmbase", "FunctionPermission")

    func_module, created = FunctionModule.objects.get_or_create(name='项目',
                                                                codename='projects')
    permission = FunctionPermission.objects.filter(codename='view_pm_statistical_data')
    if permission.exists():
        permission = permission.first()
        permission.name = '查看产品经理数据'
        permission.module = func_module
        permission.save()
    else:
        FunctionPermission.objects.get_or_create(codename='view_pm_statistical_data',
                                                                       module=func_module,
                                                                       name='查看产品经理数据')


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0069_refresh_project_prototype_files'),
    ]

    operations = [
        migrations.RunPython(set_view_pm_statistical_data_perm, migrations.RunPython.noop),
    ]
