import os
import datetime
import shutil
import logging
from copy import deepcopy

from django.dispatch.dispatcher import receiver
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from django.db.models import signals
from django.db.models.signals import post_init, post_save, post_delete

from auth_top.models import TopToken
from farmbase.models import Profile, User
from files.models import File
from finance.models import JobPayment, JobContract
from finance.utils import build_payments_for_regular_job_contract
from notifications.tasks import send_proposal_status_update_reminder, send_report_new_comment
from projects.models import Project, DeliveryDocument, ProjectContract, ProjectPrototype, JobPosition
from reports.models import Report
from reports.pdf_gen import report_path
from comments.models import Comment
from projects.tasks import create_prototype_comment_point_cache_data, create_prototype_client_comment_point_cache_data, \
    create_prototype_developer_comment_point_cache_data
from webphone.models import CallRecord
from proposals.models import Proposal


def isinstance_of_classes(obj, class_list: list):
    for i in class_list:
        if isinstance(obj, i):
            return True
    return False


@receiver(post_init)
def save_objs_origin_instance(sender, instance, **kwargs):
    class_list = [Project, Proposal, Report]
    if isinstance_of_classes(instance, class_list):
        instance.origin_instance = deepcopy(instance)


@receiver(signals.post_save, sender=JobContract)
def listen_job_contract_signed(sender, instance, created, **kwargs):
    if not created:
        if instance.status == "signed" and instance.contract_category == 'regular':
            build_payments_for_regular_job_contract(instance)


@receiver(post_save, sender=JobPosition)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        instance.project.rebuild_dev_docs_checkpoint_status()


# farmbase
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        TopToken.get_or_create(user=instance)


# file
@receiver(post_delete, sender=File)
def file_delete(sender, instance, **kwargs):
    instance.file.delete(False)


@receiver(post_save, sender=Project)
def project_members_change(sender, instance, created, **kwargs):
    if not created:
        gantt_chart = getattr(instance, 'gantt_chart', None)
        if not gantt_chart:
            return
        from projects.utils.gantt_chart_utils import rebuild_project_gantt_role
        for role_data in Project.PROJECT_MEMBERS_FIELDS:
            '''项目人员修改后 甘特图角色的名称及绑定的人员随之变化
                        项目人员修改后  自动创建新的甘特图角色
                        原项目人员   未完成的甘特图任务  自动分配给新的项目人员
                        原项目人员   已完成的甘特图任务  保持不变
                        原项目人员   如果没有任何甘特图任务   自动删除其对应的甘特图角色'''
            role_type = role_data['field_name']
            if role_type == 'mentor':
                continue
            new_member = getattr(instance, role_type, None)
            origin_member = getattr(instance.origin_instance, role_type, None)
            if new_member and new_member != origin_member:
                rebuild_project_gantt_role(instance, role_data, gantt_chart)


@receiver(post_delete, sender=DeliveryDocument)
def delivery_document_delete(sender, instance, **kwargs):
    instance.file.delete(False)


@receiver(post_delete, sender=ProjectContract)
def project_contract_delete(sender, instance, **kwargs):
    instance.file.delete(False)


# reports
@receiver(signals.post_save, sender=Report)
def delete_report_old_data(sender, instance, created, **kwargs):
    if not created:
        report = instance.origin_instance
        if report.expired_at != instance.expired_at:
            if os.path.isfile(report_path(instance.uid)):
                os.remove(report_path(instance.uid))
        if not report.is_public and instance.is_public:
            reports_data = cache.get('reports_editable_data', {})
            if instance.uid in reports_data:
                del reports_data[instance.uid]
                cache.set('reports_editable_data', reports_data, None)


@receiver(signals.post_delete, sender=Report)
def delete_report_data(sender, instance, **kwargs):
    reports_data = cache.get('reports_editable_data', {})
    if instance.uid in reports_data:
        del reports_data[instance.uid]
        cache.set('reports_editable_data', reports_data, None)
    if os.path.isfile(report_path(instance.uid)):
        os.remove(report_path(instance.uid))


@receiver(post_save, sender=Report)
def update_report_proposal_report_at(sender, instance, **kwargs):
    if instance.is_public and instance.proposal and not instance.proposal.report_at:
        instance.proposal.report_at = timezone.now()
        instance.proposal.save()


@receiver(post_delete, sender=ProjectPrototype)
def prototype_delete(sender, instance, **kwargs):
    shutil.rmtree(instance.prototype_dir(), True)
    if os.path.isfile(instance.prototype_zip_path()):
        os.remove(instance.prototype_zip_path())
    try:
        instance.file.delete(False)
    except Exception as e:
        logger = logging.getLogger()
        logger.error(e)


@receiver(post_delete, sender=Comment)
def prototype_comment_delete(sender, instance, **kwargs):
    comment_point_type = ContentType.objects.get(app_label="projects", model="prototypecommentpoint")
    if instance.content_type == comment_point_type:
        try:
            prototype = instance.content_object.prototype
            create_prototype_comment_point_cache_data.delay(prototype.id)
            create_prototype_developer_comment_point_cache_data(prototype.id)
            if instance.content_object.creator and instance.content_object.creator.is_client:
                create_prototype_client_comment_point_cache_data.delay(prototype.id)
        except:
            pass


@receiver(post_save, sender=Comment)
def prototype_comment_save(sender, instance, **kwargs):
    comment_point_type = ContentType.objects.get(app_label="projects", model="prototypecommentpoint")

    report_type = ContentType.objects.get(app_label="reports", model="report")
    if instance.content_type == comment_point_type:
        prototype = instance.content_object.prototype
        create_prototype_comment_point_cache_data.delay(prototype.id)
        create_prototype_developer_comment_point_cache_data(prototype.id)
        if instance.content_object.creator and instance.content_object.creator.is_client:
            create_prototype_client_comment_point_cache_data.delay(prototype.id)

    elif instance.content_type == report_type:
        report = instance.content_object
        send_report_new_comment.delay(report.id, instance.author_id)


@receiver(post_delete, sender=CallRecord)
def call_record_delete(sender, instance, **kwargs):
    if instance.file:
        try:
            instance.file.delete(False)
        except Exception as e:
            logger = logging.getLogger()
            logger.error(e)


# Proposal
@receiver(signals.post_save, sender=Proposal)
def listen_proposal_status_update(sender, instance, created, **kwargs):
    if not created:
        proposal = instance.origin_instance
        if proposal.status != instance.status:
            send_proposal_status_update_reminder.delay(instance.pk)


from .pusher_handlers import *
from .testing_handlers import *
from .auto_tasks_handlers import *
