# Generated by Django 2.0 on 2020-07-08 16:46

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('farmbase', '0020_auto_20191007_0228'),
    ]

    operations = [
        migrations.DeleteModel(
            name='UrlPermission',
        ),
        migrations.RemoveField(
            model_name='functionpermission',
            name='urls',
        ),
    ]
