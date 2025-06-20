# -*- coding:utf-8 -*-
from __future__ import absolute_import, unicode_literals
from datetime import datetime, timedelta

from django.utils import timezone
from celery import shared_task

from clients.models import Lead
from finance.models import ProjectPayment, JobContract
from projects.models import Project
from proposals.models import Proposal
from tasks.models import Task
from tasks.auto_task_utils import create_lead_new_task_auto_task, create_proposal_new_task_auto_task, \
    create_proposal_contact_auto_task, create_project_payment_auto_task, build_project_position_star_rating_auto_tasks, \
    create_regular_contract_payment_auto_task


# 每天定时扫描创建、并清理自动任务
# 每天零点定时扫描
#     自动任务【线索新任务】如果绑定的线索不是非前期沟通状态 则自动完成
#     自动任务【线索新任务】如果绑定的线索有其他任务 则自动完成
#     自动任务【线索新任务】负责人和线索BD不一致 修改负责人为线索BD
# 每天零点定时扫描  前期沟通的线索  如果没有任务安排 则创建 自动任务【线索新任务】
@shared_task
def leads_auto_tasks_lead_new_task():
    undone_tasks = Task.undone_tasks().filter(task_type='lead_new_task')
    for task in undone_tasks:
        content_object = task.content_object
        if content_object.status != 'contact':
            task.done_at = timezone.now()
            task.is_done = True
            task.save()
        elif content_object.undone_tasks().exclude(task_type='lead_new_task').count():
            task.done_at = timezone.now()
            task.is_done = True
            task.save()
        elif task.principal != content_object.salesman:
            task.principal = content_object.salesman
            task.save()
    pending_leads = Lead.pending_leads()
    for obj in pending_leads:
        if not len(obj.undone_tasks()):
            create_lead_new_task_auto_task(obj)


# 每天零点定时扫描
#     自动任务【线索新任务】如果绑定的线索不是非前期沟通状态 则自动完成
#     自动任务【线索新任务】如果绑定的线索有其他任务 则自动完成
#     自动任务【线索新任务】负责人和线索BD不一致 修改负责人为线索BD
# 每天零点定时扫描  前期沟通的线索  如果没有任务安排 则创建 自动任务【线索新任务】
@shared_task
def proposals_auto_tasks_lead_new_task():
    new_task_undone_tasks = Task.undone_tasks().filter(task_type='proposal_new_task')
    for task in new_task_undone_tasks:
        content_object = task.content_object
        if content_object.closed_at:
            task.done_at = timezone.now()
            task.is_done = True
            task.save()
        elif content_object.undone_tasks().exclude(task_type='proposal_new_task').count():
            task.done_at = timezone.now()
            task.is_done = True
            task.save()
        elif task.principal != content_object.bd:
            task.principal = content_object.bd
            task.save()

    proposal_contact_undone_tasks = Task.undone_tasks().filter(task_type='proposal_contact')
    for task in proposal_contact_undone_tasks:
        content_object = task.content_object
        if content_object.status != Proposal.PROPOSAL_STATUS_DICT['contact']['status']:
            task.done_at = timezone.now()
            task.is_done = True
            task.save()
        elif task.principal != content_object.bd:
            task.principal = content_object.bd
            task.save()

    for obj in Proposal.ongoing_proposals():
        if not len(obj.undone_tasks()):
            create_proposal_new_task_auto_task(obj)

    for obj in Proposal.waiting_contact_proposals():
        if not obj.auto_tasks.filter(task_type='proposal_contact', is_done=False).count():
            expected_at = obj.assigned_at.date() + timedelta(days=1)
            create_proposal_contact_auto_task(obj, expected_at=expected_at)


# 项目收款 自动创建任务、修改、清理无效自动任务
# # 每天零点定时扫描
#     已有自动任务【项目收款】处理
#         如果所关联的项目收款已完成、阶段已收款、则自动完成
#         所关联的项目收款阶段已修改日期  则任务修改日期
#         项目经理和任务负责人不一致，修改负责人为项目项目经理
#     则创建 自动任务【项目收款】
#         进行中的项目收款，其中未收款的收款阶段，已经到了预计收款日期，但仍未收到款
#         则创建 自动任务【项目收款】
@shared_task
def project_payments_auto_tasks():
    undone_tasks = Task.undone_tasks().filter(task_type='project_payment')
    for task in undone_tasks:
        stage = task.source_object
        payment = stage.project_payment
        project = payment.project

        if stage.receipted_amount:
            task.done_at = timezone.now()
            task.is_done = True
            task.save()
            continue
        if payment.status != 'process':
            task.done_at = timezone.now()
            task.is_done = True
            task.save()
            continue

        if stage.expected_date >= timezone.now().date():
            task.expected_at = stage.expected_date
            task.save()

        if project.manager_id != task.principal_id:
            task.principal_id = project.manager_id
            task.save()

    payments = ProjectPayment.process_project_payments()
    for payment in payments:
        for stage in payment.stages.all():
            if stage.receipted_amount:
                continue
            if stage.expected_date and timezone.now().date() >= stage.expected_date:
                if not stage.auto_tasks.filter(is_done=False, task_type="project_payment").count():
                    create_project_payment_auto_task(stage)


# 固定工程师合同打款 自动创建任务、修改、清理无效自动任务
# # 每天零点定时扫描
#     已有自动任务【固定工程师合同打款】处理
#         所关联的固定工程师合同打款已修改日期  则任务修改日期
#         所关联的固定工程师合同打款已启动  则任务修改日期
#     则创建 自动任务【项目收款】
#         进行中的项目收款，其中未收款的收款阶段，已经到了预计收款日期，但仍未收到款
#         则创建 自动任务【项目收款】
@shared_task
def regular_contract_payments_auto_tasks():
    undone_tasks = Task.undone_tasks().filter(task_type='regular_contract_payment')
    for task in undone_tasks:
        source_object = task.source_object
        if source_object.status != 0:
            task.done_at = timezone.now()
            task.is_done = True
            task.save()
            continue
        if source_object.expected_at and source_object.expected_at > timezone.now().date() + timedelta(days=1):
            task.expected_at = source_object.expected_at
            task.save()
            continue
    queryset = JobContract.signed_regular_contracts()
    for obj in queryset:
        for payment in obj.payments.filter(status=0):
            if payment.expected_at and payment.expected_at <= timezone.now().date() + timedelta(days=1):
                if not payment.auto_tasks.filter(is_done=False, task_type="regular_contract_payment").count():
                    create_regular_contract_payment_auto_task(payment)


@shared_task
def project_position_star_rating_auto_tasks():
    projects = Project.ongoing_projects()
    for project in projects:
        # 所有职位已评分
        if not len(project.need_star_rating_job_positions):
            project.undone_tasks().filter(task_type="project_position_star_rating").delete()
            continue
        # 创建任务 、重新构造任务
        create_date = project.end_date - timedelta(days=5)
        if timezone.now().date() >= create_date:
            build_project_position_star_rating_auto_tasks(project)
        else:
            project.undone_tasks().filter(task_type="project_position_star_rating").delete()


@shared_task
def build_auto_tasks():
    leads_auto_tasks_lead_new_task()
    proposals_auto_tasks_lead_new_task()
    project_payments_auto_tasks()
    project_position_star_rating_auto_tasks()
    regular_contract_payments_auto_tasks()
