# Generated by Django 2.0 on 2018-12-13 17:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0086_auto_20181118_0035'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='project',
            name='expected_at',
        ),
        migrations.RemoveField(
            model_name='project',
            name='start_at',
        ),
    ]
