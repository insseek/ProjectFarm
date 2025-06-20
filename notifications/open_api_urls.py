from django.urls import include, path

from notifications import open_api

app_name = 'notifications_open_api'
urlpatterns = [
    path(r'feishu/message/send', open_api.send_feishu_message, name='send_feishu_message'),

    path(r'bug_message/send', open_api.send_bug_message_to_developers, name='send_bug_message_to_developers'),

    path(r'cicd_message/send', open_api.send_cicd_failed_message, name='send_cicd_message_to_developers'),
    path(r'cicd_message/failed/send', open_api.send_cicd_failed_message, name='send_cicd_failed_message'),
    path(r'cicd_message/passed/send', open_api.send_cicd_passed_message, name='send_cicd_passed_message'),

    path(r'gitlab_project/farm_projects', open_api.get_projects_by_gitlab_project,
         name='get_projects_by_gitlab_project'),
    path(r'gitlab_user/farm_users', open_api.get_farm_users_by_gitlab_user,
         name='get_farm_users_by_gitlab_user'),

    path(r'feishu/send/farm_users', open_api.send_feishu_message_to_farm_users,
         name='send_feishu_message_to_farm_users'),
    # path(r'feishu/send/developers', open_api.send_feishu_message_to_developers,
    #      name='send_feishu_message_to_developers'),

    path(r'dysms/send/farm_users', open_api.send_dysms_to_farm_users,
         name='send_dysms_to_farm_users'),

    path(r'dysms/cicd_failed/send/farm_users', open_api.send_cicd_failed_message_to_farm_users,
         name='send_cicd_failed_message_to_farm_users'),
    path(r'dysms/cicd_passed/send/farm_users', open_api.send_cicd_passed_message_to_farm_users,
         name='send_cicd_passed_message_to_farm_users'),

]
