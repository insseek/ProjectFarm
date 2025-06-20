import logging
from copy import deepcopy

from django.dispatch.dispatcher import receiver
from django.db.models.signals import pre_init, post_init, pre_save, post_save, pre_delete, post_delete, \
    m2m_changed, pre_migrate, pre_migrate
from crum import get_current_request

from testing.models import TestCaseLibrary, TestCaseModule, TestCase, ProjectTestCaseLibrary, ProjectPlatform, \
    ProjectTag, ProjectTestCaseModule, ProjectTestCase, ProjectTestPlan, TestPlanCase, Bug, Project
from logs.models import Log


# Gear Test的操作记录开始
def isinstance_of_classes(obj, class_list: list):
    for i in class_list:
        if isinstance(obj, i):
            return True
    return False


@receiver(post_init)
def save_test_objs_origin_instance(sender, instance, **kwargs):
    if isinstance_of_test_models(instance):
        instance.origin_instance = deepcopy(instance)


def isinstance_of_test_models(obj):
    class_list = [TestCaseLibrary, TestCaseModule, TestCase, ProjectTestCaseLibrary, ProjectPlatform, ProjectTag,
                  ProjectTestCaseModule, ProjectTestCase, ProjectTestPlan, TestPlanCase, Bug]
    if isinstance_of_classes(obj, class_list):
        return True


# model的删除记录
@receiver(post_delete)
def build_instance_delete_log(sender, instance, **kwargs):
    request = get_current_request()
    top_user = getattr(request, 'top_user') if request else None
    if not top_user:
        return
    if isinstance_of_classes(instance, [TestCaseModule, TestCase]):
        Log.build_delete_object_log(top_user, instance, related_object=instance.library)
    elif isinstance_of_classes(instance, [ProjectPlatform, ProjectTag, ProjectTestCaseModule,
                                          ProjectTestCase]):
        project = instance.project
        test_case_library, library_created = ProjectTestCaseLibrary.objects.get_or_create(project=project)
        Log.build_delete_object_log(top_user, instance, related_object=test_case_library)


@receiver(post_save, sender=TestCase)
def create_project_test_case_library(sender, instance, created, **kwargs):
    if not created:
        request = get_current_request()
        top_user = getattr(request, 'top_user') if request else None
        if not top_user:
            return
        origin = instance.origin_instance
        if origin.is_active and not instance.is_active:
            test_case_library = instance.library
            Log.build_delete_object_log(top_user, instance, related_object=test_case_library)


@receiver(post_save, sender=ProjectTestCase)
def create_project_test_case_library(sender, instance, created, **kwargs):
    if not created:
        request = get_current_request()
        top_user = getattr(request, 'top_user') if request else None
        if not top_user:
            return
        origin = instance.origin_instance
        if origin.is_active and not instance.is_active:
            project = instance.project
            test_case_library, library_created = ProjectTestCaseLibrary.objects.get_or_create(project=project)
            Log.build_delete_object_log(top_user, instance, related_object=test_case_library)


# model的删除记录结束


# model的创建更新记录
@receiver(post_save)
def build_instance_log(sender, instance, created, **kwargs):
    request = get_current_request()
    top_user = getattr(request, 'top_user') if request else None
    if not top_user:
        return
    related_object = None
    #  删除的不记录
    if isinstance_of_classes(instance, [TestCase, ProjectTestCase]):
        if not instance.is_active:
            return
    if isinstance_of_classes(instance, [TestCaseModule, TestCase]):
        related_object = instance.library
    elif isinstance_of_classes(instance, [ProjectPlatform, ProjectTag, ProjectTestCaseModule,
                                          ProjectTestCase]):
        project = instance.project
        test_case_library, library_created = ProjectTestCaseLibrary.objects.get_or_create(project=project)
        related_object = test_case_library
    elif isinstance(instance, ProjectTestPlan):
        related_object = instance
    elif isinstance(instance, TestPlanCase):
        related_object = instance.plan
    elif isinstance(instance, Bug):
        related_object = instance
    else:
        return

    if created:
        Log.build_create_object_log(request.top_user, instance, related_object=related_object)
    else:
        Log.build_update_object_log(request.top_user, instance.origin_instance, instance,
                                    related_object=related_object)


# model的创建更新记录结束

# Test
@receiver(post_save, sender=Project)
def create_project_test_case_library(sender, instance, created, **kwargs):
    if created:
        ProjectTestCaseLibrary.objects.create(project=instance)

# Gear Test的操作记录结束
