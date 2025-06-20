from django.urls import path

from comments import api

app_name = 'comments_api'
urlpatterns = [
    path(r'', api.CommentList.as_view(), name='list'),
    path(r'<int:id>', api.CommentDetail.as_view(), name='detail'),
    path(r'<int:id>/stick', api.stick_the_comment, name='stick_the_comment'),
    path(r'<int:id>/stick/cancel', api.cancel_the_top, name='cancel_the_top'),
]
