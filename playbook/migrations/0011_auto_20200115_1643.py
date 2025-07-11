# Generated by Django 2.0 on 2020-01-17 14:28

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('playbook', '0010_update_existing_proposals_playbook'),
    ]

    operations = [
        migrations.CreateModel(
            name='Template',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('template_type', models.CharField(choices=[('proposal', '需求Playbook'), ('project', '项目Playbook')], max_length=15, verbose_name='模板类型')),
                ('version', models.CharField(blank=True, default='1.0', max_length=10, null=True, verbose_name='当前版本')),
                ('status', models.CharField(choices=[('draft', '草稿'), ('online', '线上版本'), ('history', '历史版本')], default='draft', max_length=15, verbose_name='状态')),
                ('is_active', models.BooleanField(default=True, verbose_name='删除状态')),
                ('remarks', models.CharField(blank=True, max_length=64, null=True, verbose_name='备注')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('published_at', models.DateTimeField(blank=True, null=True, verbose_name='发布时间')),
                ('creator', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='create_playbook_templates', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
                ('last_operator', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='last_edit_playbook_templates', to=settings.AUTH_USER_MODEL, verbose_name='最近编辑人')),
                ('publisher', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='publish_playbook_templates', to=settings.AUTH_USER_MODEL, verbose_name='发布人')),
            ],
            options={
                'verbose_name': 'Playbook模板',
            },
        ),
        migrations.CreateModel(
            name='TemplateCheckGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.TextField(verbose_name='描述')),
                ('index', models.IntegerField(verbose_name='位置')),
            ],
            options={
                'verbose_name': 'Playbook模板检查项组',
                'ordering': ['index'],
            },
        ),
        migrations.CreateModel(
            name='TemplateCheckItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(blank=True, max_length=20, null=True, verbose_name='类型')),
                ('period', models.CharField(choices=[('once', '一次性任务'), ('weekly', '每周任务'), ('sprint', 'Sprint任务')], default='once', max_length=15, verbose_name='周期')),
                ('description', models.TextField(verbose_name='描述')),
                ('index', models.IntegerField(verbose_name='位置')),
                ('template_check_group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='check_items', to='playbook.TemplateCheckGroup')),
            ],
            options={
                'verbose_name': 'Playbook模板检查项',
                'ordering': ['index'],
            },
        ),
        migrations.CreateModel(
            name='TemplateInfoItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.TextField(verbose_name='描述')),
                ('index', models.IntegerField(verbose_name='位置')),
                ('template_check_item', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='info_items', to='playbook.TemplateCheckItem')),
            ],
            options={
                'verbose_name': 'Playbook模板任务注意项',
                'ordering': ['index'],
            },
        ),
        migrations.CreateModel(
            name='TemplateLinkItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=68, verbose_name='名称')),
                ('url', models.CharField(max_length=81, verbose_name='链接地址')),
                ('index', models.IntegerField(verbose_name='位置')),
                ('template_check_item', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='links', to='playbook.TemplateCheckItem')),
            ],
            options={
                'verbose_name': 'Playbook模板任务链接',
                'ordering': ['index'],
            },
        ),
        migrations.CreateModel(
            name='TemplateStage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='阶段名称')),
                ('index', models.IntegerField(verbose_name='位置')),
                ('status', models.IntegerField(blank=True, null=True, verbose_name='对应项目状态')),
                ('playbook_template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stages', to='playbook.Template', verbose_name='Playbook模板')),
            ],
            options={
                'verbose_name': 'Playbook模板阶段',
                'ordering': ['index'],
            },
        ),
        migrations.AlterModelOptions(
            name='checkitem',
            options={'ordering': ['index'], 'verbose_name': 'Playbook检查项'},
        ),
        migrations.AlterModelOptions(
            name='checklistitem',
            options={'ordering': ['index'], 'verbose_name': 'Playbook检查项组'},
        ),
        migrations.AlterModelOptions(
            name='infoitem',
            options={'ordering': ['index'], 'verbose_name': 'Playbook注意项'},
        ),
        migrations.AlterModelOptions(
            name='linkitem',
            options={'ordering': ['index'], 'verbose_name': '链接'},
        ),
        migrations.AlterModelOptions(
            name='stage',
            options={'ordering': ['index'], 'verbose_name': 'Playbook阶段'},
        ),
        migrations.RenameField(
            model_name='checkitem',
            old_name='position',
            new_name='index',
        ),
        migrations.RenameField(
            model_name='checklistitem',
            old_name='position',
            new_name='index',
        ),
        migrations.RenameField(
            model_name='infoitem',
            old_name='position',
            new_name='index',
        ),
        migrations.RenameField(
            model_name='linkitem',
            old_name='position',
            new_name='index',
        ),
        migrations.RenameField(
            model_name='stage',
            old_name='position',
            new_name='index',
        ),
        migrations.RemoveField(
            model_name='checklistitem',
            name='content_type',
        ),
        migrations.RemoveField(
            model_name='checklistitem',
            name='object_id',
        ),
        migrations.RemoveField(
            model_name='checklistitem',
            name='status',
        ),
        migrations.RemoveField(
            model_name='infoitem',
            name='stage',
        ),
        migrations.RemoveField(
            model_name='infoitem',
            name='status',
        ),
        migrations.AddField(
            model_name='checkitem',
            name='period',
            field=models.CharField(choices=[('once', '一次性任务'), ('weekly', '每周任务'), ('sprint', 'Sprint任务')], default='once', max_length=15, verbose_name='周期'),
        ),
        migrations.AlterField(
            model_name='stage',
            name='status',
            field=models.IntegerField(blank=True, null=True, verbose_name='对应项目状态'),
        ),
        migrations.AddField(
            model_name='templatecheckgroup',
            name='template_stage',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='check_groups', to='playbook.TemplateStage'),
        ),
    ]
