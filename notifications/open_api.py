import logging
from itertools import chain

from django.contrib.auth.models import User, Group
from django.conf import settings
from rest_framework.decorators import api_view

from gearfarm.utils.farm_response import api_success, api_request_params_required, api_error, api_bad_request
from gearfarm.utils import farm_response
from gearfarm.utils.decorators import request_data_fields_required, request_params_required
from farmbase.models import Profile
from oauth.feishu_client import FeiShu
from oauth.aliyun_client import AliyunApi
from geargitlab.gitlab_client import GitlabClient
from developers.models import Developer
from notifications.utils import create_developer_notification, create_notification, send_feishu_message_to_user
from projects.utils.common_utils import get_project_members_dict, get_project_developers_data
from oauth.utils import get_feishu_client

logger = logging.getLogger()


@api_view(['POST'])
@request_data_fields_required(['app_id', 'app_secret', 'message'])
def send_feishu_message(request):
    app_id = request.data.get('app_id')
    app_secret = request.data.get('app_secret')
    chat_id = request.data.get('chat_id')
    message = request.data.get('message')
    link = request.data.get('link')
    username_list = request.data.get('users', [])

    KUBERNETES_APP_ID = "cli_9d338787da799101"
    KUBERNETES_CHAT_ID = 'oc_f84a81984897bfb9d1303ba77dc0fa0b'
    try:
        feishu_client = FeiShu(app_id=app_id, app_secret=app_secret)
        at_user_ids = []
        if username_list:
            users = User.objects.filter(username__in=username_list, is_active=True)
            at_user_ids = [user.profile.feishu_user_id for user in users if user.profile.feishu_user_id]
        if chat_id:
            feishu_client.send_message_to_chat(chat_id, message, at_user_ids=at_user_ids, link=link)
        elif app_id == KUBERNETES_APP_ID:
            feishu_client.send_message_to_chat(KUBERNETES_CHAT_ID, message, at_user_ids=at_user_ids, link=link)
        else:
            for feishu_user_id in at_user_ids:
                feishu_client.send_message_to_user(feishu_user_id, message, link=link)
    except Exception as e:
        return farm_response.api_error(str(e))
    return farm_response.api_success()


@api_view(['POST'])
@request_data_fields_required(['content', 'app_name'])
def send_bug_message_to_developers(request):
    app_name = request.data.get('app_name')
    content = request.data.get('content')
    env = request.data.get('env', '') or ''
    phone = request.data.get('phone', '')

    gitlab_user_id = request.data.get('gitlab_user_id', None)
    gitlab_project_id = request.data.get('gitlab_project_id', None)
    if not (gitlab_project_id or gitlab_project_id or phone):
        return api_bad_request("参数gitlab_user_id、gitlab_project_id、phone至少传一个")
    link_base = 'https://devops.monitoring.aks.chilunyc.com/elk/index.html?appName={}&env={}'
    link = link_base.format(app_name, env)
    developers = []
    users = []
    phones = set()
    if phone:
        phones.add(phone)
        developer = Developer.objects.filter(phone=phone, is_active=True)
        if developer.exists():
            developers.append(developer.first())
    elif gitlab_user_id:
        developer = Developer.objects.filter(gitlab_user_id=gitlab_user_id, is_active=True).first()
        if not developer:
            return farm_response.api_not_found('没有找到工程师')
        developers.append(developer)
    elif gitlab_project_id:
        users, developers = get_users_developers_by_gitlab_project(gitlab_project_id)

    for developer in developers:
        create_developer_notification(developer, content, url=link)
        if developer.phone:
            phones.add(developer.phone)
    if not settings.DEVELOPMENT:
        aliyun_client = AliyunApi(access_key_id=settings.ALIYUN_ACCESS_KEY_ID,
                                  access_key_secret=settings.ALIYUN_ACCESS_KEY_SECRET)
        for phone in phones:
            aliyun_client.send_app_bug_sms(phone, content, app_name, env)
    for user in users:
        create_notification(user, content, url=link)
    return farm_response.api_success()


def get_users_developers_by_gitlab_project(gitlab_project_id):
    developers = []
    users = []
    gitlab_client = GitlabClient()
    try:
        project_members = gitlab_client.get_project_members(gitlab_project_id)
    except Exception as e:
        return farm_response.api_error(str(e))

    if project_members:
        gitlab_user_ids = [member.id for member in project_members]
        group_dict = settings.GROUP_NAME_DICT
        groups = [group_dict['tpm'], group_dict['project_manager'], group_dict['pm'], group_dict['learning_pm'],
                  group_dict['remote_tpm'], group_dict['test']]
        users = User.objects.filter(groups__name__in=groups).filter(profile__gitlab_user_id__in=gitlab_user_ids,
                                                                    is_active=True).distinct()
        developers = Developer.objects.filter(gitlab_user_id__in=gitlab_user_ids, is_active=True)
    return users, developers


def get_farm_projects_by_gitlab_project(gitlab_project_id):
    gitlab_client = GitlabClient()
    try:
        gitlab_project = gitlab_client.get_project(gitlab_project_id)
    except Exception as e:
        raise

    projects = []
    from projects.models import ProjectLinks
    if gitlab_project:
        project_links = ProjectLinks.objects.filter(gitlab_project_id=gitlab_project_id)
        for project_link in project_links:
            projects.append(project_link.project)

    if gitlab_project:
        p_attributes = gitlab_project.attributes
        p_namespace = p_attributes.get('namespace', None)
        if p_namespace and p_namespace.get('kind', None) == 'group':
            gitlab_group_id = p_namespace['id']
            project_links = ProjectLinks.objects.filter(gitlab_group_id=gitlab_group_id)
            for project_link in project_links:
                projects.append(project_link.project)
    return projects


def get_gitlab_project(gitlab_project_id):
    gitlab_client = GitlabClient()
    try:
        gitlab_project = gitlab_client.get_project(gitlab_project_id)
        return gitlab_project
    except Exception as e:
        raise


@api_view(['POST'])
@request_data_fields_required(['branch', 'stage', 'job_id'])
def send_cicd_failed_message(request):
    '项目${app_name}的分支${branch}的CICD的${stage}阶段失败，请查看https://git.chilunyc.com/${group}/${project}/-/jobs/${job_id}'

    app_name = request.data.get('app_name')
    branch = request.data.get('branch')
    stage = request.data.get('stage')

    job_id = request.data.get('job_id')

    group = request.data.get('group', '')
    project = request.data.get('project', '')

    gitlab_project_id = request.data.get('gitlab_project_id', None)
    if gitlab_project_id:
        gitlab_project = get_gitlab_project(gitlab_project_id)
        if gitlab_project:
            path_with_namespace = gitlab_project.attributes.get('path_with_namespace')
            if path_with_namespace:
                group, project = path_with_namespace.split('/', 1)
            app_name = gitlab_project.attributes.get('name_with_namespace', '').replace(' ', '')

    path = '/{}/{}/-/jobs/{}'.format(group, project, job_id)
    phone = request.data.get('phone', None)

    gitlab_user_id = request.data.get('gitlab_user_id', None)
    gitlab_project_id = request.data.get('gitlab_project_id', None)
    if not (gitlab_user_id or gitlab_project_id or phone):
        return api_bad_request("参数gitlab_user_id、gitlab_project_id、phone至少传一个")

    developers = set()
    # users = set(settings.DEV_OPS_RESPONSIBLE)
    phones = set()
    if phone:
        phones.add(phone)
    if gitlab_user_id:
        developer = Developer.objects.filter(gitlab_user_id=gitlab_user_id, is_active=True).first()
        if developer:
            developers.add(developer)
            if developer.phone:
                phones.add(developer.phone)
        else:
            return farm_response.api_not_found('通过gitlab_user_id没有找到工程师')
    if gitlab_project_id:
        projects = get_farm_projects_by_gitlab_project(gitlab_project_id)
        if projects:
            for p in projects:
                if p.tpm and p.tpm.is_active:
                    users.add(p.tpm)
    link = 'https://git.chilunyc.com{path}'.format(path=path)

    if not settings.DEVELOPMENT:
        aliyun_client = AliyunApi(access_key_id=settings.ALIYUN_ACCESS_KEY_ID,
                                  access_key_secret=settings.ALIYUN_ACCESS_KEY_SECRET)
        for phone in phones:
            aliyun_client.send_project_cicd_sms(phone, app_name, branch, stage, group, project, job_id)

    content = 'Gitlab项目【{app_name}】的{branch}分支的CICD的{stage}阶段失败'.format(
        app_name=app_name,
        branch=branch,
        stage=stage
    )
    for developer in developers:
        create_developer_notification(developer, content, url=link)
    # for user in users:
    #     send_feishu_message_to_user(user, content, url=link)
    return farm_response.api_success()


@api_view(['GET'])
@request_params_required(['gitlab_project_id'])
def get_projects_by_gitlab_project(request):
    gitlab_project_id = request.GET['gitlab_project_id']
    project_list = []
    if gitlab_project_id:
        projects = get_farm_projects_by_gitlab_project(gitlab_project_id)
        if projects:
            for p in projects:
                p_data = {
                    'id': p.id,
                    'name': p.name,
                    'members': get_project_members_dict(p),
                    'developers': get_project_developers_data(p)
                }
                project_list.append(p_data)
    return farm_response.api_success(project_list)


@api_view(['GET'])
@request_params_required(['gitlab_user_id'])
def get_farm_users_by_gitlab_user(request):
    gitlab_user_id = request.GET['gitlab_user_id']
    data = {
        "user": None,
        "developer": None
    }
    if gitlab_user_id:
        user = User.objects.filter(profile__gitlab_user_id=gitlab_user_id, is_active=True).first()
        developer = Developer.objects.filter(gitlab_user_id=gitlab_user_id, is_active=True).first()
        if user:
            data['user'] = {'id': user.id, 'username': user.username}
        if developer:
            data['developer'] = {'id': developer.id, 'username': developer.username}

    return farm_response.api_success(data)


@api_view(['POST'])
@request_data_fields_required(['branch', 'pipeline_id'])
def send_cicd_passed_message(request):
    'Gitlab项目【李帆平测试】的develop分支的CICD已完成，请查看https://git.chilunyc.com/chaoneng/GearFarm/pipelines/76621 (https://git.chilunyc.com/chaoneng/GearFarm/pipelines)'

    app_name = request.data.get('app_name', '')
    branch = request.data.get('branch', '')

    group = request.data.get('group', '')
    project = request.data.get('project', '')

    gitlab_project_id = request.data.get('gitlab_project_id', None)
    if gitlab_project_id:
        gitlab_project = get_gitlab_project(gitlab_project_id)
        if gitlab_project:
            path_with_namespace = gitlab_project.attributes.get('path_with_namespace')
            if path_with_namespace:
                group, project = path_with_namespace.split('/', 1)
            app_name = gitlab_project.attributes.get('name_with_namespace', '').replace(' ', '')

    pipeline_id = request.data.get('pipeline_id')

    path = '/{}/{}/pipelines/{}'.format(group, project, pipeline_id)
    phone = request.data.get('phone', None)

    gitlab_user_id = request.data.get('gitlab_user_id', None)
    gitlab_project_id = request.data.get('gitlab_project_id', None)
    if not (gitlab_user_id or gitlab_project_id or phone):
        return api_bad_request("参数gitlab_user_id、gitlab_project_id、phone至少传一个")

    developers = set()
    users = set()
    phones = set()
    if phone:
        phones.add(phone)
    if gitlab_user_id:
        developer = Developer.objects.filter(gitlab_user_id=gitlab_user_id, is_active=True).first()
        if developer:
            developers.add(developer)
            if developer.phone:
                phones.add(developer.phone)
        else:
            return farm_response.api_not_found('通过gitlab_user_id没有找到工程师')

    projects = []
    if gitlab_project_id:
        projects = get_farm_projects_by_gitlab_project(gitlab_project_id)
        if projects:
            for p in projects:
                if p.manager and p.manager.is_active:
                    users.add(p.manager)
                if p.test and p.test.is_active:
                    users.add(p.test)

    if not settings.DEVELOPMENT:
        aliyun_client = AliyunApi(access_key_id=settings.ALIYUN_ACCESS_KEY_ID,
                                  access_key_secret=settings.ALIYUN_ACCESS_KEY_SECRET)
        for phone in phones:
            aliyun_client.send_project_cicd_passed_sms(phone, app_name, branch, group, project, pipeline_id)

    link = 'https://git.chilunyc.com{path}'.format(path=path)
    project_name = '、'.join([p.name for p in projects])
    content = '项目【{}】绑定的Gitlab项目中【{}】的{}分支的CICD已完成'.format(project_name, app_name, branch)
    for user in users:
        send_feishu_message_to_user(user, content, url=link)
    return farm_response.api_success()


@api_view(['POST'])
@request_data_fields_required(['message'])
def send_feishu_message_to_farm_users(request):
    message = request.data.get('message')
    link = request.data.get('link')
    users, developers = get_users_developers_from_request(request)

    at_user_ids = []
    for user in users:
        if user.profile.feishu_user_id:
            at_user_ids.append(user.profile.feishu_user_id)
    for developer in developers:
        if developer.feishu_user_id:
            at_user_ids.append(developer.feishu_user_id)
    if at_user_ids:
        feishu_client = get_feishu_client()
        for feishu_user_id in at_user_ids:
            feishu_client.send_message_to_user(feishu_user_id, message, link=link)
    return farm_response.api_success()


@api_view(['POST'])
@request_data_fields_required(['template_code', 'template_param'])
def send_dysms_to_farm_users(request):
    template_code = request.data.get('template_code')
    template_param = request.data.get('template_param')
    phones = get_users_developers_phones_from_request(request)
    if not settings.DEVELOPMENT:
        if phones:
            aliyun_client = AliyunApi(access_key_id=settings.ALIYUN_ACCESS_KEY_ID,
                                      access_key_secret=settings.ALIYUN_ACCESS_KEY_SECRET)
            for phone in phones:
                aliyun_client.send_sms(phone, template_code, template_param)

    return farm_response.api_success()


@api_view(['POST'])
@request_data_fields_required(['gitlab_project_id', 'branch', 'stage', 'job_id'])
def send_cicd_failed_message_to_farm_users(request):
    '项目${app_name}的分支${branch}的CICD的${stage}阶段失败，请查看https://git.chilunyc.com/${group}/${project}/-/jobs/${job_id}'
    phones = get_users_developers_phones_from_request(request)

    gitlab_project_id = request.data['gitlab_project_id']
    branch = request.data.get('branch')
    stage = request.data.get('stage')
    job_id = request.data.get('job_id')

    app_name = request.data.get('app_name')
    group = request.data.get('group', '')
    project = request.data.get('project', '')

    if gitlab_project_id:
        gitlab_project = get_gitlab_project(gitlab_project_id)
        if gitlab_project:
            path_with_namespace = gitlab_project.attributes.get('path_with_namespace')
            if path_with_namespace:
                group, project = path_with_namespace.split('/', 1)
            app_name = gitlab_project.attributes.get('name_with_namespace', '').replace(' ', '')

    if not settings.DEVELOPMENT:
        if phones:
            aliyun_client = AliyunApi(access_key_id=settings.ALIYUN_ACCESS_KEY_ID,
                                      access_key_secret=settings.ALIYUN_ACCESS_KEY_SECRET)
            for phone in phones:
                aliyun_client.send_project_cicd_sms(phone, app_name, branch, stage, group, project, job_id)

    return farm_response.api_success()


def get_users_developers_from_request(request):
    user_ids = request.data.get('users', [])
    developer_ids = request.data.get('developers', [])
    users = []
    if user_ids:
        users = User.objects.filter(id__in=user_ids, is_active=True)
    developers = []
    if developer_ids:
        developers = Developer.objects.filter(id__in=developers, is_active=True)
    return users, developers


@api_view(['POST'])
@request_data_fields_required(['branch', 'pipeline_id', 'gitlab_project_id'])
def send_cicd_passed_message_to_farm_users(request):
    'Gitlab项目【李帆平测试】的develop分支的CICD已完成，请查看https://git.chilunyc.com/chaoneng/GearFarm/pipelines/76621 (https://git.chilunyc.com/chaoneng/GearFarm/pipelines)'

    '项目${app_name}的分支${branch}的CICD的${stage}阶段失败，请查看https://git.chilunyc.com/${group}/${project}/-/jobs/${job_id}'
    phones = get_users_developers_phones_from_request(request)

    gitlab_project_id = request.data['gitlab_project_id']
    branch = request.data.get('branch')
    pipeline_id = request.data.get('pipeline_id')

    app_name = request.data.get('app_name')
    group = request.data.get('group', '')
    project = request.data.get('project', '')

    if gitlab_project_id:
        gitlab_project = get_gitlab_project(gitlab_project_id)
        if gitlab_project:
            path_with_namespace = gitlab_project.attributes.get('path_with_namespace')
            if path_with_namespace:
                group, project = path_with_namespace.split('/', 1)
            app_name = gitlab_project.attributes.get('name_with_namespace', '').replace(' ', '')

    if not settings.DEVELOPMENT:
        if phones:
            aliyun_client = AliyunApi(access_key_id=settings.ALIYUN_ACCESS_KEY_ID,
                                      access_key_secret=settings.ALIYUN_ACCESS_KEY_SECRET)
            for phone in phones:
                aliyun_client.send_project_cicd_passed_sms(phone, app_name, branch, group, project, pipeline_id)
    return farm_response.api_success()


def get_users_developers_phones_from_request(request):
    user_ids = request.data.get('users', [])
    developer_ids = request.data.get('developers', [])
    users = []
    if user_ids:
        users = User.objects.filter(id__in=user_ids, is_active=True)
    developers = []
    if developer_ids:
        developers = Developer.objects.filter(id__in=developers, is_active=True)

    phones = set()

    for user in users:
        if user.profile and user.profile.phone_number:
            phones.add(user.profile.phone_number)
    for developer in developers:
        if developer.phone:
            phones.add(developer.phone)
    return phones
