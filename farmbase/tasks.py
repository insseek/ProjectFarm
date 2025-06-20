from __future__ import absolute_import, unicode_literals

import time
import random
import logging
import re
from copy import deepcopy
from pprint import pprint
from itertools import chain

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.shortcuts import reverse
from django.utils import timezone
from django.utils.timezone import now, timedelta
from celery import shared_task
from tenacity import retry, wait_fixed, stop_after_attempt
import requests

from farmbase.models import Team
from farmbase.permissions_init import init_func_perms
from clients.models import Lead
from developers.models import Developer
from developers.utils import build_project_developer_daily_works_statistics, \
    get_project_developer_daily_works_statistics
from farmbase.models import FunctionPermission
from notifications.tasks import send_feishu_message_to_all, send_feishu_message_to_individual
from logs.models import Log
from notifications.utils import create_notification_group, create_notification
from projects.models import Project, PrototypeCommentPoint, ProjectGanttChart, ProjectLinks, \
    TechnologyCheckpoint
from proposals.models import Proposal
from playbook.models import CheckItem
from oauth import quip
from tasks.models import Task
from projects.tasks import create_prototype_comment_point_cache_data, create_prototype_client_comment_point_cache_data, \
    create_prototype_developer_comment_point_cache_data
from projects.serializers import GanttTaskCatalogueCleanSerializer, GanttTaskTopicCleanSerializer, \
    ProjectGanttChartRetrieveSerializer
from oauth.quip_utils import new_project_folder, new_project_engineer_contact_folder, get_project_quip_folder_template, \
    get_folders_docs
from farmbase.users_undone_works_utils import get_user_today_undone_tasks, get_user_today_work_orders_tasks
from farmbase.users_undone_works_utils import *
from tasks.auto_task_utils import *

logger = logging.getLogger()


@shared_task
def change_developer_status():
    Developer.objects.filter(expected_work_at__lte=timezone.now().date(), status="2").update(status="1")


def build_user_works_statistics(user, statistics, work_type):
    '''
    每个用户的数据
    {
        "tasks_count": len(tasks),
        "gantt_tasks_count": len(gantt_tasks),
        "playbook_tasks_count": len(playbook_tasks),
        "tpm_checkpoints_count": len(tpm_checkpoints),
        'work_orders_count': len(work_orders),
    }
    未完成任务数量：💩💩💩💩💩
    待办事项 n 个
    甘特图任务 n 个
    Playbook任务 n 个
    TPM检查点 n 个
    工单 n 个
    '''
    username = user.username
    if username not in statistics:
        statistics[username] = {
            "tasks_count": 0,
            "gantt_tasks_count": 0,
            "playbook_tasks_count": 0,
            "tpm_checkpoints_count": 0,
            'work_orders_count': 0,
        }
    statistics[username][work_type] = statistics[username][work_type] + 1
    return statistics


def get_users_today_undone_works():
    '''
    每个用户的数据
    {
        "tasks_count": len(tasks),
        "gantt_tasks_count": len(gantt_tasks),
        "playbook_tasks_count": len(playbook_tasks),
        "tpm_checkpoints_count": len(tpm_checkpoints),
        'work_orders_count': len(work_orders),
    }
    未完成任务数量：💩💩💩💩💩
    待办事项 n 个
    甘特图任务 n 个
    Playbook任务 n 个
    TPM检查点 n 个
    工单 n 个
    '''
    statistics = {}
    # 待办事项
    tasks = get_user_today_undone_tasks()
    for task in tasks:
        principal = task.principal
        if principal and principal.is_active:
            build_user_works_statistics(principal, statistics, 'tasks_count')

    # 甘特图任务
    gantt_tasks = get_user_today_undone_gantt_tasks()
    for task_topic in gantt_tasks:
        principal = task_topic.role.user if task_topic.role else None
        if principal and principal.is_active:
            build_user_works_statistics(principal, statistics, 'gantt_tasks_count')

    # 未完成的Playbook任务
    check_items = get_user_today_undone_playbook_tasks(only_expected_date=True)
    for check_item in check_items:
        stage = check_item.check_group.stage
        content_object = stage.content_object
        member_type = stage.member_type
        principal = getattr(content_object, member_type, None)
        if principal and principal.is_active:
            build_user_works_statistics(principal, statistics, 'playbook_tasks_count')

    # TPM项目检查点
    tpm_checkpoints = get_user_today_tpm_checkpoints_tasks()
    for checkpoint in tpm_checkpoints:
        principal = checkpoint.project.tpm
        if principal and principal.is_active:
            build_user_works_statistics(principal, statistics, 'tpm_checkpoints_count')

    # 工单
    work_orders = get_user_today_work_orders_tasks()
    for work_order in work_orders:
        principal = work_order.principal
        if principal and principal.is_active:
            build_user_works_statistics(principal, statistics, 'work_orders_count')
    for u in statistics:
        statistics[u]['total'] = sum(statistics[u].values())
    return statistics


USER_WORK_NAME_DICT = {
    "tasks_count": "待办事项",
    "gantt_tasks_count": "甘特图任务",
    "playbook_tasks_count": "Playbook任务",
    "tpm_checkpoints_count": 'TPM检查点',
    'work_orders_count': '工单'
}


def build_user_works_msg(statistic):
    msg = "请处理未完成任务："
    total = statistic['total']
    msg += "{}".format("💩" * total)
    for item_key in ["tasks_count", "gantt_tasks_count", "playbook_tasks_count", "tpm_checkpoints_count",
                     "work_orders_count"]:
        if item_key in statistic:
            item_value = statistic[item_key]
            if item_value:
                item_name = USER_WORK_NAME_DICT.get(item_key)
                item_msg = '{}{}个'.format(item_name, item_value)
                msg = msg + '\n' + item_msg
    return msg


def build_team_works_msg(statistics, team):
    if team.leader and team.leader.is_active:
        team_msg_title = '团队【{}】成员未完成任务：'.format(team.name)
        members_msg = []
        members = team.members
        for member in members:
            if member.is_active:
                username = member.username
                if username in statistics:
                    member_msg = '{}:{}'.format(username, "💩" * statistics[username]['total'])
                    members_msg.append(member_msg)
        if members_msg:
            members_msg.insert(0, team_msg_title)
            team_msg = '\n'.join(members_msg)
            return team_msg
    return None


@shared_task
def send_task_reminder_to_individual(forced_to_send=False):
    if not forced_to_send:
        if not settings.PRODUCTION:
            return
    statistics = get_users_today_undone_works()
    for username, statistic in statistics.items():
        user = User.objects.get(username=username)
        msg = build_user_works_msg(statistic)
        if user.profile.feishu_user_id:
            send_feishu_message_to_individual(user.profile.feishu_user_id, msg)

    #  给每个团队的leader发送自己的团队组员的今日任务
    teams = Team.objects.all()
    for team in teams:
        leader = team.leader
        team_msg = build_team_works_msg(statistics, team)
        if leader and leader.profile.feishu_user_id:
            send_feishu_message_to_individual(leader.profile.feishu_user_id, team_msg)
    return statistics


@shared_task
def send_task_reminder_to_all():
    statistics = get_users_today_undone_works()
    msg = ""
    if statistics:
        statistics = sorted(statistics.items(), key=lambda x: x[1]['total'], reverse=True)
        msg += "Farm今日未完成任务数量："
        for username, user_statistic in statistics:
            msg += "\n{username}: {task_count}".format(username=username, task_count="💩" * user_statistic['total'])
    else:
        msg += "Farm当前无未完成任务：😘"
    if settings.PRODUCTION:
        send_feishu_message_to_all(msg)
    return msg


def set_proposals_quip_folders(folders):
    folder_mapping = {}
    for f in folders:
        folder = folders[f]
        folder_title = folder["folder"]["title"].strip()
        pattern1 = re.compile("^(\d+)")
        match1 = pattern1.match(folder_title)
        pattern2 = re.compile("^【(\d+)】")
        match2 = pattern2.match(folder_title)
        if match1:
            proposal_id = match1.group()
            folder_mapping[proposal_id] = folder
        elif match2:
            proposal_id = match2.group(1)
            folder_mapping[proposal_id] = folder
    proposals = Proposal.ongoing_proposals().filter(quip_folder_id__isnull=True)
    for proposal in proposals:
        folder_content = folder_mapping.get(str(proposal.id), None)
        if folder_content:
            if not proposal.quip_folder_id:
                proposal.quip_folder_id = folder_content["folder"]["id"]
                proposal.quip_folder_type = 'auto'
                proposal.save()


# 爬取所有quip需求文件夹
@shared_task
def crawl_quip_proposals_folders():
    '''
    :return:
    {'DbUAOASzjWA': {'children': [{'thread_id': 'bVVAAAOSdpk'},
                              {'thread_id': 'IAMAAAG0Yag'}],
                 'folder': {'color': 'manila',
                            'created_usec': 1570526035292577,
                            'creator_id': 'BWMAEAUwUlv',
                            'id': 'DbUAOASzjWA',
                            'parent_id': 'HUHAOAC9xGf',
                            'title': '【2】我是需求2号',
                            'updated_usec': 1570527316726184},
                 'member_ids': []}
    }
    '''
    quip_proposals_folders = cache.get('quip_proposals_folders', {})
    ignore_quip_folders = cache.get('ignore_quip_folders', set())
    client = quip.QuipClient(settings.QUIP_TOKEN)
    parent_id = settings.QUIP_PROPOSAL_FOLDER_ID
    proposal_folder = client.get_folder(parent_id)
    children_folder_ids = []
    for child in proposal_folder["children"]:
        folder_id = child.get('folder_id', None)
        if folder_id and folder_id not in quip_proposals_folders:
            if ignore_quip_folders and folder_id in ignore_quip_folders:
                continue
            children_folder_ids.append(folder_id)
    if children_folder_ids:
        folders = client.get_folders(children_folder_ids)
        if folders:
            set_proposals_quip_folders(folders)
            quip_proposals_folders.update(folders)
    cache.set('quip_proposals_folders', quip_proposals_folders, None)
    return quip_proposals_folders


@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
def get_quip_folder_children_folders_data(parent_id, ignore=None):
    client = quip.QuipClient(settings.QUIP_TOKEN)
    try:
        project_folder = client.get_folder(parent_id)
    except Exception as e:
        logger.error("爬取quip文件夹ID({}）的子目录失败:{}".format(parent_id, str(e)))
        return
    children_folder_ids = []
    for child in project_folder["children"]:
        folder_id = child.get('folder_id', None)
        if not folder_id:
            continue
        if ignore and folder_id in ignore:
            continue
        if folder_id not in children_folder_ids:
            children_folder_ids.append(folder_id)
    if children_folder_ids:
        folders = client.get_folders(children_folder_ids)
        return folders


@shared_task
def crawl_quip_folder_children_folders_to_cache(parent_id):
    folders_dict = cache.get('quip_folder_children_folders', {})

    folders = get_quip_folder_children_folders_data(parent_id)

    folders_dict[parent_id] = folders
    cache.set('quip_folder_children_folders', folders_dict, None)
    return folders


# 爬取所有quip项目文件夹
@shared_task
def crawl_quip_projects_folders():
    quip_projects_folders = cache.get('quip_projects_folders', {})
    ignore_quip_folders = cache.get('ignore_quip_folders', set())
    parent_id = settings.QUIP_PROJECT_FOLDER_ID
    folders = get_quip_folder_children_folders_data(parent_id, ignore=ignore_quip_folders)
    if folders:
        new_folders_data = {}
        for folder_id, folder_data in folders.items():
            title = folder_data["folder"].get('title', '').lower().strip()
            if 'archive' == title or '客户档案' in title:
                ignore_quip_folders.add(folder_id)
                continue
            elif '完成项目归档' in title or '项目完成归档' in title:
                children_folders = get_quip_folder_children_folders_data(folder_id, ignore=ignore_quip_folders)
                if children_folders:
                    for key in children_folders:
                        children_folders[key]['folder']['parent_title'] = title
                    quip_projects_folders.update(children_folders)
                continue
            new_folders_data[folder_id] = folder_data
        quip_projects_folders.update(new_folders_data)
    cache.set('ignore_quip_folders', ignore_quip_folders, None)
    cache.set('quip_projects_folders', quip_projects_folders, None)
    return quip_projects_folders


# 爬取所有quip项目工程师文件夹
@shared_task
def crawl_quip_projects_engineer_folders():
    quip_projects_engineer_folders = cache.get('quip_projects_engineer_folders', {})
    ignore_quip_folders = cache.get('ignore_quip_folders', set())
    parent_id = settings.QUIP_PROJECT_ENGINEER_FOLDER_ID

    folders = get_quip_folder_children_folders_data(parent_id, ignore=ignore_quip_folders)

    if folders:
        new_folders_data = {}
        for folder_id, folder_data in folders.items():
            title = folder_data["folder"].get('title', '').lower().strip()
            if 'archive' == title or '客户档案' in title:
                ignore_quip_folders.add(folder_id)
                continue
            elif '完成项目归档' in title or '项目完成归档' in title:
                children_folders = get_quip_folder_children_folders_data(folder_id, ignore=ignore_quip_folders)
                if children_folders:
                    for key in children_folders:
                        children_folders[key]['folder']['parent_title'] = title
                    quip_projects_engineer_folders.update(children_folders)
                continue
            new_folders_data[folder_id] = folder_data
        quip_projects_engineer_folders.update(new_folders_data)
    cache.set('ignore_quip_folders', ignore_quip_folders, None)
    cache.set('quip_projects_engineer_folders', quip_projects_engineer_folders, None)
    return quip_projects_engineer_folders


@shared_task
def crawl_projects_engineer_folders_docs():
    projects = Project.ongoing_projects()
    for project in projects:
        crawl_project_engineer_contact_folder_docs(project.id)


@shared_task
def crawl_project_engineer_contact_folder_docs(project_id):
    '''
    :return:
    {'DbUAOASzjWA': {'children': [{'thread_id': 'bVVAAAOSdpk'},
                              {'thread_id': 'IAMAAAG0Yag'}],
                 'folder': {'color': 'manila',
                            'created_usec': 1570526035292577,
                            'creator_id': 'BWMAEAUwUlv',
                            'id': 'DbUAOASzjWA',
                            'parent_id': 'HUHAOAC9xGf',
                            'title': '【2】我是需求2号',
                            'updated_usec': 1570527316726184},
                 'member_ids': []}
    }
    '''
    project_links = ProjectLinks.objects.filter(project_id=project_id).first()
    if not project_links:
        return
    project = project_links.project
    try:
        quip_engineer_folder_id = project_links.quip_engineer_folder_id
        if quip_engineer_folder_id:
            quip_projects_dev_contact_docs = cache.get('quip_projects_dev_contact_docs', {})
            contact_docs = get_folders_docs(quip_engineer_folder_id)
            quip_projects_dev_contact_docs[project_links.project.id] = contact_docs
            cache.set('quip_projects_dev_contact_docs', quip_projects_dev_contact_docs, None)
    except Exception as e:
        logger.error("项目【{}】【{}】爬取Quip工程师沟通文档失败:{}".format(project.id, project.name, str(e)))


@shared_task
def crawl_ongoing_projects_tpm_folder_docs():
    for project in Project.ongoing_projects():
        crawl_project_tpm_folder_docs(project.id, rebuild=True)


@shared_task
def crawl_project_tpm_folder_docs(project_id, rebuild=False):
    '''
    :return:
    {'DbUAOASzjWA': {'children': [{'thread_id': 'bVVAAAOSdpk'},
                              {'thread_id': 'IAMAAAG0Yag'}],
                 'folder': {'color': 'manila',
                            'created_usec': 1570526035292577,
                            'creator_id': 'BWMAEAUwUlv',
                            'id': 'DbUAOASzjWA',
                            'parent_id': 'HUHAOAC9xGf',
                            'title': '【2】我是需求2号',
                            'updated_usec': 1570527316726184},
                 'member_ids': []}
    }
    '''

    project_links = ProjectLinks.objects.filter(project_id=project_id).first()
    if project_links:
        quip_projects_tpm_docs = cache.get('quip_projects_tpm_docs', {})
        if (rebuild or not project_links.quip_folder_id) and project_id in quip_projects_tpm_docs:
            quip_projects_tpm_docs.pop(project_id, None)

        project_tpm_docs = quip_projects_tpm_docs.get(project_id, {})
        quip_tpm_folder_id = project_tpm_docs.get('quip_tpm_folder_id', None)
        if not quip_tpm_folder_id:
            folder_id = project_links.quip_folder_id

            if folder_id:
                parent_id = folder_id
                folders = get_quip_folder_children_folders_data(parent_id)
                if folders:
                    for folder_id, folder_data in folders.items():
                        title = folder_data["folder"].get('title', '').lower().strip()
                        if title == 'tpm产出物':
                            quip_tpm_folder_id = folder_data["folder"].get('id', None)
        if quip_tpm_folder_id:
            docs = get_folders_docs(quip_tpm_folder_id)
            project_tpm_docs = {'quip_tpm_folder_id': quip_tpm_folder_id, 'docs': docs}
            quip_projects_tpm_docs[project_id] = project_tpm_docs
        cache.set('quip_projects_tpm_docs', quip_projects_tpm_docs, None)
        return quip_projects_tpm_docs


# 更新需求quip文件夹的名字
@shared_task
def update_quip_proposal_folder(proposal_id):
    proposal = Proposal.objects.filter(pk=proposal_id).first()
    if proposal:
        folder_id = proposal.quip_folder_id
        if folder_id:
            quip_proposals_folders = cache.get('quip_proposals_folders', {})
            title = "【{id}】{name}".format(id=proposal.id, name=proposal.name)
            folder_data = quip_proposals_folders.get(folder_id)
            if folder_data and folder_data['folder']['title'] != title:
                client = quip.QuipClient(settings.QUIP_TOKEN)
                try:
                    folder_data = client.update_folder(folder_id, title=title)
                except Exception as e:
                    logger.error("需求【{}】【{}】更新需求quip文件夹失败:{}".format(proposal.id, proposal.name, str(e)))
                    return
                if folder_data and 'folder' in folder_data:
                    quip_proposals_folders[folder_id] = folder_data
                cache.set('quip_proposals_folders', quip_proposals_folders, None)
            return folder_data


# 更新项目quip文件夹的名字
@shared_task
def update_quip_project_folder(project_id):
    project_link = ProjectLinks.objects.filter(project_id=project_id).first()

    if project_link:
        project = project_link
        title = project_link.project.name
        folder_id = project_link.quip_folder_id
        if folder_id:
            quip_projects_folders = cache.get('quip_projects_folders', {})
            folder_data = quip_projects_folders.get(folder_id)
            if not folder_data or (folder_data and folder_data['folder']['title'] != title):
                client = quip.QuipClient(settings.QUIP_TOKEN)

                try:
                    folder_data = client.update_folder(folder_id, title=title)
                except Exception as e:
                    logger.error("项目【{}】【{}】更新项目quip文件夹失败:{}".format(project.id, project.name, str(e)))
                    return
                if folder_data and 'folder' in folder_data:
                    quip_projects_folders[folder_id] = folder_data
                cache.set('quip_projects_folders', quip_projects_folders, None)
        crawl_project_tpm_folder_docs(project_id, rebuild=True)


# 更新项目工程师沟通quip文件夹名字
@shared_task
def update_quip_project_engineer_folder(project_id):
    project_link = ProjectLinks.objects.filter(project_id=project_id).first()
    if project_link:
        project = project_link.project
        engineer_folder_title = project_link.project.name + '-工程师沟通'
        engineer_folder_id = project_link.quip_engineer_folder_id
        if engineer_folder_id:
            quip_projects_engineer_folders = cache.get('quip_projects_engineer_folders', {})
            folder_data = quip_projects_engineer_folders.get(engineer_folder_id)
            if not folder_data or (folder_data and folder_data['folder']['title'] != title):
                client = quip.QuipClient(settings.QUIP_TOKEN)

                try:
                    folder_data = client.update_folder(engineer_folder_id, title=engineer_folder_title)
                except Exception as e:
                    logger.error("项目【{}】【{}】更新项目工程师沟通quip文件夹失败:{}".format(project.id, project.name, str(e)))
                    return
                if folder_data and 'folder' in folder_data:
                    quip_projects_engineer_folders[engineer_folder_id] = folder_data
                cache.set('quip_projects_engineer_folders', quip_projects_engineer_folders, None)
        crawl_project_engineer_contact_folder_docs.delay(project_id)


# 创建需求quip文件夹
@shared_task
def create_quip_proposal_folder(proposal_id):
    proposal = Proposal.objects.filter(pk=proposal_id).first()
    if proposal:
        quip_proposals_folders = cache.get('quip_proposals_folders', {})
        title = "【{id}】{name}".format(id=proposal.id, name=proposal.name)
        parent_id = settings.QUIP_PROPOSAL_FOLDER_ID
        client = quip.QuipClient(settings.QUIP_TOKEN)
        folder_data = client.new_folder(title, parent_id=parent_id)
        if folder_data and 'folder' in folder_data:
            folder_id = folder_data['folder']['id']
            quip_proposals_folders[folder_id] = folder_data
        cache.set('quip_proposals_folders', quip_proposals_folders, None)
        proposal.quip_folder_id = folder_data['folder']['id']
        proposal.save()
        return folder_data


# 创建项目quip文件夹  项目工程师文件夹
@shared_task
def create_quip_project_folder(project_id):
    project = Project.objects.filter(pk=project_id).first()
    if project:
        project_links, created = ProjectLinks.objects.get_or_create(project_id=project_id)
        if project_links.quip_folder_id:
            return
        # 项目文件夹
        title = project.name
        quip_projects_folders = cache.get('quip_projects_folders', {})
        folder_data = new_project_folder(project, title=title)
        if folder_data and 'folder' in folder_data:
            folder_id = folder_data['folder']['id']
            quip_projects_folders[folder_id] = folder_data

        cache.set('quip_projects_folders', quip_projects_folders, None)
        project_links.quip_folder_id = folder_data['folder']['id']
        # 项目沟通文件夹
        if not project_links.quip_engineer_folder_id:
            quip_projects_engineer_folders = cache.get('quip_projects_engineer_folders', {})

            engineer_folder_title = project.name + '-工程师沟通'
            engineer_folder_data = new_project_engineer_contact_folder(project, title=engineer_folder_title)
            if engineer_folder_data and 'folder' in engineer_folder_data:
                folder_id = engineer_folder_data['folder']['id']
                quip_projects_engineer_folders[folder_id] = engineer_folder_data
            cache.set('quip_projects_engineer_folders', quip_projects_engineer_folders, None)
            project_links.quip_engineer_folder_id = engineer_folder_data['folder']['id']
        project_links.save()

        quip_tpm_folder_id = folder_data.get('quip_tpm_folder_id', None)
        if quip_tpm_folder_id:
            quip_projects_tpm_docs = cache.get('quip_projects_tpm_docs', {})
            quip_projects_tpm_docs[project_id] = {'quip_tpm_folder_id': quip_tpm_folder_id, 'docs': []}
            cache.set('quip_projects_tpm_docs', quip_projects_tpm_docs, None)
            crawl_project_tpm_folder_docs(project_id)
        else:
            crawl_project_tpm_folder_docs(project_id, rebuild=True)
        return folder_data


# 已经被绑定的需求文件夹
@shared_task
def rebuild_bound_quip_proposals_folders():
    bound_folders = Proposal.objects.filter(quip_folder_id__isnull=False).values_list('quip_folder_id',
                                                                                      flat=True)
    bound_folders = set(bound_folders)
    cache.set("bound_quip_proposals_folders", bound_folders, None)
    return bound_folders


# 已经被绑定的项目文件夹
@shared_task
def rebuild_bound_quip_projects_folders():
    bound_folders = ProjectLinks.objects.filter(quip_folder_id__isnull=False).values_list('quip_folder_id',
                                                                                          flat=True)

    bound_folders = set(bound_folders)
    cache.set("bound_quip_projects_folders", bound_folders, None)
    return bound_folders


# 已经被绑定的项目工程师文件夹
@shared_task
def rebuild_bound_quip_projects_engineer_folders():
    bound_folders = ProjectLinks.objects.filter(quip_engineer_folder_id__isnull=False).values_list(
        'quip_engineer_folder_id',
        flat=True)

    bound_folders = set(bound_folders)
    cache.set("bound_quip_projects_engineer_folders", bound_folders, None)
    return bound_folders


def craw_ongoing_proposals_quip_contract_doc():
    client = quip.QuipClient(settings.QUIP_TOKEN)
    proposals = Proposal.ongoing_proposals().filter(quip_folder_id__isnull=False, quip_doc_id__isnull=True)
    folder_ids = proposals.values_list('quip_folder_id', flat=True)
    folders = client.get_folders(folder_ids)

    for proposal in proposals:
        quip_folder_id = proposal.quip_folder_id
        if quip_folder_id in folders:
            folder_content = folders[quip_folder_id]
            thread_ids = []
            children = folder_content.get("children", [])
            for child in children:
                if "thread_id" in child:
                    thread_ids.append(child["thread_id"])
            if not thread_ids:
                continue
            threads = client.get_threads(thread_ids)
            for t in threads:
                thread = threads[t]
                if thread and 'thread' in thread and "title" in thread["thread"]:
                    title = thread["thread"]["title"]
                    if title and "电话沟通准备" in title:
                        proposal.quip_doc_id = thread["thread"]["id"]
                        proposal.save()
                        break


@shared_task
def create_friday_tasks():
    projects = Project.ongoing_projects()
    friday = timezone.now() + timedelta((4 - timezone.now().weekday()) % 7)
    create_projects_progress_report_auto_tasks(projects, expected_at=friday)


@shared_task
def clear_prototype_comment_points():
    comment_points = PrototypeCommentPoint.objects.filter(comments__isnull=True)
    prototype_ids = comment_points.values_list('prototype_id', flat=True)
    for prototype_id in set(prototype_ids):
        comment_points.filter(prototype_id=prototype_ids).delete()
        create_prototype_comment_point_cache_data(prototype_id)
        create_prototype_client_comment_point_cache_data(prototype_id)
        create_prototype_developer_comment_point_cache_data(prototype_id)


@shared_task
def build_project_gantt_cache_data(gantt_id):
    if ProjectGanttChart.objects.filter(pk=gantt_id).exists():
        project_gantt = ProjectGanttChart.objects.get(pk=gantt_id)
        project_gantt_data = ProjectGanttChartRetrieveSerializer(project_gantt).data
        start_time = project_gantt_data['start_time']
        finish_time = project_gantt_data['finish_time']
        tasks = project_gantt.task_topics.all()
        catalogues = project_gantt.task_catalogues.all()
        task_data_list = GanttTaskTopicCleanSerializer(tasks, many=True).data
        catalogue_data_list = GanttTaskCatalogueCleanSerializer(catalogues, many=True).data
        task_data_dict = {}
        catalogue_data_dict = {}
        for task_data in task_data_list:
            task_data_dict[task_data['id']] = task_data
        for catalogue_data in catalogue_data_list:
            catalogue_data_dict[catalogue_data['id']] = catalogue_data
        gantt_data = {'topics': task_data_dict, 'catalogues': catalogue_data_dict, 'start_time': start_time,
                      'finish_time': finish_time}
        cache.set('gantt-{}-data'.format(project_gantt.id), gantt_data, None)


@shared_task
def build_all_project_gantt_cache_data():
    project_gantts = ProjectGanttChart.objects.all()
    for project_gantt in project_gantts:
        project_gantt_data = ProjectGanttChartRetrieveSerializer(project_gantt).data
        start_time = project_gantt_data['start_time']
        finish_time = project_gantt_data['finish_time']
        tasks = project_gantt.task_topics.all()
        catalogues = project_gantt.task_catalogues.all()
        task_data_list = GanttTaskTopicCleanSerializer(tasks, many=True).data
        catalogue_data_list = GanttTaskCatalogueCleanSerializer(catalogues, many=True).data
        task_data_dict = {}
        catalogue_data_dict = {}
        for task_data in task_data_list:
            task_data_dict[task_data['id']] = task_data
        for catalogue_data in catalogue_data_list:
            catalogue_data_dict[catalogue_data['id']] = catalogue_data
        gantt_data = {'topics': task_data_dict, 'catalogues': catalogue_data_dict, 'start_time': start_time,
                      'finish_time': finish_time}
        cache.set('gantt-{}-data'.format(project_gantt.id), gantt_data, None)


# 重置每周执行的Playbook任务
@shared_task
def update_ongoing_project_playbook_weekly_task():
    # 当前阶段下的每周任务重置为未完成
    ongoing_projects = Project.ongoing_projects()
    ongoing_proposals = Proposal.ongoing_proposals()
    for project in chain(ongoing_projects, ongoing_proposals):
        stages = project.playbook_stages.all()
        for stage in stages:
            if stage.is_current_stage:
                stage_check_groups = stage.check_groups.all()
                for check_group in stage_check_groups:
                    check_group_check_items = check_group.check_items.all()
                    check_group_need_reset = False
                    for check_item in check_group_check_items:
                        if check_item.period == 'weekly':
                            check_item.checked = False
                            check_item.skipped = False
                            check_item.completed_at = None
                            check_item.expected_date = check_item.build_expected_date()
                            check_item.save()
                            check_group_need_reset = True
                    if check_group_need_reset:
                        check_group.checked = False
                        check_group.skipped = False
                        check_group.completed_at = None
                        check_group.save()


# 更新quip项目模版文件夹
@shared_task
def rebuild_project_quip_folder_template():
    get_project_quip_folder_template(rebuild=True)


@shared_task
def rebuild_test_cases_index():
    from testing.models import TestCaseLibrary
    for project in Project.objects.all():
        project_modules = project.test_case_modules.all()
        for module in project_modules:
            for index, case in enumerate(module.test_cases.filter(is_active=True).order_by('index', 'created_at')):
                case.index = index + 1
                case.save()

    for project in TestCaseLibrary.objects.all():
        project_modules = project.modules.all()
        for module in project_modules:
            for index, case in enumerate(module.test_cases.filter(is_active=True).order_by('index', 'created_at')):
                case.index = index + 1
                case.save()


@shared_task
def sync_permissions_groups_from_production_env():
    url = 'https://farm.chilunyc.com/api/users/func_perms/init_data?with_groups=true'
    result_data = requests.get(url).json()
    if "data" in result_data:
        init_func_perms(init_data=result_data['data'], build_groups=True)
