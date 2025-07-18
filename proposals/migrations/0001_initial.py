# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2017-03-31 14:37
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('projects', '0016_remove_task_project'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Proposal',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source', models.IntegerField(choices=[(1, '其它'), (2, '官网/搜索引擎'), (3, '口碑'), (4, '朋友介绍'), (5, '兄弟公司'), (6, '空间/孵化器')], default=1, verbose_name='需求来源')),
                ('status', models.IntegerField(choices=[(1, '等待认领'), (2, '等待第一次沟通'), (3, '等待第一次反馈'), (4, '进行中'), (5, '成单'), (6, '未成单')], default=1, verbose_name='需求状态')),
                ('closed_reason', models.IntegerField(choices=[(1, '其它'), (2, '无响应'), (3, '暂时不做'), (4, '选择其它家'), (5, '无效需求（不靠谱）')], default=1, verbose_name='未成单原因')),
                ('description', models.TextField(verbose_name='描述')),
                ('submitter_comments', models.TextField(blank=True, null=True, verbose_name='提交人备注')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='提交时间')),
                ('assigned_at', models.DateTimeField(blank=True, null=True, verbose_name='认领时间')),
                ('contact_at', models.DateTimeField(blank=True, null=True, verbose_name='联系时间')),
                ('report_at', models.DateTimeField(blank=True, null=True, verbose_name='报告时间')),
                ('closed_at', models.DateTimeField(blank=True, null=True, verbose_name='关闭时间')),
                ('pm', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='proposals', to=settings.AUTH_USER_MODEL, verbose_name='产品经理')),
                ('project', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='proposal', to='projects.Project', verbose_name='项目')),
                ('submitter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='submitted_proposals', to=settings.AUTH_USER_MODEL, verbose_name='提交人')),
            ],
        ),
    ]
