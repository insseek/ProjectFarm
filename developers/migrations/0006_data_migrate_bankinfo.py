# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.management import create_permissions
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import migrations


def migrate_bank(apps, schema_editor):
    Developer = apps.get_model("developers", "Developer")
    for developer in Developer.objects.all():
        rewrite_bank_info(developer)
    

def rewrite_bank_info(developer):
    bank_info = ''
    if developer.bank_name:
        bank_info += '开户行: '
        bank_info += developer.bank_name
        bank_info += ';'
    if developer.bank_account:
        bank_info += '银行账号: '
        bank_info += developer.bank_account
        bank_info += ';'
    bank_info += developer.bank_info
    developer.bank_info = bank_info
    developer.save()


class Migration(migrations.Migration):
    dependencies = [
        ('developers', '0005_auto_20170904_1955'),
    ]
    operations = [
        migrations.RunPython(migrate_bank, migrations.RunPython.noop),
    ]
