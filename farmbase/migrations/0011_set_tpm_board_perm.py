# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import migrations


def set_tpm_board_perm(apps, schema_editor):
    FunctionModule = apps.get_model("farmbase", "FunctionModule")
    FunctionPermission = apps.get_model("farmbase", "FunctionPermission")

    func_module, created = FunctionModule.objects.get_or_create(name='项目',
                                                                codename='projects')
    permission = FunctionPermission.objects.filter(codename='view_tpm_board')
    if permission.exists():
        permission = permission.first()
        permission.name = '查看TPM看板'
        permission.module = func_module
        permission.save()
    else:
        FunctionPermission.objects.get_or_create(codename='view_tpm_board',
                                                 module=func_module,
                                                 name='查看TPM看板')


class Migration(migrations.Migration):
    dependencies = [
        ('farmbase', '0010_assign_func_perm_urls'),
    ]

    operations = [
        migrations.RunPython(set_tpm_board_perm, migrations.RunPython.noop),
    ]
