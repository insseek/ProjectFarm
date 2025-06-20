from django.urls import path

from . import api

app_name = 'tasks'
urlpatterns = [
    path(r'', api.TaskList.as_view(), name='list'),
    path(r'<int:id>', api.TaskDetail.as_view(), name='detail'),
    path(r'<int:id>/edit', api.TaskDetail.as_view(), name='edit_task'),
    path(r'<int:id>/toggle_done', api.toggle_done, name='toggle_done'),
    path(r'<int:id>/done', api.finish_task, name='finish_task'),
    path(r'sources', api.task_sources, name='sources'),
    path(r'sources/', api.task_sources, name='sources'),
    # path(r'mine/tags', api.my_tasks_tags, name='my_tasks_tags'),
    # path(r'tags/clear', api.clear_users_tasks_tags_cache, name='clear_users_tasks_tags_cache'),
    path(r'data/migrate', api.data_migrate, name='data_migrate')
]