from copy import deepcopy

from auth_top.utils import get_top_user_data
from projects.models import Project


def get_project_members_top_user_data(project):
    members_data = []
    for member_filed in Project.PROJECT_MEMBERS_FIELDS:
        field_name = member_filed['field_name']
        if field_name == 'test':
            project_tests = project.tests.all()
            for project_test in project_tests:
                test_data = get_top_user_data(project_test)
                test_data['role'] = member_filed
                members_data.append(deepcopy(test_data))
        elif hasattr(project, field_name) and getattr(project, field_name):
            member_data = get_top_user_data(user=getattr(project, field_name))
            member_data['role'] = member_filed
            members_data.append(deepcopy(member_data))
    return members_data


def get_project_members_top_user_dict(project):
    members_dict = {}
    for member_filed in Project.PROJECT_MEMBERS_FIELDS:
        # if member_filed['field_name'] == 'test':
        #     continue
        field_name = member_filed['field_name']
        if hasattr(project, field_name) and getattr(project, field_name):
            member_data = get_top_user_data(user=getattr(project, field_name))
            member_data['role'] = member_filed
            members_dict[field_name] = deepcopy(member_data)
    members_dict['tests'] = []
    project_tests = project.tests.all()
    for project_test in project_tests:
        obj_data = get_top_user_data(user=project_test)
        obj_data['role'] = {"field_name": 'test', "name": "测试", "short_name": 'QA'},
        members_dict['tests'].append(deepcopy(obj_data))
    job_positions = project.job_positions.filter(role__name='测试工程师')
    test_developers = set([job_position.developer for job_position in job_positions]) if job_positions else []
    if test_developers:
        for test_developer in test_developers:
            obj_data = get_top_user_data(developer=test_developer)
            obj_data['role'] = {"field_name": 'test_developers', "name": "测试工程师", "short_name": 'QA'},
            members_dict['tests'].append(deepcopy(obj_data))
    return members_dict


def get_project_developers_top_user_data(project):
    job_positions = project.job_positions.order_by('-created_at')
    developer_ids = set()
    developers = []
    for position in job_positions:
        developer = position.developer
        role = position.role
        developer_id = developer.id
        if developer_id not in developer_ids:
            developer_data = get_top_user_data(developer=developer)
            developer_data['role'] = {"id": role.pk, "name": role.name}
            developers.append(developer_data)
            developer_ids.add(developer_id)
    return developers
