# Generated by Django 2.0 on 2020-07-10 14:52

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0157_auto_20200609_1726'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='milestone',
            name='project',
        ),
        migrations.RemoveField(
            model_name='phase',
            name='project',
        ),
        migrations.DeleteModel(
            name='Milestone',
        ),
        migrations.DeleteModel(
            name='Phase',
        ),
    ]
