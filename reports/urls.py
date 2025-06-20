from django.urls import path

from reports import views, api

app_name = 'reports'
urlpatterns = [
    path(r'pv/', views.reports_pv, name='pv'),
    path(r'mindmap/view/', views.mindmap_view, name='mindmap_view'),
    path(r'<str:uid>/edit/', views.new_report, name='new_report'),
    path(r'<str:uid>/pdf/', views.pdf, name='pdf'),
    path(r'<str:uid>/preview/', views.preview, name='preview'),
    path(r'<str:uid>/', views.view, name='view'),
]
