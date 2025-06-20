# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import migrations


def data_migrate_developers_real_name_auth_status(apps, schema_editor):
    Developer = apps.get_model("developers", "Developer")
    JobContract = apps.get_model("finance", "JobContract")
    developers = Developer.objects.all()
    for developer in developers:
        job_contracts = JobContract.objects.filter(developer_id=developer.id)
        for job_contract in job_contracts:
            if job_contract.is_esign_contract and job_contract.status == 'signed':
                developer.is_real_name_auth = True
                developer.save()
                break


class Migration(migrations.Migration):
    dependencies = [
        ('developers', '0053_developer_is_real_name_auth'),
        ('finance', '0046_auto_20210408_1606'),

    ]
    operations = [
        migrations.RunPython(data_migrate_developers_real_name_auth_status, migrations.RunPython.noop),
    ]
