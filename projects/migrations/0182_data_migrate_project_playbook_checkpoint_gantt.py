from datetime import timedelta, datetime

from django.db import migrations
from playbook.utils import migrate_projects_playbook, build_project_playbook_cache_data


def data_migrate_project_playbook_checkpoint_gantt(apps, schema_editor):
    Project = apps.get_model('projects', 'Project')
    ProjectGanttChart = apps.get_model('projects', 'ProjectGanttChart')
    TechnologyCheckpoint = apps.get_model('projects', 'TechnologyCheckpoint')
    ProjectStage = apps.get_model('projects', 'ProjectStage')

    for gantt in ProjectGanttChart.objects.all():
        if gantt.template_init_status == 'initialized':
            ProjectStage.objects.filter(project_id=gantt.project_id).update(gantt_chart_built=True)

    for p in Project.objects.all():
        project_id = p.id

        stages = ProjectStage.objects.filter(project_id=project_id).order_by('index')
        prd_stage = stages.filter(stage_type='prd').order_by('index').first()
        dev_stages = stages.filter(stage_type='development').order_by('index')

        checkpoints = TechnologyCheckpoint.objects.filter(project_id=project_id)
        for index, dev_stage in enumerate(dev_stages):
            sprint_flag = 'Sprint {}'.format(index + 1)
            checkpoints.filter(flag=sprint_flag).update(project_stage=dev_stage)
        if prd_stage:
            checkpoints.filter(name__in=['制定开发方案', '详细开发计划排期']).update(project_stage=prd_stage)
    '''
    生成新的项目阶段后，将项目阶段与原来的playbook关联
    注意：有多个开发阶段的， 第一个开发阶段与当前playbook中开发阶段关联。
        对于其他开发阶段：
            如果项目在进行中，且本开发阶段未完成，则为其生成新的playbook任务；
            否则：绑定一个空的playbook开发阶段
    
    Playbok模板中sprint任务修改为一次性任务
    '''
    migrate_projects_playbook()


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0181_data_migrate_project_schedule_to_project_stage'),
        ('playbook', '0024_auto_20210302_1702'),
    ]

    operations = [
        migrations.RunPython(data_migrate_project_playbook_checkpoint_gantt, migrations.RunPython.noop),
    ]
