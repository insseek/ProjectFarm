# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2018-06-06 13:47
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contenttypes', '0002_remove_content_type_name'),
        ('logs', '0007_auto_20180413_1450'),
    ]

    operations = [
        migrations.CreateModel(
            name='BrowsingHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('object_id', models.PositiveIntegerField()),
                ('ip_address', models.CharField(blank=True, max_length=100, null=True, verbose_name='IP地址')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='开始时间')),
                ('done_at', models.DateTimeField(blank=True, null=True, verbose_name='结束时间')),
                ('browsing_seconds', models.IntegerField(blank=True, null=True, verbose_name='浏览秒数')),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='browsing_histories', to='contenttypes.ContentType')),
                ('visitor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='browsing_histories', to=settings.AUTH_USER_MODEL, verbose_name='浏览者')),
            ],
            options={
                'verbose_name': '操作记录',
                'ordering': ['-created_at'],
            },
        ),
    ]
