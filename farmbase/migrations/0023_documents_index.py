# Generated by Django 2.0 on 2021-01-18 17:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('farmbase', '0022_team_teamuser'),
    ]

    operations = [
        migrations.AddField(
            model_name='documents',
            name='index',
            field=models.IntegerField(default=0, verbose_name='排序位置'),
        ),
    ]
