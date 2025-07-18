# Generated by Django 2.0 on 2019-10-17 17:06

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0020_merge_20190827_1255'),
        ('reports', '0031_quotationplan_position'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='report',
            name='user_visible',
        ),
        migrations.AddField(
            model_name='report',
            name='lead',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reports', to='clients.Lead', verbose_name='线索'),
        ),
        migrations.AddField(
            model_name='report',
            name='meeting_participants',
            field=models.TextField(blank=True, null=True, verbose_name='参会人员'),
        ),
        migrations.AddField(
            model_name='report',
            name='meeting_place',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='会议地点'),
        ),
        migrations.AddField(
            model_name='report',
            name='meeting_time',
            field=models.DateTimeField(blank=True, null=True, verbose_name='会议时间'),
        ),
        migrations.AddField(
            model_name='report',
            name='report_type',
            field=models.CharField(choices=[('proposal', '需求报告'), ('lead', '线索报告')], default='proposal', max_length=20, verbose_name='报告分类'),
        ),
        migrations.AddField(
            model_name='report',
            name='show_company_about',
            field=models.BooleanField(default=True, verbose_name='关于我们'),
        ),
        migrations.AddField(
            model_name='report',
            name='show_company_clients',
            field=models.BooleanField(default=True, verbose_name='我们的客户'),
        ),
    ]
