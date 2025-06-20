from __future__ import unicode_literals
from django.db import migrations


def migrate_notifications_is_read(apps, schema_editor):
    Notification = apps.get_model("notifications", "Notification")
    Notification.objects.filter(read_at__isnull=False).update(is_read=True)


class Migration(migrations.Migration):
    dependencies = [
        ('notifications', '0002_auto_20191101_1713'),
    ]

    operations = [
        migrations.RunPython(migrate_notifications_is_read, migrations.RunPython.noop),
    ]
