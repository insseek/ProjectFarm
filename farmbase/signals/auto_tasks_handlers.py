import logging
from copy import deepcopy
from datetime import datetime, timedelta

from django.contrib.contenttypes.models import ContentType
from django.dispatch.dispatcher import receiver
from django.db.models.signals import pre_init, post_init, pre_save, post_save, pre_delete, post_delete, \
    m2m_changed, pre_migrate, pre_migrate
from django.utils import timezone
from crum import get_current_request

from clients.models import Lead
from projects.models import Project, JobPosition, JobPositionNeed, JobPositionCandidate, JobReferenceScore, \
    JobStandardScore, GradeQuestionnaire
from proposals.models import Proposal
from tasks.models import Task
from finance.models import ProjectPayment, ProjectPaymentStage, JobPayment
from tasks.auto_task_utils import build_project_position_star_rating_auto_tasks, create_lead_new_task_auto_task, \
    create_proposal_new_task_auto_task


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
#     ('regular_contract_payment', '固定工程师合同'),
# )


@receiver(post_init)
def save_project_proposal_lead_objs_origin_instance(sender, instance, **kwargs):
    class_list = [Project, Proposal, Lead, JobPositionNeed]
    if isinstance_of_classes(instance, class_list):
        instance.origin_instance = deepcopy(instance)


def isinstance_of_classes(obj, class_list: list):
    for i in class_list:
        if isinstance(obj, i):
            return True
    return False


# ('lead_new_task', '线索新任务')
# 1、该线索已有1个或更多任务 则自动完成
# 2、线索状态为非前期沟通 则自动完成 ok
@receiver(post_save, sender=Lead)
def auto_close_lead_new_task_lead_close(sender, instance, created, **kwargs):
    if created:
        create_lead_new_task_auto_task(instance)
    else:
        if instance.status != 'contact':
            instance.auto_tasks.filter(is_done=False, task_type="lead_new_task").update(
                is_done=True,
                done_at=timezone.now()
            )


# ('proposal_new_task', '需求新任务'),
# 1、该需求已有1个或更多任务 则自动完成  ok
# 2、线索状态为非前期沟通 则自动完成
# ('lead_new_task', '线索新任务')
# 1、该线索已有1个或更多任务 则自动完成 ok
@receiver(post_save, sender=Task)
def auto_close_obj_new_task_new_task(sender, instance, created, **kwargs):
    if created and instance.task_type not in ['lead_new_task', 'proposal_new_task']:
        obj = instance.content_object
        if isinstance(obj, Lead):
            obj.auto_tasks.filter(is_done=False, task_type="lead_new_task").update(is_done=True, done_at=timezone.now())
        elif isinstance(obj, Proposal):
            obj.auto_tasks.filter(is_done=False, task_type="proposal_new_task").update(is_done=True,
                                                                                       done_at=timezone.now())


# ('proposal_contact', '需求初次联系'),
# 1、该需求状态不是等待沟通 则自动完成 ok
# ('proposal_new_task', '需求新任务'),
# 1、该需求已有1个或更多任务 则自动完成
# 2、线索状态为非前期沟通 则自动完成 ok
@receiver(post_save, sender=Proposal)
def auto_close_proposal_new_task_proposal_close(sender, instance, created, **kwargs):
    if created:
        create_proposal_new_task_auto_task(instance)
    else:
        if instance.closed_at:
            instance.auto_tasks.filter(is_done=False, task_type="proposal_new_task").update(is_done=True,
                                                                                            done_at=timezone.now())

        if instance.status != instance.PROPOSAL_STATUS_DICT['contact']['status']:
            instance.auto_tasks.filter(is_done=False, task_type="proposal_contact").update(is_done=True,
                                                                                           done_at=timezone.now())


# ('project_payment', '项目收款'),
# 触发 项目的合同已经到了预计收款日期，但仍未收到款
# 自动完成
# 1、项目收款正常完成、异常 ok
# 2、项目收款阶段修改了预计收款日期
# 3、项目收款阶段收款信息已填写
@receiver(post_save, sender=ProjectPayment)
def auto_close_project_payment_task_project_payment(sender, instance, created, **kwargs):
    if not created:
        if instance.status != 'process':
            instance.stages_auto_tasks(is_done=False).filter(task_type="project_payment").update(is_done=True,
                                                                                                 done_at=timezone.now())


# ('project_payment', '项目收款'),
# 触发 项目的合同已经到了预计收款日期，但仍未收到款
# 自动完成
# 1、项目收款正常完成、异常
# 2、项目收款阶段修改了预计收款日期 ok
# 3、项目收款阶段收款信息已填写 ok
@receiver(post_save, sender=ProjectPaymentStage)
def auto_close_project_payment_task_project_payment_stage(sender, instance, created, **kwargs):
    if not created:
        auto_tasks = instance.auto_tasks.filter(is_done=False, task_type="project_payment")
        if auto_tasks.count():
            if instance.receipted_amount:
                auto_tasks.update(is_done=True, done_at=timezone.now())
            elif instance.expected_date and instance.expected_date > timezone.now().date():
                auto_tasks.update(is_done=True, done_at=timezone.now())


# ('regular_contract_payment', '固定工程师合同')
# 触发 合同中打款项已经到了期望日期前1天，但仍未启动
# 自动完成
# 1、合同中打款项已启动
# 2、合同中打款项修改了预计收款日期
@receiver(post_save, sender=JobPayment)
def auto_close_contract_payment_task_regular_contract_payment(sender, instance, created, **kwargs):
    if not created and instance.job_contract and instance.job_contract.contract_category == 'regular':
        auto_tasks = instance.auto_tasks.filter(is_done=False, task_type="regular_contract_payment")
        if auto_tasks.count():
            if instance.status != 0:
                auto_tasks.update(is_done=True, done_at=timezone.now())
            elif instance.expected_at and instance.expected_at > timezone.now().date() + timedelta(days=1):
                auto_tasks.update(expected_at=instance.expected_at)


# ('project_position_candidate', '项目职位需求候选人'),
# 自动完成
#   已确认、已拒绝、未选择 ok
#   需求被取消、已确认
@receiver(post_save, sender=JobPositionCandidate)
def auto_close_project_position_candidate_task_candidate(sender, instance, created, **kwargs):
    if not created:
        auto_tasks = instance.auto_tasks.filter(is_done=False, task_type="project_position_candidate")
        if auto_tasks.count():
            if instance.status != 0:
                auto_tasks.update(is_done=True, done_at=timezone.now())


# ('project_position_candidate', '项目职位需求候选人'),
# 自动完成
#   已确认、已拒绝、未选择
#   需求被取消、已确认 ok
@receiver(post_save, sender=JobPositionNeed)
def auto_close_project_position_candidate_task_position_need(sender, instance, created, **kwargs):
    if not created:
        if instance.status != 0:
            instance.candidates_auto_tasks(is_done=False).filter(task_type="project_position_candidate").update(
                is_done=True,
                done_at=timezone.now()
            )


# 截止日期修改
#     需求预计日期修改，任务截止期修改
@receiver(post_save, sender=JobPositionNeed)
def auto_tasks_project_position_need_expected_date(sender, instance, created, **kwargs):
    if not created:
        if instance.expected_date != instance.origin_instance.expected_date:
            instance.candidates_auto_tasks(is_done=False).filter(task_type="project_position_candidate").update(
                expected_at=instance.expected_date,
            )


# ('project_position_star_rating', '项目职位评分'),
# 自动完成
#     已经进行最终评分 ok
#     负责人进行参考评分 且未标准评分 且不是该项目项目经理（项目经理的评分任务 只有在有了最终评分才能关闭）
#     开发职位被删除
# 自动删除
#     负责人已离职
#     项目人员变动
@receiver(post_save, sender=JobStandardScore)
def auto_close_project_position_star_rating_task_standard_score(sender, instance, created, **kwargs):
    job_position = instance.job_position
    job_position.auto_tasks.filter(
        is_done=False,
        task_type="project_position_star_rating"
    ).update(is_done=True, done_at=timezone.now())


# ('project_position_star_rating', '项目职位评分'),
# 自动完成
#     已经进行最终评分
#     负责人进行参考评分 且未标准评分 且不是该项目项目经理（项目经理的评分任务 只有在有了最终评分才能关闭）  ok
#     开发职位被删除
# 自动删除
#     项目人员变动
@receiver(post_save, sender=JobReferenceScore)
def auto_close_project_position_star_rating_task_reference_score(sender, instance, created, **kwargs):
    if created:
        job_position = instance.job_position
        project = instance.job_position.project
        manager = project.manager
        if instance.score_person_id != manager.id:
            job_position.auto_tasks.filter(
                is_done=False,
                task_type="project_position_star_rating",
                principal=instance.score_person,
            ).update(is_done=True, done_at=timezone.now())


# 项目职位评分人跳过评分任务也自动完成
@receiver(post_save, sender=GradeQuestionnaire)
def auto_close_project_position_star_rating_task_reference_score(sender, instance, created, **kwargs):
    if created:
        job_position = instance.job_position
        project = instance.job_position.project
        manager = project.manager
        if instance.score_person_id != manager.id and instance.is_skip_grade:
            job_position.auto_tasks.filter(
                is_done=False,
                task_type="project_position_star_rating",
                principal=instance.score_person,
            ).update(is_done=True, done_at=timezone.now())


# ('project_position_star_rating', '项目职位评分'),
# 自动完成
#     已经进行最终评分
#     负责人进行参考评分 且未标准评分 且不是该项目项目经理（项目经理的评分任务 只有在有了最终评分才能关闭）
#     开发职位被删除
# 自动删除
#     项目人员变动 ok
@receiver(post_save, sender=Project)
def auto_close_project_position_star_rating_task_project_members_change(sender, instance, created, **kwargs):
    if not created:
        origin = instance.origin_instance
        for field_name in Project.NEED_STAR_RATING_MEMBERS_FIELDS:
            if field_name == 'tests':
                continue
            origin_member = getattr(origin, field_name, None)
            member = getattr(instance, field_name, None)
            if origin_member != member:
                if instance.need_star_rating:
                    build_project_position_star_rating_auto_tasks(instance)


@receiver(post_save, sender=Project)
def auto_tasks_principal_change_project(sender, instance, created, **kwargs):
    if not created:
        origin = instance.origin_instance
        if origin.manager != instance.manager:
            principal = instance.manager
            instance.undone_tasks().filter(
                task_type__in=("project_position_candidate", "project_payment")
            ).update(
                principal=principal,
            )


@receiver(post_save, sender=Lead)
def auto_tasks_principal_change_lead(sender, instance, created, **kwargs):
    if not created:
        origin = instance.origin_instance
        if origin.salesman != instance.salesman:
            principal = instance.salesman
            instance.undone_tasks().filter(
                task_type__in=("lead_new_task",)
            ).update(
                principal=principal,
            )


@receiver(post_save, sender=Proposal)
def auto_tasks_principal_change_proposal(sender, instance, created, **kwargs):
    if not created:
        origin = instance.origin_instance
        if origin.bd != instance.bd:
            principal = instance.bd
            instance.undone_tasks().filter(
                task_type__in=("proposal_new_task", 'proposal_contact')
            ).update(
                principal=principal,
            )


@receiver(post_save, sender=Project)
def auto_change_project_position_star_rating_task_project_end_date(sender, instance, created,
                                                                   **kwargs):
    if not created:
        origin = instance.origin_instance
        project = instance
        if origin.end_date != instance.end_date:
            today = timezone.now().date()
            expected_at = project.end_date - timedelta(days=1)
            create_date = project.end_date - timedelta(days=5)
            if today < create_date:
                project.undone_tasks().filter(task_type="project_position_star_rating").delete()
            else:
                project.undone_tasks().filter(task_type="project_position_star_rating").update(
                    expected_at=expected_at)
