# Generated by Django 2.0 on 2019-10-07 02:28

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('farmbase', '0019_auto_20191006_1826'),
    ]

    operations = [
        migrations.RenameField(
            model_name='profile',
            old_name='feishu_id',
            new_name='feishu_user_id',
        ),
    ]
