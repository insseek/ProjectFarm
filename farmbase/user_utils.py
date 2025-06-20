from copy import deepcopy
from datetime import datetime, timedelta

from django.db.models import Sum, IntegerField, When, Case, Q
from django.utils import timezone
from django.utils import six
from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache

from farmbase.permissions_utils import has_function_perm, has_any_function_perms, func_perm_required
from farmbase.models import FunctionPermission
from projects.models import Project
from proposals.models import Proposal
from clients.models import Lead


def unique_chain(*iterables):
    known_ids = set()
    for item in iterables:
        for element in item:
            if element.id not in known_ids:
                known_ids.add(element.id)
                yield element


def get_user_view_leads(user, is_mine=None):
    base_leads = Lead.objects.all()
    my_leads = base_leads.filter(Q(creator_id=user.id) | Q(salesman_id=user.id))
    if user.groups.filter(name=settings.GROUP_NAME_DICT['sem']).exists():
        my_leads = base_leads.filter(
            Q(creator_id=user.id) | Q(salesman_id=user.id) | Q(lead_source__source_type='sem') | Q(
                lead_source__source_type='website'))
    if not is_mine:
        if has_function_perm(user, 'view_all_leads'):
            other_leads = deepcopy(base_leads)
            # 全部线索权限 限定
            cache_key = 'user_{user_id}_special_permissions'.format(user_id=user.id)
            user_special_permissions = cache.get(cache_key, {})
            if 'view_all_leads' in user_special_permissions:
                special_permission_data = user_special_permissions['view_all_leads']
                special_params = special_permission_data.get('params')
                if special_params:
                    creator_username_list = special_params.get('creators', [])
                    salesmen_username_list = special_params.get('salesmen', [])
                    if creator_username_list:
                        other_leads = other_leads.filter(creator_id__in=creator_username_list)
                    if salesmen_username_list:
                        other_leads = other_leads.filter(salesman_id__in=salesmen_username_list)
            return (my_leads | other_leads).distinct()
        return my_leads
    return my_leads


def get_user_view_proposals(user, main_status=None):
    base_proposals = Proposal.objects.all()
    if main_status == 'ongoing':
        base_proposals = Proposal.ongoing_proposals()
    elif main_status == 'closed':
        base_proposals = Proposal.closed_proposals()

    ongoing_proposals = Proposal.ongoing_proposals(queryset=base_proposals).order_by('created_at')
    closed_proposals = Proposal.closed_proposals(queryset=base_proposals).order_by('-closed_at')
    user_ongoing_proposals = Proposal.user_proposals(user, queryset=ongoing_proposals)
    user_closed_proposals = Proposal.user_proposals(user, queryset=closed_proposals)

    if has_function_perm(user, 'view_all_proposals'):
        pass
    else:
        if not has_function_perm(user, 'view_ongoing_proposals'):
            ongoing_proposals = Proposal.objects.none()

        if has_function_perm(user, 'view_proposals_finished_in_90_days'):
            closed_proposals = closed_proposals.filter(closed_at__gte=timezone.now() - timedelta(days=90))
        else:
            closed_proposals = Proposal.objects.none()
    combined_list = list(
        unique_chain(user_ongoing_proposals, ongoing_proposals, user_closed_proposals, closed_proposals))
    return combined_list


def get_user_view_projects(user, main_status=None):
    base_projects = Project.objects.all()
    if main_status == 'ongoing':
        base_projects = Project.ongoing_projects()
    elif main_status == 'closed':
        base_projects = Project.completion_projects()

    ongoing_projects = Project.ongoing_projects(queryset=base_projects).order_by('created_at')
    closed_projects = Project.closed_projects(queryset=base_projects).order_by('-done_at')
    user_ongoing_projects = Project.user_projects(user, queryset=ongoing_projects)
    user_closed_projects = Project.user_projects(user, queryset=closed_projects)

    if has_function_perm(user, 'view_all_projects'):
        pass
    else:
        if not has_function_perm(user, 'view_ongoing_projects'):
            ongoing_projects = Project.objects.none()

        if has_function_perm(user, 'view_projects_finished_in_60_days'):
            closed_projects = closed_projects.filter(done_at__gte=timezone.now() - timedelta(days=60))
        else:
            closed_projects = Project.objects.none()

    combined_list = list(
        unique_chain(user_ongoing_projects, ongoing_projects, user_closed_projects, closed_projects))
    return combined_list


def get_user_projects(user, projects=None, members=None, exclude_members=[]):
    from projects.models import Project
    return Project.user_projects(user, queryset=projects, members=None, exclude_members=[])


def get_user_by_name(name):
    users = User.objects.filter(username=name)
    if users.exists():
        user = users.first()
        return user


def get_users_by_group(groups):
    if isinstance(groups, six.string_types):
        groups = (groups,)
    else:
        groups = groups
    users = User.objects.filter(is_active=True).filter(groups__name__in=groups).distinct()
    return users


def get_user_data(manager):
    avatar_url = None
    if manager.profile.avatar:
        avatar_url = manager.profile.avatar.url
    avatar_color = manager.profile.avatar_color
    manager_data = {'username': manager.username,
                    "avatar": avatar_url,
                    "phone": manager.profile.phone,
                    "avatar_url": avatar_url, 'avatar_color': avatar_color,
                    'id': manager.id,
                    'is_active': manager.is_active
                    }
    return manager_data


def in_group(user, group_name):
    return user.groups.filter(name=group_name).exists()


def in_any_groups(user, group_names):
    if isinstance(group_names, str):
        group_names = [group_names]
    else:
        group_names = group_names
    return user.groups.filter(name__in=group_names).exists()


def get_active_users_by_function_perm(perm, need_superuser=False):
    func_perm = FunctionPermission.objects.filter(codename=perm)
    users = User.objects.none()
    if need_superuser:
        users = User.objects.filter(is_active=True, is_superuser=True)
    if func_perm.exists():
        func_perm = func_perm.first()
        groups = func_perm.groups.all()
        perm_users = func_perm.users.filter(is_active=True)
        if users:
            users = users | perm_users
        else:
            users = perm_users
        for group in groups:
            users = users | group.user_set.filter(is_active=True)
        users = users.distinct()
    return users
