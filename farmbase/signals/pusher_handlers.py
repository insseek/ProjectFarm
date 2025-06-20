from copy import deepcopy

from django.dispatch.dispatcher import receiver
from django.conf import settings
from django.db.models.signals import pre_init, post_init, pre_save, post_save, pre_delete, post_delete
from crum import get_current_request
#
from notifications.tasks import send_pusher_message

from projects.models import Project, DeliveryDocument, ProjectContract, ProjectPrototype, \
    ProjectGanttChart, GanttRole, GanttTaskCatalogue, GanttTaskTopic, JobPosition, \
    PrototypeCommentPoint, TechnologyCheckpoint, ProjectStage
from comments.models import Comment


def isinstance_of_classes(obj, class_list: list):
    for i in class_list:
        if isinstance(obj, i):
            return True
    return False


# 前端页面实时推送开始
# 1、项目甘特图、测试甘特图、设计甘特图、开发者端的项目甘特图

def send_project_gantt_update_message(project):
    project_id = project.id
    channel = 'project-{project_id}-gantt'.format(project_id=project_id)
    event = 'data-updated'
    message = None
    send_pusher_message_with_request_top_user(channel, event, message)


def send_test_gantt_update_message():
    channel = 'test-gantt'
    event = 'data-updated'
    message = None
    send_pusher_message_with_request_top_user(channel, event, message)


def send_design_gantt_update_message():
    channel = 'design-gantt'
    event = 'data-updated'
    message = None
    send_pusher_message_with_request_top_user(channel, event, message)


@receiver(post_save)
def project_gantt_update_signal(sender, instance, created, **kwargs):
    if isinstance_of_classes(instance, [GanttTaskTopic, GanttTaskCatalogue, GanttRole]):
        project = instance.project
        send_project_gantt_update_message(project)
        if isinstance_of_classes(instance, [GanttTaskTopic, GanttRole]):
            if instance.role_type == 'test':
                send_test_gantt_update_message()
            elif instance.role_type == 'designer':
                send_design_gantt_update_message()


@receiver(post_delete)
def project_gantt_delete_signal(sender, instance, **kwargs):
    if isinstance_of_classes(instance, [GanttTaskTopic, GanttTaskCatalogue, GanttRole]):
        project = instance.project
        send_project_gantt_update_message(project)
        if isinstance_of_classes(instance, [GanttTaskTopic, GanttRole]):
            if instance.role_type == 'test':
                send_test_gantt_update_message()
            elif instance.role_type == 'designer':
                send_design_gantt_update_message()


# 1、项目甘特图、测试甘特图、设计甘特图、开发者端的项目甘特图 结束
#
# 2、项目进度页面开始


def send_projects_schedules_update_message():
    channel = 'projects-schedules'
    event = 'data-updated'
    message = None
    send_pusher_message_with_request_top_user(channel, event, message)


@receiver(post_save)
def projects_schedules_update(sender, instance, created, **kwargs):
    if isinstance(instance, ProjectStage):
        if not instance.project.is_done:
            send_projects_schedules_update_message()


@receiver(post_save, sender=Comment)
def projects_schedules_comments_update(sender, instance, created, **kwargs):
    if created and instance.codename == 'schedule_remarks':
        send_projects_schedules_update_message()


# 2、项目进度页面结束


# 3、项目原型开始
def send_project_prototype_update_message(prototype):
    prototype_uid = prototype.uid
    channel = 'prototype-{prototype_uid}'.format(prototype_uid=prototype_uid)
    event = 'new-comments'
    message = None
    send_pusher_message_with_request_top_user(channel, event, message)


def send_pusher_message_with_request_top_user(channel, event, message):
    request = get_current_request()
    top_user = getattr(request, 'top_user', None)
    top_user_id = top_user.id if top_user else None
    send_pusher_message.delay(channel, event, message, top_user_id)


#
@receiver(post_save, sender=PrototypeCommentPoint)
def project_prototype_update_signal(sender, instance, created, **kwargs):
    prototype = instance.prototype
    send_project_prototype_update_message(prototype)


#
#
@receiver(post_delete, sender=PrototypeCommentPoint)
def project_prototype_delete_signal(sender, instance, **kwargs):
    prototype = instance.prototype
    send_project_prototype_update_message(prototype)


#
#
@receiver(post_save, sender=Comment)
def projects_schedules_comment_update(sender, instance, created, **kwargs):
    if created and isinstance(instance.content_object, PrototypeCommentPoint):
        prototype = instance.content_object.prototype
        send_project_prototype_update_message(prototype)


#
#
@receiver(post_delete, sender=Comment)
def projects_schedules_comment_delete(sender, instance, **kwargs):
    if isinstance(instance.content_object, PrototypeCommentPoint):
        prototype = instance.content_object.prototype
        send_project_prototype_update_message(prototype)


# 3、项目原型结束

# 4、TPM看板开始

def send_no_tpm_projects_message():
    channel = 'no-tpm-projects'
    event = 'data-updated'
    message = None
    send_pusher_message_with_request_top_user(channel, event, message)


def send_technology_checkpoints_message():
    channel = 'technology-checkpoints'
    event = 'data-updated'
    message = None
    send_pusher_message_with_request_top_user(channel, event, message)


@receiver(post_init, sender=Project)
def save_project_origin_instance(sender, instance, **kwargs):
    instance.origin_instance = deepcopy(instance)


@receiver(post_save, sender=Project)
def project_set_tpm(sender, instance, created, **kwargs):
    if created:
        if not instance.tpm_id:
            send_no_tpm_projects_message()
    else:
        origin_instance = getattr(instance, 'origin_instance', None)
        if origin_instance and not origin_instance.tpm_id and instance.tpm_id:
            send_no_tpm_projects_message()


@receiver(post_save, sender=TechnologyCheckpoint)
def projects_technology_checkpoints_update(sender, instance, created, **kwargs):
    send_technology_checkpoints_message()

# 4、TPM看板结束


# 前端页面实时推送结束
