from __future__ import unicode_literals
from django.db import migrations


def migrate_checkpoint_codename(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0110_checkpoint_codename'),
    ]

    operations = [
        migrations.RunPython(migrate_checkpoint_codename, migrations.RunPython.noop),
    ]
