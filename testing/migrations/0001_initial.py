# Generated by Django 2.0 on 2020-07-08 16:46

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth_top', '0003_auto_20200619_1302'),
        ('projects', '0157_auto_20200609_1726'),
    ]

    operations = [
        migrations.CreateModel(
            name='Bug',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('index', models.IntegerField(default=0, verbose_name='排序位置')),
                ('title', models.CharField(max_length=50, verbose_name='标题')),
                ('description', models.TextField(verbose_name='描述')),
                ('priority', models.CharField(choices=[('P0', 'P0'), ('P1', 'P1'), ('P2', 'P2'), ('P3', 'P3')], max_length=10, verbose_name='优先级')),
                ('bug_type', models.CharField(choices=[('function', '功能'), ('ui', 'UI'), ('requirement', '需求'), ('api', '接口'), ('performance', '性能'), ('other', '其他')], max_length=25, verbose_name='bug类型')),
                ('status', models.CharField(choices=[('pending', '待修复'), ('fixed', '已修复'), ('confirmed', '修复关闭'), ('closed', '无效关闭')], default='pending', max_length=15, verbose_name='状态')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('closed_at', models.DateTimeField(blank=True, null=True, verbose_name='关闭时间')),
                ('assignee', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assignee_bugs', to='auth_top.TopUser', verbose_name='分配人')),
                ('closed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='closed_bugs', to='auth_top.TopUser', verbose_name='关闭人')),
                ('creator', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_bugs', to='auth_top.TopUser', verbose_name='创建人')),
                ('fixed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='fixed_bugs', to='auth_top.TopUser', verbose_name='修复人')),
            ],
            options={
                'verbose_name': '项目Bug',
            },
        ),
        migrations.CreateModel(
            name='ProjectPlatform',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('creator', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='creator_project_platforms', to='auth_top.TopUser', verbose_name='创建人')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='platforms', to='projects.Project', verbose_name='项目')),
            ],
            options={
                'verbose_name': '项目平台',
            },
        ),
        migrations.CreateModel(
            name='ProjectTag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('index', models.IntegerField(default=0, verbose_name='排序位置')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('creator', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='creator_test_tags', to='auth_top.TopUser', verbose_name='创建人')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='test_tags', to='projects.Project', verbose_name='项目')),
            ],
            options={
                'verbose_name': '项目测试标签',
            },
        ),
        migrations.CreateModel(
            name='ProjectTestCase',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', '待评审'), ('approved', '通过'), ('rejected', '驳回')], default='pending', max_length=15, verbose_name='状态')),
                ('description', models.TextField(verbose_name='描述')),
                ('precondition', models.TextField(blank=True, null=True, verbose_name='前置条件')),
                ('expected_result', models.TextField(verbose_name='预期结果')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True, verbose_name='可用的')),
                ('creator', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='creator_project_test_cases', to='auth_top.TopUser', verbose_name='创建人')),
            ],
            options={
                'verbose_name': '项目用例',
            },
        ),
        migrations.CreateModel(
            name='ProjectTestCaseLibrary',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('project', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='test_case_library', to='projects.Project', verbose_name='项目')),
            ],
            options={
                'verbose_name': '项目用例库',
            },
        ),
        migrations.CreateModel(
            name='ProjectTestCaseModule',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='名称')),
                ('index', models.IntegerField(default=0, verbose_name='排序位置')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('creator', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='creator_project_test_case_modules', to='auth_top.TopUser', verbose_name='创建人')),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='testing.ProjectTestCaseModule', verbose_name='父级模块')),
                ('platforms', models.ManyToManyField(related_name='test_case_modules', to='testing.ProjectPlatform', verbose_name='平台')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='test_case_modules', to='projects.Project', verbose_name='项目')),
            ],
            options={
                'verbose_name': '项目用例模块',
            },
        ),
        migrations.CreateModel(
            name='ProjectTestPlan',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('index', models.IntegerField(default=0, verbose_name='序号')),
                ('status', models.CharField(choices=[('ongoing', '进行中'), ('done', '已完成')], default='ongoing', max_length=15, verbose_name='状态')),
                ('environment', models.TextField(verbose_name='测试环境')),
                ('remarks', models.TextField(blank=True, null=True, verbose_name='备注')),
                ('full_volume_test', models.BooleanField(default=False, verbose_name='全量测试')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('done_at', models.DateTimeField(blank=True, null=True, verbose_name='完成时间')),
                ('creator', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='creator_project_test_plans', to='auth_top.TopUser', verbose_name='创建人')),
                ('platform', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='test_plans', to='testing.ProjectPlatform', verbose_name='平台')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='test_plans', to='projects.Project', verbose_name='项目')),
            ],
            options={
                'verbose_name': '项目测试计划',
            },
        ),
        migrations.CreateModel(
            name='TestCase',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', '待评审'), ('approved', '通过'), ('rejected', '驳回')], default='pending', max_length=15, verbose_name='状态')),
                ('description', models.TextField(verbose_name='描述')),
                ('precondition', models.TextField(blank=True, null=True, verbose_name='前置条件')),
                ('expected_result', models.TextField(verbose_name='预期结果')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True, verbose_name='可用的')),
                ('creator', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='creator_test_cases', to='auth_top.TopUser', verbose_name='创建人')),
            ],
            options={
                'verbose_name': '用例',
            },
        ),
        migrations.CreateModel(
            name='TestCaseLibrary',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True, verbose_name='名称')),
                ('description', models.TextField(verbose_name='描述')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('creator', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='test_case_libraries', to='auth_top.TopUser', verbose_name='创建人')),
            ],
            options={
                'verbose_name': '用例库',
            },
        ),
        migrations.CreateModel(
            name='TestCaseModule',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='名称')),
                ('index', models.IntegerField(default=0, verbose_name='排序位置')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('creator', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='creator_test_case_modules', to='auth_top.TopUser', verbose_name='创建人')),
                ('library', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='modules', to='testing.TestCaseLibrary', verbose_name='用例库')),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='testing.TestCaseModule', verbose_name='父级模块')),
            ],
            options={
                'verbose_name': '用例模块',
            },
        ),
        migrations.CreateModel(
            name='TestPlanCase',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', '进行中'), ('pass', '通过'), ('failed', '失败'), ('closed', '未执行')], default='pending', max_length=15, verbose_name='状态')),
                ('description', models.TextField(verbose_name='描述')),
                ('precondition', models.TextField(blank=True, null=True, verbose_name='前置条件')),
                ('expected_result', models.TextField(verbose_name='预期结果')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('closed_at', models.DateTimeField(blank=True, null=True, verbose_name='关闭时间')),
                ('case', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='plan_cases', to='testing.ProjectTestCase', verbose_name='项目用例')),
                ('creator', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='creator_plan_cases', to='auth_top.TopUser', verbose_name='创建人')),
                ('executor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='executor_plan_cases', to='auth_top.TopUser', verbose_name='执行人')),
            ],
            options={
                'verbose_name': '测试计划的用例',
            },
        ),
        migrations.CreateModel(
            name='TestPlanModule',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='名称')),
                ('index', models.IntegerField(default=0, verbose_name='排序位置')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('creator', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='creator_test_plan_modules', to='auth_top.TopUser', verbose_name='创建人')),
                ('module', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='plan_modules', to='testing.ProjectTestCaseModule', verbose_name='项目用例模块')),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='testing.TestPlanModule', verbose_name='父级模块')),
                ('plan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='plan_modules', to='testing.ProjectTestPlan', verbose_name='测试计划')),
            ],
            options={
                'verbose_name': '测试计划的模块',
            },
        ),
        migrations.AddField(
            model_name='testplancase',
            name='module',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='plan_cases', to='testing.TestPlanModule', verbose_name='模块'),
        ),
        migrations.AddField(
            model_name='testplancase',
            name='plan',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='plan_cases', to='testing.ProjectTestPlan', verbose_name='测试计划'),
        ),
        migrations.AddField(
            model_name='testplancase',
            name='project',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='plan_cases', to='projects.Project', verbose_name='项目'),
        ),
        migrations.AddField(
            model_name='testplancase',
            name='tags',
            field=models.ManyToManyField(related_name='plan_cases', to='testing.ProjectTag', verbose_name='标签'),
        ),
        migrations.AddField(
            model_name='testcase',
            name='module',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='test_cases', to='testing.TestCaseModule', verbose_name='模块'),
        ),
        migrations.AddField(
            model_name='projecttestcase',
            name='module',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='test_cases', to='testing.ProjectTestCaseModule', verbose_name='模块'),
        ),
        migrations.AddField(
            model_name='projecttestcase',
            name='platforms',
            field=models.ManyToManyField(related_name='test_cases', to='testing.ProjectPlatform', verbose_name='平台'),
        ),
        migrations.AddField(
            model_name='projecttestcase',
            name='project',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='test_cases', to='projects.Project', verbose_name='项目'),
        ),
        migrations.AddField(
            model_name='projecttestcase',
            name='tags',
            field=models.ManyToManyField(related_name='test_cases', to='testing.ProjectTag', verbose_name='标签'),
        ),
        migrations.AddField(
            model_name='bug',
            name='module',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='bugs', to='testing.ProjectTestCaseModule', verbose_name='模块'),
        ),
        migrations.AddField(
            model_name='bug',
            name='plan_case',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='bugs', to='testing.TestPlanCase', verbose_name='用例执行'),
        ),
        migrations.AddField(
            model_name='bug',
            name='platform',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bugs', to='testing.ProjectPlatform', verbose_name='平台'),
        ),
        migrations.AddField(
            model_name='bug',
            name='project',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bugs', to='projects.Project', verbose_name='项目'),
        ),
        migrations.AddField(
            model_name='bug',
            name='tags',
            field=models.ManyToManyField(related_name='bugs', to='testing.ProjectTag', verbose_name='标签'),
        ),
        migrations.AlterUniqueTogether(
            name='projecttag',
            unique_together={('project', 'name')},
        ),
        migrations.AlterUniqueTogether(
            name='projectplatform',
            unique_together={('project', 'name')},
        ),
    ]
