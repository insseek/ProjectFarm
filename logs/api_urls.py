from django.urls import path

from . import api

app_name = 'logs_api'
urlpatterns = [
    path(r'', api.LogList.as_view(), name='list'),
    path(r'browsing_histories', api.BrowsingHistoryList.as_view(), name='browsing_history_list'),
    path(r'browsing_histories/<int:id>/done', api.finish_browsing_history, name='browsing_history_done'),
]
