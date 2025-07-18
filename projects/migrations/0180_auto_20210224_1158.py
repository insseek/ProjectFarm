# Generated by Django 2.2.14 on 2021-03-02 17:02

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0179_data_migrate_proposal_bd_to_project_bd'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='end_date',
            field=models.DateField(blank=True, null=True, verbose_name='项目结束日期'),
        ),
        migrations.AddField(
            model_name='project',
            name='start_date',
            field=models.DateField(blank=True, null=True, verbose_name='项目启动日期'),
        ),
        migrations.CreateModel(
            name='ProjectStage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stage_type', models.CharField(choices=[('prd', '原型'), ('design', '设计'), ('development', '开发'), ('test', '测试'), ('acceptance', '验收')], max_length=20, verbose_name='阶段类型')),
                ('name', models.CharField(max_length=50, verbose_name='阶段名称')),
                ('start_date', models.DateField(verbose_name='开始日期')),
                ('end_date', models.DateField(verbose_name='确认日期')),
                ('index', models.IntegerField(default=0, verbose_name='位置')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True, verbose_name='项目日程表修改时间')),
                ('gantt_chart_built', models.BooleanField(default=False, verbose_name='已初始化甘特图任务')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='project_stages', to='projects.Project', verbose_name='项目')),
            ],
            options={
                'verbose_name': '项目阶段表',
            },
        ),
        migrations.AddField(
            model_name='gantttaskcatalogue',
            name='project_stage',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='gantt_chart_catalogues', to='projects.ProjectStage', verbose_name='项目阶段'),
        ),
        migrations.AddField(
            model_name='technologycheckpoint',
            name='project_stage',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='technology_checkpoints', to='projects.ProjectStage', verbose_name='项目阶段'),
        ),
    ]
