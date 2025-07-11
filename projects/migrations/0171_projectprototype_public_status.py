# Generated by Django 2.0 on 2020-12-23 16:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0170_auto_20201106_1609'),
    ]

    operations = [
        migrations.AddField(
            model_name='projectprototype',
            name='public_status',
            field=models.CharField(choices=[('none', '非公开'), ('client_public', '客户可见'), ('developer_public', '工程师可见'), ('public', '公开可见')], default='none', max_length=50, verbose_name='公开状态'),
        ),
    ]
