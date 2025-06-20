from copy import deepcopy
from django.utils import timezone

from farmbase.utils import get_user_data
from logs.models import get_field_value


def get_changed_fieldnames(original, updated):
    fields = updated._meta.get_fields()
    changed_field_names = set()
    for field in fields:
        old_value = get_field_value(original, field)
        new_value = get_field_value(updated, field)
        if old_value != new_value and field.editable:
            changed_field_names.add(field.name)
    return changed_field_names


def get_project_members_data(project, with_bd=True):
    members_data = []
    for member_filed in project.PROJECT_MEMBERS_FIELDS:
        field_name = member_filed['field_name']
        if field_name == 'test':
            continue
        if not with_bd and field_name == 'bd':
            continue
        if hasattr(project, field_name) and getattr(project, field_name):
            member_data = get_user_data(getattr(project, field_name))
            member_data['role'] = member_filed
            members_data.append(deepcopy(member_data))
    project_tests = project.tests.all()
    for project_test in project_tests:
        bd_data = get_user_data(project_test)
        bd_data['role'] = {"field_name": 'test', "name": "测试", "short_name": 'QA'}
        members_data.append(deepcopy(bd_data))
    return members_data


def get_project_developers_data(project, with_daily_work_statistics=False):
    from developers.utils import get_project_developer_daily_works_statistics, get_need_submit_daily_work
    job_positions = project.job_positions.order_by('-created_at')
    developer_ids = []
    developers = []
    for position in job_positions:
        developer = position.developer
        role = position.role
        developer_id = developer.id
        if developer_id not in developer_ids:
            avatar = None
            if developer.avatar:
                avatar = developer.avatar.url
            developer_data = {"id": developer.pk, "name": developer.name, 'username': developer.name,
                              'phone': developer.phone,
                              'avatar': avatar, 'avatar_url': avatar}
            developer_data['role'] = {"id": role.pk, "name": role.name}
            if with_daily_work_statistics:
                developer_data['statistics'] = get_project_developer_daily_works_statistics(project, developer)
            developer_data['today_need_submit_daily_work'] = get_need_submit_daily_work(project, developer,
                                                                                        timezone.now().date())
            developers.append(developer_data)
            developer_ids.append(developer_id)
    return developers


def get_project_members_dict(project):
    members_dict = {}
    for member_filed in project.PROJECT_MEMBERS_FIELDS:
        # if member_filed['field_name'] == 'test':
        #     continue
        field_name = member_filed['field_name']
        if hasattr(project, field_name) and getattr(project, field_name):
            member_data = get_user_data(getattr(project, field_name))
            member_data['role'] = member_filed
            members_dict[field_name] = deepcopy(member_data)
    members_dict['tests'] = []
    project_tests = project.tests.all()
    for project_test in project_tests:
        obj_data = get_user_data(project_test)
        obj_data['role'] = {"field_name": 'test', "name": "测试"}
        members_dict['tests'].append(deepcopy(obj_data))
    return members_dict


def get_need_star_rating_members_dict(project):
    members_dict = {}
    for member_filed in project.NEED_GRADE_MEMBERS_FIELDS:
        field_name = member_filed['field_name']
        if hasattr(project, field_name) and getattr(project, field_name):
            member_data = get_user_data(getattr(project, field_name))
            member_data['role'] = member_filed
            members_dict[field_name] = deepcopy(member_data)
    members_dict['tests'] = []
    project_tests = project.tests.all()
    for project_test in project_tests:
        obj_data = get_user_data(project_test)
        obj_data['role'] = {"field_name": 'test', "name": "测试"}
        members_dict['tests'].append(deepcopy(obj_data))
    return members_dict


def get_user_day_gantt_chart_tasks(user, day):
    from projects.models import GanttTaskTopic, Project
    task_topics = GanttTaskTopic.objects.none()
    for project in Project.ongoing_projects():
        gantt_chart = getattr(project, 'gantt_chart', None)
        if gantt_chart:
            roles = gantt_chart.roles.filter(user_id=user.id)
            for role in roles:
                task_topics = task_topics | role.task_topics.filter(is_done=False, is_dev_done=False,
                                                                    expected_finish_time__lte=day)
    return task_topics
