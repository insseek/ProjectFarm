# Generated by Django 2.0 on 2021-01-19 18:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0055_client'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lead',
            name='invalid_remarks',
            field=models.TextField(blank=True, null=True, verbose_name='关闭备注'),
        ),
    ]
