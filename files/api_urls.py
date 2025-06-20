from django.urls import path

from . import api

app_name = 'files_api'
urlpatterns = [
    path(r'', api.FileList.as_view(), name='list'),
    path(r'upload', api.FileList.as_view(), name='upload'),
    path(r'<int:id>', api.FileDetail.as_view(), name='detail'),
    path(r'public', api.PublicFileList.as_view(), name='public_list'),
    path(r'public/<int:id>', api.PublicFileDetail.as_view(), name='public_detail'),
]
