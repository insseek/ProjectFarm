# Generated by Django 2.0 on 2020-12-10 12:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0024_auto_20201203_1652'),
    ]

    operations = [
        migrations.AddField(
            model_name='jobcontract',
            name='committed_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='提交时间'),
        ),
    ]
