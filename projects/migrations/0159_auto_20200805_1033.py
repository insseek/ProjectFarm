# Generated by Django 2.0 on 2020-08-05 10:33

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0158_auto_20200710_1452'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='statuscomment',
            name='author',
        ),
        migrations.RemoveField(
            model_name='statuscomment',
            name='project',
        ),
        migrations.RemoveField(
            model_name='project',
            name='client',
        ),
        migrations.DeleteModel(
            name='StatusComment',
        ),
    ]
