# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

def copy_mail_subject_title(apps, schema_editor):
    EmailTemplate = apps.get_model("gearmail", "EmailTemplate")
    for email_template in EmailTemplate.objects.all():
        email_template.title = email_template.subject
        email_template.save()

class Migration(migrations.Migration):

    dependencies = [
        ('gearmail', '0008_auto_20180309_1132'),
    ]

    operations = [
        migrations.RunPython(copy_mail_subject_title, migrations.RunPython.noop),
    ]
# -*- coding:utf-8 -*-