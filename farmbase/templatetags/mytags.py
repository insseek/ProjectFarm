import re
import json
from datetime import datetime, timedelta
from copy import deepcopy

from django import template
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from proposals.models import Proposal
from proposals.models import Project
from farmbase.permissions_utils import has_function_perms, has_any_function_perms, \
    has_view_function_module_perm, has_function_perm, get_user_function_perms, get_user_function_perm_codename_list
from projects.models import JobPositionNeed, TechnologyCheckpoint
from clients.models import Lead
from farmbase.serializers import ProfileSimpleSerializer
from farmbase.users_undone_works_utils import get_user_today_tpm_checkpoints_tasks, get_user_today_work_orders_tasks
from finance.models import ProjectPaymentStage

register = template.Library()


@register.filter(name="user_proposals_undone_work_count")
def user_proposals_undone_work_count(user):
    count = 0
    user_id = user.id
    objs = Proposal.ongoing_proposals().filter(Q(pm_id=user_id) | Q(bd_id=user_id)).all()
    for obj in objs:
        tasks_count = obj.undone_tasks().filter(principal_id=user_id,
                                                expected_at__lte=timezone.now().date()).count()
        count += tasks_count
    return count


@register.filter(name="user_leads_undone_work_count")
def user_leads_undone_work_count(user):
    count = 0
    user_id = user.id
    objs = Lead.objects.filter(status='contact').filter(Q(creator_id=user_id) | Q(salesman_id=user_id)).all()
    for obj in objs:
        tasks_count = obj.undone_tasks().filter(principal_id=user_id,
                                                expected_at__lte=timezone.now().date()).count()
        count += tasks_count
    return count


@register.filter(name="user_projects_job_position_needs_count")
def user_projects_job_position_needs_count(user):
    queryset = JobPositionNeed.undone_position_needs()
    manage_position_need = has_function_perm(user, 'manage_my_project_job_position_needs')
    count = 0
    if manage_position_need:
        for obj in queryset:
            project = obj.project
            if user in project.members:
                if obj.has_unhandled_candidate or obj.need_feedback:
                    count += 1
                # 状态待处理 预计确认时间在今天或已过期
                elif obj.status == 0 and obj.expected_date and obj.expected_date <= datetime.today().date():
                    count += 1
    return count


@register.filter(name="user_projects_job_position_needs_add_candidate_count")
def user_projects_job_position_needs_add_candidate_count(user):
    queryset = JobPositionNeed.undone_position_needs()
    add_candidate = has_function_perm(user, 'add_candidates_for_all_project_job_position_needs')
    count = 0
    if add_candidate:
        for obj in queryset:
            # 状态待处理   职位需求中需要新的候选人
            if add_candidate and obj.status == 0:
                if obj.need_new_candidate:
                    count += 1
    return count


@register.filter(name="proposals_report_count")
def proposals_report_count(user):
    return user.pm_proposals.filter(status=3).count()


@register.filter(name="proposals_call_count")
def proposals_call_count(user):
    return user.pm_proposals.filter(status=2).count()


@register.filter(name="user_project_undone_work_count")
def user_project_undone_work_count(user, project):
    today = timezone.now().date()
    if project.manager_id == user.id:
        return project.undone_tasks().filter(expected_at__lte=today).count()
    else:
        return project.undone_tasks().filter(expected_at__lte=today, principal_id=user.id).count()


@register.filter(name="my_active_projects")
def my_active_projects(user, with_mentor_projects=False):
    ongoing_projects = Project.ongoing_projects()
    active_projects = set()
    for project in ongoing_projects:
        members = deepcopy(project.members)
        if not with_mentor_projects:
            if project.mentor:
                members.remove(project.mentor)
        if not project.current_stages.filter(stage_type="design").exists():
            if project.designer:
                members.remove(project.designer)
        if user in members:
            active_projects.add(project)
    active_projects = sorted(active_projects, key=lambda x: x.created_at, reverse=True)
    return active_projects


@register.filter(name="mentor_active_projects")
def mentor_active_projects(user):
    mentor_projects = Project.ongoing_projects().filter(mentor_id=user.id)
    mentor_projects = set(mentor_projects) - set(my_active_projects(user))
    return sorted(mentor_projects, key=lambda x: x.created_at, reverse=True)


@register.filter(name="pending_proposals_count")
def pending_proposals_count(user):
    return Proposal.objects.filter(status=1).count()


@register.filter(name="timediffnow")
def timediffnow(time):
    return (timezone.now() - time).total_seconds()


@register.filter(name="has_func_perm")
def has_func_perm(user, perm):
    return has_function_perm(user, perm)


@register.filter(name="has_func_perms")
def has_func_perms(user, perms):
    permission_list = re.sub(r'[;；,，]', ' ', perms).split()
    return has_function_perms(user, permission_list)


@register.filter(name="func_perms")
def func_perms(user):
    return get_user_function_perms(user)


@register.filter(name="has_any_func_perms")
def has_any_func_perms(user, perms):
    permission_list = re.sub(r'[;；,，]', ' ', perms).split()
    return has_any_function_perms(user, permission_list)


@register.filter(name="has_any_func_perm")
def has_any_func_perm(user, perms):
    permission_list = re.sub(r'[;；,，]', ' ', perms).split()
    return has_any_function_perms(user, permission_list)


@register.filter(name="can_view_func_module")
def can_view_func_module(user, module_name):
    return has_view_function_module_perm(user, module_name)


@register.filter(name="can_view_menu_module")
def can_view_func_module(user, module_name):
    proposal_menu_perms = (
        'view_unassigned_proposals', 'create_proposal', 'view_my_proposals', 'view_all_proposals',
        'view_ongoing_proposals',
        'view_proposals_finished_in_90_days', 'view_all_proposal_biz_opportunities', 'view_calculator',
        'view_all_reports',
        'view_report_frame_diagrams', 'view_all_call_records')
    other_menu_perms = (
        'view_all_prototype_references', 'view_project_capacity_data', 'view_projects_and_proposals_statistical_data',
        'manage_projects_gitlab_committers', 'leads_manage_sem_track', 'users_management', 'use_farm_email',
        'view_proposal_pm_playbook_template', 'view_project_manager_playbook_template', 'users_perms_limit_management',
        'users_teams_management')
    if module_name == 'proposals':
        return has_any_function_perms(user, proposal_menu_perms)
    elif module_name == 'other':
        return has_any_function_perms(user, other_menu_perms)

    return has_view_function_module_perm(user, module_name)


@register.filter(name="is_superuser")
def is_superuser(user):
    return user.is_superuser


@register.filter(name="has_perm")
def has_perm(user, perm_code):
    return user.has_perm(perm_code)


@register.filter(name="in_group")
def in_group(user, group_name):
    return user.groups.filter(name=group_name).exists()


@register.filter(name="user_with_perm_data")
def user_with_perm_data(user):
    data = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "groups": list(user.groups.values_list('name', flat=True)),
        "perms": get_user_function_perm_codename_list(user),
        "is_superuser": user.is_superuser,
        "profile": ProfileSimpleSerializer(user.profile).data
    }
    groups = data['groups']
    for key, value in settings.GROUP_NAME_DICT.items():
        data["is_" + key] = True if value in groups else False
    return json.dumps(data)


@register.filter(name="all_group_name")
def all_group_name(user):
    group_list = [name for name in user.groups.values_list('name', flat=True) if name]
    if user.is_superuser:
        group_list.append('超级管理员')
    return ','.join(set(group_list))


@register.filter(name="has_cooperation_with_developer_at_present")
def has_cooperation_with_developer_at_present(user, developer_id):
    ongoing_project = Project.ongoing_projects().filter(manager=user)
    developer_id = int(developer_id)
    for project in ongoing_project:
        if project.job_positions.filter(developer_id=developer_id).exists():
            return True
    return False


@register.filter(name="proposal_countdown")
def proposal_countdown(time):
    if time:
        m, s = divmod(86400 - (timezone.now() - time).total_seconds(), 60)
        h, m = divmod(m, 60)
        return "剩余时间：%d小时%d分钟" % (h, m)
    return None


@register.simple_tag(name='settings')
def settings_value(value):
    return getattr(settings, value, '')


@register.simple_tag(name='date_timedelta_days')
def date_timedelta_days(days, fmt):
    date = datetime.now() + timedelta(days=int(days))

    return date.strftime(fmt)


@register.filter(name='tag_list')
def tag_list(value):
    return ", ".join(o.name for o in value.tags.all())


@register.filter(name='today_todo_work_orders_count')
def today_todo_work_orders_count(user):
    tasks = get_user_today_work_orders_tasks(user)
    return len(tasks(user))


@register.filter(name='undone_tpm_checkpoints_count')
def undone_tpm_checkpoints_count(user):
    tasks = get_user_today_tpm_checkpoints_tasks(user)
    return len(tasks)


@register.filter(name='sample_date_format')
def sample_date_format(datetime_data):
    return datetime_data.strftime(settings.SAMPLE_DATE_FORMAT)


@register.filter(name='sample_datetime_format')
def sample_datetime_format(datetime_data):
    return datetime_data.strftime(settings.SAMPLE_DATETIME_FORMAT)


@register.simple_tag(name='now_time_text')
def settings_value():
    now = timezone.now()
    now_text = now.strftime('%Y年%m月%d日({week}) %H:%M:%S')
    week_day = get_week_day(now)
    now_text = now_text.format(week=week_day)
    return now_text


# 没有打款项、打款项过期了
@register.filter(name='project_payments_remind')
def project_payments_remind(project):
    if not project.project_payments.count():
        return True

    stages = ProjectPaymentStage.objects.filter(project_payment__project_id=project.id)
    for obj in stages:
        if not obj.receipted_amount:
            if obj.expected_date and timezone.now().date() >= obj.expected_date:
                return True


def get_week_day(date):
    week_day_dict = {
        0: '周一',
        1: '周二',
        2: '周三',
        3: '周四',
        4: '周五',
        5: '周六',
        6: '周日',
    }
    day = date.weekday()
    return week_day_dict[day]
