# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import migrations


def data_migrate_developers_payment_info(apps, schema_editor):
    Developer = apps.get_model("developers", "Developer")
    developers = Developer.objects.all()
    for developer in developers:
        if not developer.payee_opening_bank:
            if developer.payment_info:
                developer.payee_opening_bank = developer.payment_info
                developer.save()


class Migration(migrations.Migration):
    dependencies = [
        ('developers', '0049_auto_20201218_1328'),
    ]
    operations = [
        migrations.RunPython(data_migrate_developers_payment_info, migrations.RunPython.noop),
    ]
