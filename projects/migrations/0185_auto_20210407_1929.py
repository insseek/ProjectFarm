# Generated by Django 2.2.14 on 2021-04-07 19:29

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0184_delete_projectpayment'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='schedule',
            name='project',
        ),
        migrations.DeleteModel(
            name='AgileDevelopmentSprint',
        ),
        migrations.DeleteModel(
            name='Schedule',
        ),
    ]
