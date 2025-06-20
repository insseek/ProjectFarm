from django.urls import include, path
from django.conf.urls.static import static
from django.contrib import admin
import django.contrib.auth.views
from django.conf import settings
from django.contrib.auth.views import LoginView, LogoutView
import farmbase.api
import farmbase.views
import projects.views
import projects.api
import developers.open_api

admin.autodiscover()

urlpatterns = [

                  # SSO端开始
                  path(r'api/v1/auth_top/', include('auth_top.api_urls', namespace='auth_top_api')),
                  # SSO端结束

                  # 客户Web端开始
                  path(r'open_api/v1/client/', include('clients.open_api_urls', namespace='clients_open_api')),
                  # 客户Web结束

                  # 工程师Web端开始
                  path(r'open_api/v1/developer/comments/',
                       include('comments.api_urls', namespace='developers_open_api_comments')),
                  path(r'open_api/v1/developer/', include('developers.open_api_urls', namespace='developers_open_api')),
                  # 工程师Web结束

                  # 工程师文档端开始
                  path(r'api/v1/document/documents/mine', developers.open_api.my_developer_documents,
                       name='my_developer_documents'),
                  path(r'api/v1/document/documents/versions/<int:id>/read', developers.open_api.read_document_version,
                       name='read_document_version'),
                  # 工程师文档端结束

                  # GearTest开始
                  path(r'api/v1/testing/', include('testing.api_urls', namespace='testing_api')),
                  path(r'api/v1/testing/comments/', include('comments.api_urls', namespace='testing_comments_api')),
                  path(r'api/v1/testing/notifications/',
                       include('notifications.api_urls', namespace='testing_notifications_api')),
                  path(r'api/v1/testing/logs/', include('logs.api_urls', namespace='testing_logs_api')),
                  path(r'api/v1/testing/files/', include('files.api_urls', namespace='testing_files_api')),
                  # GearTest结束

                  # 后台管理开始
                  path(r'admin/doc/', include('django.contrib.admindocs.urls')),
                  path(r'admin/', admin.site.urls),
                  # 后台管理结束

                  # Farm接口开始
                  path(r'api/documents', farmbase.api.DocumentList.as_view(), {"is_mine": True}, name='documents_api'),

                  # 用户
                  # path(r'users/', include('farmbase.urls', namespace='farmbase_users')),
                  path(r'api/users/', include('farmbase.api_urls', namespace='farmbase_users_api')),
                  # 开放的几个接口（（TPM的运维部署查询用户）
                  path(r'open_api/v1/users/', include('farmbase.open_api_urls', namespace='farmbase_users_open_api')),
                  # 短链接
                  path(r'api/short_url', farmbase.api.get_short_url, name='get_short_url'),
                  # 客户管理
                  # path(r'clients/', include('clients.urls', namespace='clients')),
                  path(r'api/clients/', include('clients.api_urls', namespace='clients_api')),
                  # 通用评论
                  path(r'api/comments/', include('comments.api_urls', namespace='comments_api')),
                  # 仪表盘数据聚合
                  path(r'api/dashboard/', include('dashboard.api_urls', namespace='dashboard_api')),
                  # 开发者管理
                  # path(r'developers/', include('developers.urls', namespace='developers')),
                  path(r'api/developers/', include('developers.api_urls', namespace='developers_api')),
                  # 导出文件
                  path(r'api/exports/', include('exports.api_urls', namespace='exports_api')),
                  # 通用附件
                  # path(r'files/', include('files.urls', namespace='files')),
                  path(r'api/files/', include('files.api_urls', namespace='files_api')),
                  # 财务
                  # path(r'finance/', include('finance.urls', namespace='finance')),
                  path(r'api/finance/', include('finance.api_urls', namespace='finance_api')),

                  # 发送邮件
                  # path(r'gearmail/', include('gearmail.urls', namespace='gearmail')),
                  path(r'api/gearmail/', include('gearmail.api_urls', namespace='gearmail_api')),

                  # 通用操作记录
                  path(r'api/logs/', include('logs.api_urls', namespace='logs_api')),

                  # 站内信 消息中心
                  # path(r'notifications/', include('notifications.urls', namespace='notifications')),
                  path(r'api/notifications/', include('notifications.api_urls', namespace='notifications_api')),
                  # 开放几个推送消息的API（TPM的运维部署）
                  path(r'open_api/v1/notifications/', include('notifications.open_api_urls'),
                       name='notifications_open_api'),

                  # 一些第三方gitlab、飞书、wechat
                  # path(r'oauth/', include('oauth.urls', namespace='oauth')),
                  path(r'api/oauth/', include('oauth.api_urls', namespace='oauth_api')),

                  # 需求 项目playbook
                  path(r'api/playbook/', include('playbook.api_urls', namespace='playbook_api')),
                  # path(r'playbook/', include('playbook.urls', namespace='playbook')),

                  # 项目
                  path(r'projects/', include('projects.urls', namespace='projects')),
                  path(r'api/projects/', include('projects.api_urls', namespace='projects_api')),
                  # 开放一个查询项目部署状态接口（TPM的运维部署）
                  path(r'open_api/v1/projects/', include('projects.open_api_urls'),
                       name='projects_open_api'),
                  # 需求
                  # path(r'proposals/', include('proposals.urls', namespace='proposals')),
                  path(r'api/proposals/', include('proposals.api_urls', namespace='proposals_api')),

                  # 原型参考
                  # path(r'prototypes/references/', include('prototypes.urls', namespace='prototypes')),
                  path(r'api/prototypes/references/', include('prototypes.api_urls', namespace='prototypes_api')),

                  # 报告
                  path(r'reports/', include('reports.urls', namespace='reports')),
                  path(r'api/reports/', include('reports.api_urls', namespace='reports_api')),

                  # 通用任务TODO
                  # path(r'tasks/', include('tasks.urls', namespace='tasks')),
                  path(r'api/tasks/', include('tasks.api_urls', namespace='tasks_api')),

                  # 华为语音通话及录音文件管理 暂时不用了
                  # path(r'webphone/', include('webphone.urls', namespace='webphone')),
                  path(r'api/webphone/', include('webphone.api_urls', namespace='webphone_api')),

                  # 工单
                  # path(r'workorder/', include('workorder.urls', namespace='workorder')),
                  path(r'api/workorder/', include('workorder.api_urls', namespace='workorder_api')),

                  # gitlab
                  path(r'api/gitlab/', include('geargitlab.api_urls', namespace='geargitlab_api')),

                  # 分享版甘特图的接口
                  path(r'api/ganttcharts/<str:uid>/tasks', projects.api.project_gantt_tasks,
                       name='project_gantt_tasks'),
                  path(r'api/ganttcharts/<str:uid>', projects.api.ProjectGanttDetail.as_view(),
                       name='gantt_chart_detail'),
                  # 临时迁移数据的一个接口
                  path(r'api/data/migrate', farmbase.api.data_migrate, name='data_migrate'),
                  path(r'404/', farmbase.views.not_found,
                       name='not_found'),
                  path(r'', farmbase.views.home, name='home'),
                  # path(r'silk/', include('silk.urls', namespace='silk'))

              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + static(settings.STATIC_URL,
                                                                                         document_root=settings.STATIC_ROOT)
handler404 = "farmbase.views.not_found"

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        path(r'__debug__/', include(debug_toolbar.urls)),
    ]
