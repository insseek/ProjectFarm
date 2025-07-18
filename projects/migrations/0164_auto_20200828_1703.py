# Generated by Django 2.0 on 2020-08-28 17:03

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('auth_top', '0004_topuser_client'),
        ('projects', '0163_data_migrate_projects_calendars_ui_links'),
    ]

    operations = [
        migrations.AddField(
            model_name='prototypecommentpoint',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='创建时间'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='prototypecommentpoint',
            name='creator',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='prototype_comment_points', to='auth_top.TopUser', verbose_name='创建人'),
        ),
        migrations.AddField(
            model_name='prototypecommentpoint',
            name='modified_at',
            field=models.DateTimeField(auto_now=True, verbose_name='修改时间'),
        ),
    ]
