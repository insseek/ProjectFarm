# Generated by Django 2.0 on 2020-05-06 18:05

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import multiselectfield.db.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('clients', '0042_auto_20200416_1635'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClientInfo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('address', models.CharField(blank=True, max_length=150, null=True, verbose_name='客户地址')),
                ('company_name', models.CharField(blank=True, max_length=64, null=True, verbose_name='公司名称')),
                ('company_description', models.TextField(verbose_name='公司简介')),
                ('contact_name', models.CharField(blank=True, max_length=20, null=True, verbose_name='联系人姓名')),
                ('contact_job', models.CharField(blank=True, max_length=20, null=True, verbose_name='联系人职位')),
                ('phone_number', models.CharField(blank=True, max_length=30, null=True, verbose_name='联系方式')),
                ('client_background', models.CharField(choices=[('0', '个人'), ('1', '初创团队'), ('2', '传统企业'), ('3', '大型/上市公司'), ('4', '互联网公司事业部'), ('5', '其他')], max_length=2, verbose_name='客户背景')),
                ('client_background_remarks', models.CharField(blank=True, max_length=64, null=True, verbose_name='客户背景备注')),
                ('contact_role', models.CharField(choices=[('0', '对接人'), ('1', '决策人'), ('2', '中间人')], max_length=2, verbose_name='联系人角色')),
                ('decision_making_capacity', models.CharField(choices=[('0', '只收集信息向上级汇报'), ('1', '拥有一定决策能力')], max_length=2, verbose_name='决策能力')),
                ('technical_capacity', models.CharField(choices=[('0', '懂产品技术，能力还行'), ('1', '不太懂，觉得自己懂'), ('2', '不懂，且知道自己不懂')], max_length=2, verbose_name='技术能力')),
                ('communication_cost', multiselectfield.db.fields.MultiSelectField(choices=[('0', '易于沟通和说服'), ('1', '较强势'), ('2', '逻辑性强，条理清楚'), ('3', '逻辑混乱'), ('4', '抠细节，有些事儿')], max_length=9, verbose_name='沟通成本')),
                ('rebate', models.CharField(choices=[('0', '渠道介绍，需要分成'), ('1', '内部成员，但需要返点'), ('2', '不需要返点')], max_length=2, verbose_name='返点')),
                ('rebate_proportion', models.IntegerField(blank=True, null=True, verbose_name='返点比例')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('modified_at', models.DateTimeField(auto_now=True, verbose_name='修改时间')),
                ('company', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='client_infos', to='clients.LeadOrganization', verbose_name='企业客户')),
                ('lead', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='client_info', to='clients.Lead', verbose_name='线索')),
                ('submitter', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='submitted_client_infos', to=settings.AUTH_USER_MODEL, verbose_name='提交人')),
            ],
            options={
                'verbose_name': '客户信息',
            },
        ),
    ]
