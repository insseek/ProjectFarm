# Generated by Django 2.0 on 2020-04-22 02:32

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0145_jobpositioncandidate_refuse_remarks'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='developerdailywork',
            name='developer',
        ),
        migrations.RemoveField(
            model_name='developerdailywork',
            name='next_day_work',
        ),
        migrations.RemoveField(
            model_name='developerdailywork',
            name='project',
        ),
        migrations.DeleteModel(
            name='DeveloperDailyWork',
        ),
    ]
