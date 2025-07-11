# Generated by Django 2.0 on 2019-11-01 17:13

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('developers', '0024_developer_refuse_new_job_reason'),
        ('notifications', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='notification',
            options={'ordering': ['-created_at'], 'verbose_name': '消息通知'},
        ),
        migrations.AddField(
            model_name='notification',
            name='developer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='developers.Developer', verbose_name='开发者'),
        ),
        migrations.AddField(
            model_name='notification',
            name='is_read',
            field=models.BooleanField(default=False, verbose_name='已阅读'),
        ),
        migrations.AlterField(
            model_name='notification',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL, verbose_name='用户'),
        ),
    ]
