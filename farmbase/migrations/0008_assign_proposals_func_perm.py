# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from django.contrib.auth.models import User, Group
from farmbase.models import FunctionModule, FunctionPermission

def assign_proposals_func_perm(apps, schema_editor):
    func_module, created = FunctionModule.objects.get_or_create(name='需求',
                                                                codename='proposals')
    permission = FunctionPermission.objects.filter(codename='assign_proposals')
    if permission.exists():
        permission = permission.first()
        permission.name = '需求分配'
        permission.module = func_module
        permission.save()
    else:
        permission, created = FunctionPermission.objects.get_or_create(codename='assign_proposals',
                                                                       module=func_module,
                                                                       name='需求分配')

    permission.users.clear()
    permission.groups.clear()
    users = User.objects.filter(groups__name='需求分配', is_active=True)
    permission.users.add(*users)
    Group.objects.filter(name='需求分配').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('farmbase', '0007_assign_func_perms'),
    ]

    operations = [
        migrations.RunPython(assign_proposals_func_perm, migrations.RunPython.noop),
    ]
