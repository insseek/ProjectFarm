from django.urls import path

from . import views

app_name = 'projects'
urlpatterns = [
    path(r'calendar/<str:uid>/', views.calendar_view, name='calendar_view'),  # 迁移前端新路由  兼容之前发给客户得瑟路由
    path(r'documents/<str:uid>/', views.download_documents, name='download_documents'),
]
