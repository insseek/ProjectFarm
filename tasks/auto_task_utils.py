from datetime import datetime, timedelta
from copy import deepcopy

from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import User
from crum import get_current_request

from tasks.models import Task
from farmbase.utils import get_protocol_host
from notifications.utils import create_notification
from projects.models import JobReferenceScore, JobStandardScore, Questionnaire
from proposals.models import Proposal


# TASK_TYPES = (
#     ('common', '普通'),
#     ('lead_new_task', '线索新任务'),
#
#     ('proposal_new_task', '需求新任务'),
#     ('proposal_contact', '需求初次联系'),
#     ('proposal_need_report', '需求需要报告'),
#
#     ('project_payment', '项目收款'),  # 项目的合同已经到了预计收款日期，但仍未收到款
#     ('project_position_need', '项目职位需求'),
#     ('project_position_candidate', '项目职位需求候选人'),
#     ('project_position_star_rating', '项目职位评分'),
# )

def close_obj_auto_tasks(obj):
    tasks = obj.undone_tasks()
    for task in tasks:
        if task.auto_close_required:
            task.done_at = timezone.now()
            task.is_done = True
            task.save()


def create_lead_new_task_auto_task(obj, expected_at=None, principal=None):
    if obj.status == 'contact' and not len(obj.undone_tasks()):
        expected_at = expected_at or timezone.now().date()
        principal = principal or obj.salesman
        Task.objects.create(
            task_type="lead_new_task",
            name="请为线索【{}】添加一个任务".format(obj.name),
            principal=principal,
            expected_at=expected_at,
            content_object=obj,
            source_object=obj  # 线索
        )


def create_proposal_new_task_auto_task(obj, expected_at=None, principal=None):
    if not obj.closed_at and not len(obj.undone_tasks()):
        expected_at = expected_at or timezone.now().date()
        principal = principal or obj.bd
        Task.objects.create(
            task_type="proposal_new_task",
            name="请为需求【{}】添加一个任务".format(obj.name),
            principal=principal,
            expected_at=expected_at,
            content_object=obj,
            source_object=obj  # 需求
        )


def create_proposal_contact_auto_task(obj, expected_at=None, principal=None):
    if obj.status == Proposal.PROPOSAL_STATUS_DICT['contact']['status']:
        if not obj.auto_tasks.filter(task_type='proposal_contact', is_done=False).count():
            expected_at = expected_at or timezone.now().date() + timedelta(days=1)
            principal = principal or obj.bd
            Task.objects.create(
                task_type="proposal_contact",
                name="请及时联系需求【{}-{}】客户".format(obj.id, obj.name),
                principal=principal,
                expected_at=expected_at,
                content_object=obj,
                source_object=obj  # 需求
            )


def create_proposal_need_report_auto_task(obj, expected_at=None, principal=None):
    expected_at = expected_at or timezone.now().date() + timedelta(days=1)
    principal = principal or obj.pm
    Task.objects.create(
        task_type="proposal_need_report",
        name="请完成需求【{}-{}】的反馈报告并发送给BD".format(obj.id, obj.name),
        principal=principal,
        expected_at=expected_at,
        content_object=obj,
        source_object=obj  # 需求
    )


def create_project_payment_auto_task(obj):
    if not obj.receipted_amount:
        if obj.expected_date and timezone.now().date() >= obj.expected_date:
            task = obj.auto_tasks.filter(is_done=False, task_type="project_payment").first()
            if not task:
                project_payment = obj.project_payment
                contract_name = project_payment.contract_name
                project = project_payment.project
                principal = project.manager
                expected_at = obj.expected_date
                Task.objects.create(
                    task_type="project_payment",
                    name="项目【{}】的合同【{}】已到预计收款日期 请确认收款情况".format(project.name, contract_name),
                    principal=principal,
                    expected_at=expected_at,
                    content_object=project,
                    source_object=obj,  # 项目收款阶段
                )
            else:
                if task.expected_at > obj.expected_date:
                    task.expected_at = obj.expected_date
                    task.save()


def create_regular_contract_payment_auto_task(obj):
    if obj.status == 0:
        if obj.expected_at and obj.expected_at <= timezone.now().date() + timedelta(days=1):
            task = obj.auto_tasks.filter(is_done=False, task_type="regular_contract_payment").first()
            if not task:
                principal = obj.job_contract.principal
                job_contract = obj.job_contract
                expected_at = obj.expected_at
                Task.objects.create(
                    task_type="regular_contract_payment",
                    name="固定工程师合同【{}】即将到期望打款时间，请确认是否打款".format(job_contract.contract_name),
                    principal=principal,
                    expected_at=expected_at,
                    content_object=obj.job_contract,
                    source_object=obj,  # 项目收款阶段
                )
            else:
                if task.expected_at > obj.expected_at:
                    task.expected_at = obj.expected_at
                    task.save()


def create_project_position_need_auto_task(obj, expected_at=None, principal=None):
    if obj.need_new_candidate:
        principals = [principal, ] if principal else User.objects.filter(
            username__in=settings.RESPONSIBLE_TPM_FOR_PROJECT_JOB_NEEDS,
            is_active=True)
        if principals:
            project = obj.project
            expected_at = expected_at or datetime.now().date() + timedelta(days=2)
            if obj.expected_date < expected_at:
                expected_at = obj.expected_date
            message_content = '请再次给项目【{project}】分配一个【{role}】，预计截止日期【{expected_at}】'.format(project=project.name,
                                                                                           role=obj.role.name,
                                                                                           expected_at=expected_at)
            request = get_current_request()
            message_url = get_protocol_host(request) + '/projects/position_needs/'
            for principal in principals:
                Task.objects.create(
                    task_type="project_position_need",
                    name="请再次给项目【{project}】分配一个【{role}】".format(project=project.name, role=obj.role.name),
                    principal=principal,
                    expected_at=expected_at,
                    content_object=project,
                    source_object=obj  # 项目工程师需求
                )
            create_notification(principal, message_content, message_url, priority="important")


def create_project_position_candidate_auto_task(obj, expected_at=None, principal=None):
    project = obj.position_need.project
    position_need = obj.position_need
    position_candidate = obj
    expected_at = expected_at or position_need.expected_date
    principal = principal or project.manager
    Task.objects.create(
        task_type="project_position_candidate",
        name="确认项目【{project}】{role}候选人：{candidate}".format(project=project.name, role=position_need.role.name,
                                                           candidate=position_candidate.developer.name),
        principal=principal,
        expected_at=expected_at,
        content_object=project,
        source_object=obj  # 项目职位需求的一个候选人
    )
    request = get_current_request()
    message_url = get_protocol_host(request) + '/projects/position_needs/mine/'
    # 发送通知给PM
    message_content = '{tpm_name}给项目【{project}】分配了一个【{role}：{developer}】；请联系【王雅宁】获取工程师联系方式'.format(
        tpm_name=request.user.username,
        project=project.name,
        role=position_need.role.name,
        developer=position_candidate.developer.name)
    create_notification(principal, message_content, message_url, priority="important")


# 给客户发进度报告邮件
def create_project_progress_report_auto_task(obj, expected_at=None, principal=None):
    # 周五
    principal = principal or obj.manager
    expected_at = expected_at or timezone.now() + timedelta((4 - timezone.now().weekday()) % 7)
    Task.objects.create(
        name="给项目【{}】客户发进度报告".format(obj.name),
        principal=principal,
        expected_at=expected_at,
        content_object=obj
    )


def create_projects_progress_report_auto_tasks(objs, expected_at=None, principal=None):
    expected_at = expected_at or timezone.now() + timedelta((4 - timezone.now().weekday()) % 7)
    for obj in objs:
        create_project_progress_report_auto_task(obj, expected_at=expected_at, principal=principal)


def build_project_position_star_rating_auto_tasks(project, expected_at=None):
    principals = project.need_star_rating_members
    expected_at = expected_at or project.end_date - timedelta(days=1)
    for obj in project.need_star_rating_job_positions:
        job_position_role = 'developer'
        if obj.role.name in '测试工程师':
            job_position_role = 'test'
        elif obj.role.name in '设计师':
            job_position_role = 'designer'
        obj.auto_tasks.filter(is_done=False, task_type="project_position_star_rating").exclude(
            principal__in=principals).delete()
        if project.is_done:
            return
        create_date = project.end_date - timedelta(days=5)
        if timezone.now().date() < create_date:
            return
        # 项目经理
        manager_task = obj.auto_tasks.filter(task_type="project_position_star_rating", principal_id=project.manager_id,
                                             is_done=False).first()
        is_grade = None
        if project.manager and project.manager in principals:
            is_grade = Questionnaire.objects.filter(written_by='manager', engineer_type=job_position_role,
                                                    status='online').first()
        if not manager_task and is_grade:
            Task.objects.create(
                task_type="project_position_star_rating",
                name="请为项目【{project}】{role}【{developer}】评分".format(project=project.name, role=obj.role.name,
                                                                   developer=obj.developer.name),
                principal=project.manager,
                expected_at=expected_at,
                content_object=project,
                source_object=obj  # 项目工程师职位
            )
        elif manager_task.expected_at != expected_at:
            manager_task.expected_at = expected_at
            manager_task.save()

            # 项目经理之外 其他成员
        other_members = deepcopy(principals)
        if project.manager in other_members:
            other_members.remove(project.manager)

        for principal in other_members:
            role = None
            if project.tests:
                for test in project.tests.all():
                    if principal == test:
                        role = 'test'
            if project.designer:
                if principal == project.designer:
                    role = 'designer'
            if project.tpm:
                if principal == project.tpm.id:
                    role = 'tpm'
            if project.product_manager:
                if principal == project.product_manager.id:
                    role = 'manager'
            questionnaire = Questionnaire.objects.filter(written_by=role, engineer_type=job_position_role,
                                                         status='online').first()
            review = JobReferenceScore.objects.filter(job_position_id=obj.id, score_person_id=principal.id).first()
            if not review and questionnaire:
                task = obj.auto_tasks.filter(task_type="project_position_star_rating", principal_id=principal.id,
                                             is_done=False).first()
                if not task:
                    Task.objects.create(
                        task_type="project_position_star_rating",
                        name="请为项目【{project}】{role}【{developer}】评分".format(project=project.name, role=obj.role.name,
                                                                           developer=obj.developer.name),
                        principal=principal,
                        expected_at=expected_at,
                        content_object=project,
                        source_object=obj  # 项目工程师职位
                    )
                elif task.expected_at != expected_at:
                    task.expected_at = expected_at
                    task.save()
