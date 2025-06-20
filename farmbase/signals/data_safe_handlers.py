from django.db.models.signals import pre_delete

from clients.models import Lead
from farmbase.models import User
from projects.models import Project
from proposals.models import Proposal


def isinstance_of_classes(obj, class_list: list):
    for i in class_list:
        if isinstance(obj, i):
            return True
    return False


@receiver(pre_delete)
def intercept_instance_pre_delete(sender, instance, **kwargs):
    class_list = [User, Lead, Proposal, Project]
    if isinstance_of_classes(instance, class_list):
        raise Exception("不允许删除")
