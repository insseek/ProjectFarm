import json
from pprint import pprint

from django.core.cache import cache
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response

from geargitlab.tasks import crawl_gitlab_user_data, crawl_all_gitlab_projects, crawl_all_gitlab_active_users, \
    reset_gitlab_data, crawl_recent_updated_gitlab_projects, crawl_farm_projects_recent_half_hour_git_demo_commits, \
    crawl_farm_projects_recent_days_git_issues


@api_view(['GET'])
def gitlab_user(request, gitlab_user_id):
    gitlab_users = cache.get('gitlab-users', {})
    if gitlab_user_id:
        if gitlab_user_id in gitlab_users:
            user_data = gitlab_users[gitlab_user_id]
        else:
            user_data = crawl_gitlab_user_data(gitlab_user_id)
        if user_data:
            return Response({"result": True, "data": user_data})
        return Response({"result": False, 'message': 'Not Fount'})
    return Response({"result": False, 'message': '用户名为必填'})


@api_view(['GET'])
def gitlab_projects_groups(request):
    gitlab_projects = cache.get('gitlab-projects', {})
    gitlab_groups = cache.get('gitlab-groups', {})

    if not gitlab_projects or not gitlab_groups:
        crawl_all_gitlab_projects.delay()
    else:
        crawl_recent_updated_gitlab_projects.delay()

    projects = sorted(gitlab_projects.values(), key=lambda x: x['id'], reverse=True)
    groups = sorted(gitlab_groups.values(), key=lambda x: x['id'], reverse=True)

    return Response({"result": True, "data": {'projects': projects, 'groups': groups}})


@api_view(['GET'])
def gitlab_users_data(request):
    users = cache.get('gitlab-users', None)
    if not users:
        users = crawl_all_gitlab_active_users()
    else:
        crawl_all_gitlab_active_users.delay()
    user_list = [user for user in users.values() if not user['is_admin']]
    users_data = sorted(user_list, key=lambda x: x['id'], reverse=True)
    # users_data = sorted(users.values(), key=lambda x: x['id'], reverse=True)
    return Response({"result": True, "data": users_data})


@api_view(['GET'])
def data_migrate(request):
    reset_gitlab_data()
    return Response({"result": True, "data": None})
