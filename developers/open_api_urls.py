from django.urls import path
from developers import open_api
from projects import api as projects_api
from notifications import api as notifications_api
from developers import api as developers_api
from oauth import api as oauth_api

app_name = 'developers_open_api'
urlpatterns = [
    # path(r'list', open_api.DeveloperList.as_view(), name='list'),
    # 登录/退出
    path(r'phone/code', open_api.phone_code, name='phone_code'),

    path(r'login/one_time/authentication', open_api.one_time_authentication_login,
         name='one_time_authentication_login'),

    path(r'login', open_api.login_handle, name='login'),
    path(r'logout', open_api.logout_handle, name='logout'),
    # 个人信息
    path(r'me', open_api.my_info, name='my_info'),
    path(r'me/avatar', open_api.my_avatar, name='my_avatar'),
    path(r'me/status', open_api.developer_status, name='status'),
    path(r'me/edit', open_api.edit_my_info, name='edit_my_info'),
    path(r'me/star_rating', open_api.my_star_rating, name='my_star_rating'),

    #  获取每个工程师个人信息 :
    path(r'gitlab/personal/info', open_api.get_gitlab_developer_info, name='gitlab_developer_info'),

    path(r'development_guides', open_api.development_guides, name='development_guides'),
    # 项目
    path(r'projects/mine', open_api.my_projects, name='my_projects'),

    path(r'projects/<int:project_id>', open_api.project_detail, name='project_detail'),
    path(r'projects/<int:project_id>/task_topics', open_api.project_task_topics, name='project_task_topics'),

    # path(r'projects/<int:project_id>/issues', open_api.project_issues, name='project_issues'),

    path(r'projects/<int:project_id>/payments', open_api.project_payments, name='project_payments'),
    # 【code explain】【工程师评分】
    path(r'projects/jobs/mine', open_api.projects_my_jobs, name='projects_my_jobs'),
    path(r'projects/<int:project_id>/jobs/mine', open_api.project_my_jobs, name='project_my_jobs'),
    # 【code explain】【工程师评分】
    path(r'projects/<int:project_id>/my_star_ratings', open_api.project_my_star_ratings,
         name='project_my_star_ratings'),
    # 【code explain】【工程师评分】

    path(r'projects/<int:project_id>/bugs/mine', open_api.project_my_bugs, name='project_my_bugs'),

    path(r'projects/<int:project_id>/members', open_api.project_members, name='project_members'),
    path(r'projects/<int:project_id>/developers', open_api.project_developers, name='project_job_positions'),

    path(r'projects/<int:project_id>/daily_works/statistics/mine', open_api.my_project_daily_works_statistics,
         name='my_project_daily_works_statistics'),

    path(r'projects/<int:project_id>/tasks/today/mine', open_api.my_project_today_tasks,
         name='my_project_today_tasks'),

    path(r'projects/<int:project_id>/daily_works/today/punch', open_api.punch_today_daily_work,
         name='punch_today_daily_work'),

    path(r'projects/<int:project_id>/daily_works/today/punch_data', open_api.project_today_daily_work_data,
         name='project_today_daily_work_data'),

    path(r'projects/<int:project_id>/daily_works/day', open_api.project_day_daily_work,
         name='project_day_daily_work'),

    path(r'projects/<int:project_id>/daily_works/last', open_api.project_developer_last_daily_work,
         name='project_developer_last_daily_work'),

    path(r'projects/<int:project_id>/daily_works/statistics', open_api.project_developer_daily_work_statistics,
         name='project_developer_daily_work_statistics'),

    path(r'projects/daily_works/<int:daily_work_id>', open_api.daily_work_detail,
         name='daily_work_detail'),

    # path(r'projects/<int:project_id>/daily_works/statistics', open_api.project_developer_daily_works_statistics,
    #      name='project_developer_daily_work_statistics'),

    # 项目甘特图
    path(r'gantt_charts/<str:uid>', open_api.ProjectGanttDetail.as_view(),
         name='gantt_chart_detail'),
    path(r'gantt_charts/<str:uid>/tasks', open_api.project_gantt_tasks,
         name='project_gantt_tasks'),

    path(r'gantt_charts/task_topics/<int:topic_id>/dev/toggle_done', open_api.gantt_task_dev_toggle_done,
         name='gantt_task_dev_toggle_done'),

    # gitlab第三方
    path(r'oauth/gitlab/bind/redirect/data', open_api.gitlab_bind_redirect_data, name='gitlab_bind_redirect_data'),
    path(r'oauth/gitlab/bind', open_api.gitlab_bind, name='gitlab_bind'),

    path(r'oauth/gitlab/login/redirect/data', open_api.gitlab_login_redirect_data, name='gitlab_login_redirect_data'),
    path(r'oauth/gitlab/login', open_api.gitlab_login, name='gitlab_login'),

    path(r'oauth/gitlab/unbind', open_api.gitlab_oauth_unbind, name='gitlab_oauth_unbind'),

    # 飞书第三方
    path(r'oauth/feishu/bind/redirect/data', oauth_api.feishu_bind_redirect_data, name='feishu_bind_redirect_data'),
    path(r'oauth/feishu/bind', oauth_api.feishu_bind, name='feishu_bind'),
    path(r'oauth/feishu/unbind', oauth_api.feishu_unbind, name='feishu_unbind'),

    # 消息通知
    path(r'notifications/mine', open_api.MyNotificationList.as_view(), name='my_notifications'),
    path(r'notifications/mine/read', open_api.read_my_notifications, name='read_my_notifications'),
    path(r'notifications/<int:notification_id>/read', open_api.read, name='read_notification'),
    path(r'notifications/send', notifications_api.send_notifications, name='send_notifications'),

    path(r'documents/mine', open_api.my_developer_documents, name='my_developer_documents'),
    path(r'documents/versions/<int:id>/read', open_api.read_document_version,
         name='read_document_version'),

    path(r'me/oauth/real_name', open_api.developer_real_name_auth, name='developer_real_name_auth'),

]
