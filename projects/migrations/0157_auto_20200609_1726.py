# Generated by Django 2.0 on 2020-06-09 17:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0156_data_migrate_projects_technology_checkpoints_quip_document_ids'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gantttasktopic',
            name='dev_done_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='工程师完成时间'),
        ),
        migrations.AlterField(
            model_name='gantttasktopic',
            name='is_dev_done',
            field=models.BooleanField(default=False, verbose_name='工程师已完成'),
        ),
    ]
