# -*- coding:utf-8 -*-
from __future__ import absolute_import, unicode_literals
from django.contrib.contenttypes.models import ContentType
from celery import shared_task

from playbook.models import ChecklistItem, InfoItem, Stage, CheckItem, LinkItem
from playbook.utils import get_project_playbook_templates_data, get_proposal_playbook_templates_data
from projects.models import Project
from proposals.models import Proposal
from playbook.utils import update_ongoing_project_playbook, update_ongoing_proposal_playbook, \
    update_existing_object_playbook, build_proposal_playbook_cache_data, build_project_playbook_cache_data


# Update existing projects and proposals and add new playbook items
@shared_task
def update_ongoing_project_proposal_existing_playbook(model_name=None, member_type=None):
    if model_name == 'project':
        update_ongoing_project_playbook(member_type=member_type)
    elif model_name == 'proposal':
        update_ongoing_proposal_playbook(member_type=member_type)
    else:
        update_ongoing_project_playbook(member_type=member_type)
        update_ongoing_proposal_playbook(member_type=member_type)


@shared_task
def update_project_playbook(project):
    project_templates = get_project_playbook_templates_data()
    project_type = ContentType.objects.get(app_label="projects", model="project")
    update_existing_object_playbook(project, project_templates, project_type)


@shared_task
def update_proposal_playbook(proposal, reset_current_status=False):
    proposal_templates = get_proposal_playbook_templates_data()
    proposal_type = ContentType.objects.get(app_label="proposals", model="proposal")
    update_existing_object_playbook(proposal, proposal_templates, proposal_type,
                                    reset_current_status=reset_current_status)


@shared_task
def rebuild_playbook_template_cache_data():
    build_proposal_playbook_cache_data()
    build_project_playbook_cache_data()
