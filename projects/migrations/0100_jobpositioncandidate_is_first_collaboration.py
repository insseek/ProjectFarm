# Generated by Django 2.0 on 2019-04-26 11:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0099_migrate_all_prototype_comment_points_page_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='jobpositioncandidate',
            name='is_first_collaboration',
            field=models.NullBooleanField(verbose_name='第一次合作'),
        ),
    ]
