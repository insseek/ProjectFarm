from datetime import datetime, timedelta

from django.core.cache import cache
from django.conf import settings
from rest_framework.decorators import api_view

from gearfarm.utils.farm_response import api_success, api_request_params_required, api_error, api_bad_request
from geargitlab.tasks import crawl_farm_project_recent_half_hour_git_demo_commits
from projects.models import Project, ProjectLinks


@api_view(['GET'])
def project_deploy_status(request):
    track_code = request.GET.get('track_code')
    if not track_code:
        return api_request_params_required(['track_code'])
    projects = Project.objects.filter(track_code=track_code)
    if not projects.exists():
        return api_bad_request(message="track_code未找到对应的项目")

    project = projects.first()
    project_links = ProjectLinks.objects.filter(project_id=project.id)
    if not project_links.exists():
        return api_bad_request(message="Farm上该项目暂未绑定gitlab项目")

    git_group = project.links.gitlab_group_id
    git_project = project.links.gitlab_project_id
    if not any([git_group, git_project]):
        return api_bad_request(message="Farm上该项目暂未绑定gitlab项目")

    farm_projects_demo_status = cache.get('farm_projects_demo_status', {})
    if not farm_projects_demo_status.get(project.id):
        farm_projects_demo_status = crawl_farm_project_recent_half_hour_git_demo_commits(project.id)
    demo_status = farm_projects_demo_status.get(project.id)
    if not demo_status:
        return api_bad_request(message='获取项目部署状态失败')

    # 测试
    # import random
    # list_one = ["normal", 'maintaining']
    # choice_num = random.choice(list_one)
    # demo_status['status'] = choice_num

    project_data = {"id": project.id, "name": project.name,
                    'demo_status': demo_status}
    last_commit = project_data['demo_status']['last_commit']

    if last_commit:
        last_commit['created_at'] = change_gitlab_datetime_str(last_commit['created_at'])

    return api_success(data=project_data)


def change_gitlab_datetime_str(datetime_str):
    if '+08:00' in datetime_str:
        datetime_str = datetime.strptime(
            datetime_str,
            "%Y-%m-%dT%H:%M:%S.%f+08:00").strftime(
            settings.DATETIME_FORMAT)
    elif datetime_str.endswith('Z'):
        datetime_str = (
                datetime.strptime(datetime_str,
                                  "%Y-%m-%dT%H:%M:%S.%fZ") + timedelta(
            hours=8)).strftime(settings.DATETIME_FORMAT)
    return datetime_str
