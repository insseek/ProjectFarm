from __future__ import unicode_literals

from django.db import migrations
from django.contrib.auth.models import User


def create_token(apps, schema_editor):
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('farmbase', '0005_merge_20171215_1231'),
    ]

    operations = [
        migrations.RunPython(create_token, migrations.RunPython.noop),
    ]
