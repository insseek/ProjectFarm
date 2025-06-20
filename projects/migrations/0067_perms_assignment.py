# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import migrations


def set_project_prototype_perm(apps, schema_editor):
    FunctionModule = apps.get_model("farmbase", "FunctionModule")
    FunctionPermission = apps.get_model("farmbase", "FunctionPermission")

    func_module, created = FunctionModule.objects.get_or_create(name='项目',
                                                                codename='projects')
    permission = FunctionPermission.objects.filter(codename='view_project_prototypes')
    if permission.exists():
        permission = permission.first()
        permission.name = '查看项目原型'
        permission.module = func_module
        permission.save()
    else:
        FunctionPermission.objects.get_or_create(codename='view_project_prototypes',
                                                 module=func_module,
                                                 name='查看项目原型')


class Migration(migrations.Migration):
    dependencies = [
        ('farmbase', '0009_auto_20180517_1645'),
        ('projects', '0066_auto_20180604_1529'),
    ]

    operations = [
        migrations.RunPython(set_project_prototype_perm, migrations.RunPython.noop),
    ]
