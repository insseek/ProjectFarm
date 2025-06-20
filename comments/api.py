from copy import deepcopy
import re

from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.shortcuts import get_object_or_404, reverse
from django.core.cache import cache

from rest_framework.views import APIView
from rest_framework.decorators import api_view

from comments.models import Comment
from comments.serializers import CommentSerializer
from notifications.utils import create_notification, create_notification_group
from notifications.notification_factory import NotificationFactory
from farmbase.permissions_utils import has_function_perm
from farmbase.utils import get_protocol_host
from gearfarm.utils import farm_response
from gearfarm.utils import simple_responses


class CommentList(APIView):
    """
    List all comment, or create a new comment.
    """

    def get(self, request):
        response_choices = farm_response
        if request.path.startswith('/api/v1/testing'):
            response_choices = simple_responses

        params = request.GET
        if not {"app_label", 'model', 'object_id'}.issubset(set(params.keys())):
            return response_choices.api_bad_request(
                "参数为必填 [app_label, model, object_id]")

        content_type = ContentType.objects.filter(app_label=params['app_label'], model=params['model'])
        if not content_type.exists():
            return response_choices.api_not_found("model不存在")
        content_type = content_type.first()
        object_id = int(params['object_id'])

        order_by_list = ['-is_sticky']
        order_by = params.get('order_by', 'created_at')
        order_dir = params.get('order_dir', 'desc')
        codename = re.sub(r'[;；,，]', ' ', params.get('codename', '')).split() if params.get('codename', '') else ''
        comments = Comment.objects.filter(content_type_id=content_type.id, object_id=object_id,
                                          parent_id=None).order_by('-is_sticky')
        if codename:
            comments = comments.filter(codename__in=codename)

        if order_dir == 'desc':
            order_by = '-' + order_by
        order_by_list.append(order_by)
        comments = comments.order_by(*order_by_list)
        data = CommentSerializer(comments, many=True).data

        return response_choices.api_success(data=data)

    def post(self, request):
        response_choices = farm_response
        if request.path.startswith('/api/v1/testing'):
            response_choices = simple_responses

        request_data = deepcopy(request.data)
        if not {"app_label", 'model', 'object_id'}.issubset(set(request_data.keys())):
            return response_choices.api_bad_request(
                "参数为必填 [app_label, model, object_id]")
        content_type = ContentType.objects.filter(app_label=request_data['app_label'], model=request_data['model'])
        if not content_type.exists():
            return response_choices.api_not_found("model不存在")
        content_type = content_type.first()
        object_id = int(request_data['object_id'])
        request_data['content_type'] = content_type.id
        request_data['object_id'] = object_id

        if request.data.get('parent'):
            parent_id = request.data.get('parent')
            parent = Comment.objects.filter(pk=parent_id).first()
            if not parent:
                return response_choices.api_not_found("父级不存在")
            elif parent.content_type.id != content_type.id:
                return response_choices.api_bad_request("父级评论不属于同一个对象")
            elif parent.parent:
                return response_choices.api_bad_request("不支持二级以上评论")

        if request.user:
            request_data['author'] = request.user.id
        elif request.developer:
            request_data['developer'] = request.developer.id
        if request.top_user:
            request_data['creator'] = request.top_user.id

        serializer = CommentSerializer(data=request_data)
        if serializer.is_valid():
            comment = serializer.save()
            NotificationFactory.build_comment_notifications(comment, request.user)
            self.handle_schedule_remarks(comment)
            return response_choices.api_success(data=serializer.data)
        return response_choices.api_bad_request(str(serializer.errors))

    def handle_schedule_remarks(self, comment):
        if comment.content_type and comment.content_type.model == 'project' and comment.codename == 'schedule_remarks':
            project_schedule_remarks_hidden_set = cache.get('project_schedule_remarks_hidden_set', set())
            if comment.content_object.id in project_schedule_remarks_hidden_set:
                project_schedule_remarks_hidden_set.remove(comment.content_object.id)
                cache.set('project_schedule_remarks_hidden_set', project_schedule_remarks_hidden_set, None)


class CommentDetail(APIView):
    def get(self, request, id, format=None):
        response_choices = farm_response
        if request.path.startswith('/api/v1/testing'):
            response_choices = simple_responses

        comment = get_object_or_404(Comment, pk=id)
        serializer = CommentSerializer(comment, many=False)
        return response_choices.api_success({"result": True, "data": serializer.data})

    def delete(self, request, id, format=None):

        response_choices = farm_response
        if request.path.startswith('/api/v1/testing'):
            response_choices = simple_responses

        comment = get_object_or_404(Comment, pk=id)
        if request.user.id == comment.author_id or has_function_perm(request.user,
                                                                     'delete_comments') or request.user.is_superuser:
            comment.delete()
            return response_choices.api_success()
        return response_choices.api_bad_request('你没有权限删除该评论，请联系评论提交人或管理员')


@api_view(['POST'])
def stick_the_comment(request, id):
    response_choices = farm_response
    if request.path.startswith('/api/v1/testing'):
        response_choices = simple_responses

    comment = get_object_or_404(Comment, pk=id)
    if not comment.is_sticky:
        comment.is_sticky = True
        comment.save()
        return response_choices.api_success()


@api_view(['POST'])
def cancel_the_top(request, id):
    response_choices = farm_response
    if request.path.startswith('/api/v1/testing'):
        response_choices = simple_responses
    comment = get_object_or_404(Comment, pk=id)
    if comment.is_sticky:
        comment.is_sticky = False
        comment.save()
    return response_choices.api_success()
