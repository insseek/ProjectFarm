# Generated by Django 2.0 on 2019-03-05 19:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('proposals', '0034_data_migrate_proposals_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='proposal',
            name='status',
            field=models.IntegerField(choices=[(1, '等待认领'), (2, '等待沟通'), (3, '等待报告'), (4, '进行中'), (5, '商机'), (6, '成单交接'), (10, '成单'), (11, '未成单')], default=1, verbose_name='需求状态'),
        ),
    ]
