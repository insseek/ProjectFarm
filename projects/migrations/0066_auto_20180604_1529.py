# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2018-06-04 15:29
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import projects.models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0065_delete_one_project_checkpoint'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProjectPrototype',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100)),
                ('version', models.CharField(default='1.0', max_length=10)),
                ('uid', models.CharField(max_length=25, verbose_name='标识码')),
                ('cipher', models.CharField(blank=True, max_length=6, null=True, verbose_name='提取码')),
                ('file', models.FileField(upload_to=projects.models.ProjectPrototype.generate_filename)),
                ('filename', models.CharField(blank=True, max_length=100, null=True, verbose_name='文件名称')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('modified_at', models.DateTimeField(auto_now=True, verbose_name='修改时间')),
                ('is_deleted', models.BooleanField(default=False, verbose_name='删除状态')),
                ('index_path', models.CharField(blank=True, max_length=200, null=True, verbose_name='index_path')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='prototypes', to='projects.Project', verbose_name='项目')),
            ],
            options={
                'verbose_name': '项目原型',
                'ordering': ['-created_at', 'title'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='projectprototype',
            unique_together=set([('project', 'title', 'version')]),
        ),
    ]
