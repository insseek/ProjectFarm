# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from farmbase.models import FunctionModule, FunctionPermission
from farmbase.permissions_init import FUNC_PERMS


def assign_func_perm_urls(apps, schema_editor):
    for func_module_perms in FUNC_PERMS:
        func_module_data = func_module_perms['func_module']
        func_module, created = FunctionModule.objects.get_or_create(name=func_module_data['name'],
                                                                    codename=func_module_data['codename'])
        for permission_data in func_module_perms['func_perms']:
            permission = FunctionPermission.objects.filter(codename=permission_data['codename'])
            if permission.exists():
                permission = permission.first()
                permission.name = permission_data['name']
                permission.module = func_module
                permission.save()
            else:
                FunctionPermission.objects.get_or_create(codename=permission_data['codename'],
                                                                               module=func_module,
                                                                               name=permission_data['name'])


class Migration(migrations.Migration):
    dependencies = [
        ('farmbase', '0009_auto_20180517_1645'),
    ]

    operations = [
        migrations.RunPython(assign_func_perm_urls, migrations.RunPython.noop),
    ]
