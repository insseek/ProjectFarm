# Generated by Django 2.0 on 2020-12-18 13:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('developers', '0048_auto_20201126_1850'),
    ]

    operations = [
        migrations.AlterField(
            model_name='developer',
            name='payee_opening_bank',
            field=models.TextField(blank=True, null=True, verbose_name='收款人开户行'),
        ),
    ]
