from copy import deepcopy

from django.core.cache import cache
from django.contrib.auth.models import User
from rest_framework.decorators import api_view, authentication_classes, permission_classes

from gearfarm.utils.farm_response import api_success, api_not_found, api_bad_request
from gearfarm.utils.decorators import request_params_required, request_data_fields_required
from farmbase.serializers import UserWithGitlabUserSerializer
from developers.models import Developer
from developers.serializers import DeveloperWithGitlabUserSerializer


@api_view(['GET'])
@request_params_required('gitlab_user_id')
def gitlab_personal_info(request):
    params = request.GET
    gitlab_user_id = params.get('gitlab_user_id')
    if not gitlab_user_id:
        return api_bad_request(message="参数无效")
    user = User.objects.filter(profile__gitlab_user_id=gitlab_user_id).first()
    if user:
        data = UserWithGitlabUserSerializer(user).data
        return api_success(data=data)
    developer = Developer.objects.filter(gitlab_user_id=gitlab_user_id).first()
    if developer:
        data = DeveloperWithGitlabUserSerializer(developer).data
        return api_success(data=data)
    return api_not_found()


@api_view(['GET'])
def gitlab_users_dict(request):
    gitlab_farm_users = {}

    gitlab_user_dict = cache.get('gitlab-users', {})
    gitlab_username_dict = {}
    gitlab_name_dict = {}
    for gitlab_user in gitlab_user_dict.values():
        gitlab_username_dict[gitlab_user['username']] = gitlab_user
        gitlab_name_dict[gitlab_user['name']] = gitlab_user

    users = User.objects.all()
    farm_users = {}
    user_data_list = UserWithGitlabUserSerializer(users, many=True).data
    for user_data in user_data_list:
        username = user_data['username']
        gitlab_user = user_data['gitlab_user']
        if gitlab_user:
            gitlab_user_id = gitlab_user['id']
            farm_users[username] = deepcopy(user_data)
            gitlab_user_dict[gitlab_user_id] = deepcopy(gitlab_user)
            gitlab_username_dict[gitlab_user['username']] = deepcopy(gitlab_user)
            gitlab_name_dict[gitlab_user['name']] = deepcopy(gitlab_user)

            if gitlab_user_id not in gitlab_farm_users:
                gitlab_farm_users[gitlab_user_id] = username

    farm_developers = {}
    developers = Developer.objects.all()
    developer_data_list = DeveloperWithGitlabUserSerializer(developers, many=True).data
    for developer_data in developer_data_list:
        username = developer_data['username']
        gitlab_user = developer_data['gitlab_user']
        if gitlab_user:
            gitlab_user_id = gitlab_user['id']
            farm_developers[username] = deepcopy(developer_data)
            gitlab_user_dict[gitlab_user_id] = deepcopy(gitlab_user)
            gitlab_username_dict[gitlab_user['username']] = deepcopy(gitlab_user)
            gitlab_name_dict[gitlab_user['name']] = deepcopy(gitlab_user)
            if gitlab_user_id not in gitlab_farm_users:
                gitlab_farm_users[gitlab_user_id] = username

    result_data = {'farm_users': farm_users, 'farm_developers': farm_developers, 'gitlab_users': gitlab_user_dict,
                   'gitlab_name_dict': gitlab_name_dict,
                   'gitlab_username_dict': gitlab_username_dict,
                   'gitlab_farm_users': gitlab_farm_users}
    return api_success(data=result_data)
