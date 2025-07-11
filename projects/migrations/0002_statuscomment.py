# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2016-11-20 09:38
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('projects', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='StatusComment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField(verbose_name='内容')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_public', models.BooleanField(default=False, verbose_name='公开')),
                ('is_warning', models.BooleanField(default=False, verbose_name='警告')),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='status_comments', to=settings.AUTH_USER_MODEL, verbose_name='作者')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='status_comments', to='projects.Project', verbose_name='项目')),
            ],
        ),
    ]
