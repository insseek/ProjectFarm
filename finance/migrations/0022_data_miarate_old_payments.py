from __future__ import unicode_literals

from django.db import migrations, models


def data_migrate_old_payments(apps, schema_editor):
    Porject = apps.get_model("projects", "Project")
    AgileDevelopmentSprint = apps.get_model("projects", "AgileDevelopmentSprint")
    Schedule = apps.get_model("projects", "Schedule")
    JobPosition = apps.get_model("projects", "JobPosition")
    JobContract = apps.get_model("finance", "JobContract")
    JobPayment = apps.get_model("finance", "JobPayment")

    job_positions = JobPosition.objects.all()
    for job_position in job_positions:
        if job_position.pay:
            project_name = job_position.project.name
            contract_name = '{}-工程师合同'.format(project_name)

            schedule = Schedule.objects.filter(project_id=job_position.project.id).first()
            develop_date_start = schedule.dev_start_time if schedule.dev_start_time else job_position.project.created_at.strftime(
                "%Y-%m-%d")
            develop_date_end = schedule.dev_completion_time if schedule.dev_completion_time else job_position.project.done_at
            develop_days = job_position.period * 7 if job_position.period else 0
            develop_sprint = AgileDevelopmentSprint.objects.filter(project_id=job_position.project.id).count()
            contract = JobContract.objects.filter(job_position_id=job_position.id, is_null_contract=True).first()
            if not contract:
                contract = JobContract.objects.create(
                    job_position_id=job_position.id,
                    is_null_contract=True,
                    status='signed',
                    contract_name=contract_name,
                    contract_money=job_position.pay,
                    sign_date=job_position.created_at,
                    develop_days=develop_days,
                    develop_date_start=develop_date_start,
                    develop_date_end=develop_date_end,
                    develop_sprint=develop_sprint,
                    remit_way='',
                    project_results_show='',
                )
                contract.created_at = job_position.created_at
                contract.save()
            JobPayment.objects.filter(position_id=job_position.id).update(job_contract=contract)


class Migration(migrations.Migration):
    dependencies = [
        ('finance', '0023_auto_20201126_1850'),
    ]

    operations = [
        migrations.AlterField(
            model_name='jobcontract',
            name='contract_name',
            field=models.CharField(verbose_name='合同名字', max_length=64),
        ),
        migrations.RunPython(data_migrate_old_payments, migrations.RunPython.noop),
    ]
