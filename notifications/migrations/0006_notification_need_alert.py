# Generated by Django 2.0 on 2020-02-17 14:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0005_notification_sender'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='need_alert',
            field=models.BooleanField(default=False, verbose_name='需要弹窗提示'),
        ),
    ]
