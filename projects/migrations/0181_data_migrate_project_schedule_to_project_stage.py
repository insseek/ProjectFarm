from datetime import timedelta
import logging
from django.db import migrations


def data_migrate_project_schedule_to_project_stage(apps, schema_editor):
    ProjectStage = apps.get_model('projects', 'ProjectStage')
    Schedule = apps.get_model('projects', 'Schedule')
    schedules = Schedule.objects.all()
    for schedule in schedules:
        project_id = schedule.project_id
        if not project_id:
            return
        flag = 0
        if schedule.start_time and schedule.prd_confirmation_time:
            ProjectStage.objects.create(project_id=project_id,
                                        start_date=schedule.start_time,
                                        end_date=schedule.prd_confirmation_time,
                                        stage_type='prd',
                                        index=flag,
                                        name='原型阶段')
            flag += 1
        if schedule.ui_start_time and schedule.ui_confirmation_time:
            ProjectStage.objects.create(project_id=project_id,
                                        start_date=schedule.ui_start_time,
                                        end_date=schedule.ui_confirmation_time,
                                        stage_type='design',
                                        index=flag,
                                        name='设计阶段')
            flag += 1
        sprints = schedule.development_sprints.all()
        if sprints.count() > 1:
            for index, sprint in enumerate(sprints):
                ProjectStage.objects.create(
                    project_id=project_id,
                    start_date=sprint.start_time,
                    end_date=sprint.end_time,
                    stage_type='development',
                    index=flag,
                    name='开发Sprint{}'.format(index + 1)
                )
                flag += 1
        else:
            if schedule.dev_start_time and schedule.dev_completion_time:
                ProjectStage.objects.create(project_id=project_id,
                                            start_date=schedule.dev_start_time,
                                            end_date=schedule.dev_completion_time,
                                            stage_type='development',
                                            name='开发阶段',
                                            index=flag)
                flag += 1
        if schedule.test_start_time and schedule.test_completion_time:
            ProjectStage.objects.create(project_id=project_id,
                                        start_date=schedule.test_start_time,
                                        end_date=schedule.test_completion_time,
                                        stage_type='test',
                                        index=flag,
                                        name='测试阶段')
            flag += 1
        if schedule.delivery_time:
            ProjectStage.objects.create(project_id=project_id,
                                        start_date=schedule.delivery_time,
                                        end_date=schedule.delivery_time + timedelta(days=42),
                                        stage_type='acceptance',
                                        index=flag,
                                        name='验收阶段')
        project = schedule.project
        if schedule.start_time:
            project.start_date = schedule.start_time
        elif project.created_at:
            project.start_date = project.created_at.date()
        if schedule.delivery_time:
            project.end_date = schedule.delivery_time + timedelta(days=42)  # delivery_time + 42
        elif project.done_at:
            project.end_date = project.done_at  # delivery_time + 42
        project.save()


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0180_auto_20210224_1158'),
    ]

    operations = [
        migrations.RunPython(data_migrate_project_schedule_to_project_stage, migrations.RunPython.noop),
    ]
