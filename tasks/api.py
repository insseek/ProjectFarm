from copy import deepcopy
from datetime import datetime, timedelta
import re
import logging
import json

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.conf import settings
from django.contrib.auth.models import User, Group
from django.shortcuts import get_object_or_404, reverse
from django.utils import timezone
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import api_view
from taggit.models import Tag

from gearfarm.utils.page_path_utils import build_page_path
from farmbase.utils import get_protocol_host
from gearfarm.utils import farm_response
from gearfarm.utils.farm_response import api_bad_request, api_success
from projects.models import Project
from proposals.models import Proposal
from tasks.serializers import TaskSerializer, TaskEditSerializer
from logs.models import Log
from notifications.utils import create_notification
from tasks.models import Task
from notifications.tasks import send_tasks_update_to_principal, send_task_auto_update_reminder
# from tasks.utils import get_tasks_tag_and_content_dict
from clients.models import Lead
from tasks.tasks import regular_contract_payments_auto_tasks

logger = logging.getLogger()


class TaskList(APIView):
    def get(self, request):
        # 某项目、需求的任务  或 全部任务
        tasks = Task.objects.all()

        params = request.GET
        if {"app_label", 'model', 'object_id'}.issubset(set(params.keys())):
            content_type = ContentType.objects.filter(app_label=params['app_label'], model=params['model'])
            if not content_type.exists():
                return farm_response.api_not_found("model不存在")
            content_type = content_type.first()
            object_id = int(params['object_id'])
            tasks = tasks.filter(content_type_id=content_type.id, object_id=object_id)

        is_mine = params.get('is_mine') in ['1', 'true', 'True', 1, True]
        principal = params.get('principal', None)
        done_value = params.get('is_done') if 'is_done' in params else params.get('done')
        is_done = True if done_value in ['1', 'true', 'True', 1, True] else False if done_value in ['0', 'False',
                                                                                                    'false', 0,
                                                                                                    False] else None
        has_personal = params.get('has_personal', None) in ['1', 'true', 'True', 1, True]
        group_type = params.get('group_type') in ['1', 'true', 'True', 1, True]
        search_value = params.get('search_value', None)

        # 我的任务 包含自己项目的任务
        if is_mine:
            manage_projects = request.user.manage_projects.all()
            my_project_tasks = None
            if manage_projects.exists():
                my_project_tasks = manage_projects.first().tasks.all()
                for project in manage_projects[1:]:
                    my_project_tasks = my_project_tasks | project.tasks.all()
            tasks = tasks.filter(principal_id=request.user.id)
            if my_project_tasks:
                tasks = tasks | my_project_tasks
            tasks = tasks.distinct()
        # 负责人
        if principal:
            tasks = tasks.filter(principal_id=principal)
        # 任务状态
        if is_done is not None:
            tasks = tasks.filter(is_done=is_done).order_by('expected_at')
            if is_done:
                tasks = tasks.order_by('-done_at')
            else:
                tasks = tasks.order_by('expected_at')

        # 检索任务 任务名 任务标签 任务
        if search_value:
            tasks = tasks.filter(
                Q(name__icontains=search_value) | (Q(content_type__model='lead') & Q(object_id__isnull=False) & Q(
                    leads__name__icontains=search_value)) |
                (Q(content_type__model='project') & Q(object_id__isnull=False) & Q(
                    projects__name__icontains=search_value)) |
                (Q(content_type__model='proposal') & Q(object_id__isnull=False) &
                 ((Q(proposals__name__isnull=False) & Q(proposals__name__icontains=search_value)) | (
                         Q(proposals__name__isnull=True) & Q(
                     proposals__description__icontains=search_value))))
            ).distinct()

        # 项目需求的任务
        content_tasks = None
        content_models = request.GET.get('content_models', None)
        if content_models:
            model_name_list = re.sub(r'[;；,，]', ' ', content_models).split()
            for model_name in model_name_list:
                model_object_list = re.sub(r'[;；,，]', ' ',
                                           request.GET.get(model_name, None)).split() if request.GET.get(model_name,
                                                                                                         None) else []
                if model_object_list:
                    model_tasks = tasks.filter(content_type__model=model_name).filter(object_id__in=model_object_list)
                    if content_tasks:
                        content_tasks = content_tasks | model_tasks.distinct()
                    else:
                        content_tasks = model_tasks.distinct()
        # 个人的任务
        personal_tasks = None
        if has_personal:
            personal_tasks = tasks.filter(Q(object_id__isnull=True) | Q(content_type__isnull=True)).distinct()

        # 标签筛选任务
        tags_tasks = None
        tags = request.GET.get('tags', None)
        if tags:
            tag_name_list = re.sub(r'[;；,，]', ' ', tags).split()
            tag_list = Tag.objects.filter(name__in=tag_name_list)
            tags_tasks = tasks.filter(tags__in=tag_list).distinct()

        if any([tags_tasks != None, personal_tasks != None, content_tasks != None]):
            tasks_set = Task.objects.filter(id__isnull=True).distinct()
            for task_set in [tags_tasks, personal_tasks, content_tasks]:
                if task_set:
                    tasks_set = tasks_set | task_set
                    tasks_set = tasks_set.distinct()
            tasks = tasks_set

        total = tasks.count()

        # 未完成任务分组
        if group_type and is_done is not None and not is_done:
            today = timezone.now().today().date()
            tasks_expired = tasks.filter(expected_at__lt=today)
            tasks_today = tasks.filter(expected_at=today)
            tasks_tomorrow = tasks.filter(expected_at=today + timedelta(days=1))
            tasks_days_after_tomorrow = tasks.filter(expected_at__gt=today + timedelta(days=1))
            tasks_data = {}
            tasks_data['total'] = total
            tasks_data['tasks_expired'] = TaskSerializer(tasks_expired, many=True).data
            tasks_data['tasks_today'] = TaskSerializer(tasks_today, many=True).data
            tasks_data['tasks_tomorrow'] = TaskSerializer(tasks_tomorrow, many=True).data
            tasks_data['tasks_days_after_tomorrow'] = TaskSerializer(tasks_days_after_tomorrow, many=True).data
            return farm_response.api_success(data=tasks_data)
        # 完成任务 分页
        return farm_response.build_pagination_response(request, tasks, TaskSerializer)

    def post(self, request):
        request_data = deepcopy(request.data)
        request_data['creator'] = request.user.id

        content_type = None
        if {"app_label", 'model', 'object_id'}.issubset(set(request_data.keys())):
            content_type = ContentType.objects.filter(app_label=request_data['app_label'], model=request_data['model'])
            if not content_type.exists():
                return farm_response.api_not_found("model不存在")
            content_type = content_type.first()
            request_data['content_type'] = content_type.id
            request_data['object_id'] = int(request_data['object_id'])

        serializer = TaskSerializer(data=request_data)
        if serializer.is_valid():
            task = serializer.save()
            tags = re.findall(r'#([^#]*?)#', task.name)
            if tags:
                for tag in tags:
                    if tag and tag.strip() != '':
                        task.tags.add(tag.strip())
            if request.user.id != task.principal_id:
                content = "收到一个新任务【{}】".format(task.name)
                url = get_protocol_host(request) + build_page_path("dashboard")
                create_notification(task.principal, content, url, priority="important")
            try:
                if task.principal_id:
                    send_tasks_update_to_principal.delay(task.principal_id)
                    send_tasks_update_to_principal.delay(task.principal_id)
                if task.content_object:
                    send_task_auto_update_reminder.delay(task.content_type.model, task.object_id)
                    send_task_auto_update_reminder.delay(content_type.model, task.object_id)
            except Exception as e:
                logger.error(e)
            Log.build_create_object_log(request.user, task, related_object=task.content_object)
            return Response({"result": True, 'data': serializer.data})
        return Response({'result': False, 'message': str(serializer.errors)})


class TaskDetail(APIView):
    """
    Retrieve, update or delete a task instance.
    """

    def get(self, request, id):
        task = get_object_or_404(Task, id=id)
        serializer = TaskSerializer(task)
        return Response({"result": True, 'data': serializer.data})

    def post(self, request, id):
        task = get_object_or_404(Task, id=id)
        serializer = TaskEditSerializer(task, data=request.data)
        if serializer.is_valid():
            origin = deepcopy(task)
            task = serializer.save()
            tags = re.findall(r'#([^#]*?)#', task.name)
            task.tags.clear()
            for tag in tags:
                if tag and tag.strip() != '':
                    task.tags.add(tag.strip())
            comment = request.data['update_comment']
            if request.user.id != task.principal_id:
                content = "{username}更新了任务：{task_name} \n期望完成时间:{expected_at}\n修改原因：{comment}".format(
                    username=request.user.username,
                    task_name=task.name,
                    expected_at=task.expected_at,
                    comment=comment)
                url = get_protocol_host(request) + '/'
                create_notification(task.principal, content, url, priority="important")
            send_tasks_update_to_principal.delay(task.principal.id)
            Log.build_update_object_log(request.user, origin, task, related_object=task.content_object, comment=comment)
            serializer = TaskSerializer(task)
            return Response({"result": True, 'data': serializer.data})
        return Response({"result": False, 'message': str(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
        task = get_object_or_404(Task, id=id)
        if task.auto_close_required:
            if not request.user.is_superuser:
                return api_bad_request("该自动创建的待办事项不能删除")
        origin = deepcopy(task)
        principal = task.principal
        task.delete()
        Log.build_delete_object_log(request.user, origin, origin.content_object)
        send_tasks_update_to_principal.delay(principal.id)
        return Response({"result": True})


@api_view(['POST'])
def toggle_done(request, id):
    task = get_object_or_404(Task, id=id)
    if task.auto_close_required:
        return api_bad_request("该自动创建的待办事项不能手动完成")
    if task.principal_id != request.user.id:
        return Response({'result': False, 'message': '不能切换他人任务状态'})
    origin = deepcopy(task)
    if task.done_at:
        task.done_at = None
        task.is_done = False
    else:
        task.done_at = timezone.now()
        task.is_done = True
    task.save()
    Log.build_update_object_log(request.user, origin, task, related_object=task.content_object)
    if task.principal_id and User.objects.filter(pk=task.principal_id,
                                                 is_active=True).exists():
        send_tasks_update_to_principal.delay(task.principal_id)
    return Response({'result': True})


@api_view(['POST'])
def finish_task(request, id):
    task = get_object_or_404(Task, id=id)
    if task.principal_id and User.objects.filter(pk=task.principal_id,
                                                 is_active=True).exists() and task.principal_id != request.user.id:
        return Response({'result': False, 'message': '不能完成他人任务状态'})
    if task.done_at:
        return Response({'result': False, 'message': '该任务已完成'})
    if task.auto_close_required:
        return api_bad_request("该自动创建的待办事项不能手动完成")

    origin = deepcopy(task)
    task.done_at = timezone.now()
    task.is_done = True
    task.save()
    Log.build_update_object_log(request.user, origin, task, related_object=task.content_object)
    if task.principal_id and User.objects.filter(pk=task.principal_id,
                                                 is_active=True).exists():
        send_tasks_update_to_principal.delay(task.principal_id)
    return Response({'result': True})


@api_view(['GET'])
def task_sources(request):
    user_id = request.user.id
    all_ongoing_projects = Project.ongoing_projects()
    all_ongoing_proposals = Proposal.ongoing_proposals()
    my_ongoing_leads = Lead.pending_leads()

    search_value = request.GET.get('search_value', None)
    if search_value:
        all_ongoing_proposals = all_ongoing_proposals.filter(
            Q(pm__username__icontains=search_value) | Q(bd__username__icontains=search_value) | \
            (Q(name__isnull=False) & Q(
                name__icontains=search_value)) | (
                (Q(name__isnull=True) & Q(
                    description__icontains=search_value))))

        all_ongoing_projects = all_ongoing_projects.filter(
            Q(name__icontains=search_value) | Q(manager__username__icontains=search_value))

        my_ongoing_leads = my_ongoing_leads.filter(name__icontains=search_value)

    my_ongoing_projects = all_ongoing_projects.filter(manager_id=user_id)
    my_ongoing_proposals = all_ongoing_proposals.filter(Q(pm_id=user_id) | Q(bd_id=user_id))
    other_ongoing_projects = all_ongoing_projects.exclude(manager_id=user_id)
    other_ongoing_proposals = all_ongoing_proposals.exclude(Q(pm_id=user_id) | Q(bd_id=user_id))
    my_ongoing_leads = my_ongoing_leads.filter(salesman_id=user_id)
    data = {
        "my_ongoing_leads": my_ongoing_leads.values('id', 'name'),
        "my_ongoing_projects": my_ongoing_projects.values('id', 'name'),
        "my_ongoing_proposals": my_ongoing_proposals.values('id', 'name', 'description'),
        "other_ongoing_projects": other_ongoing_projects.values('id', 'name'),
        "other_ongoing_proposals": other_ongoing_proposals.values('id', 'name', 'description'),
    }
    return Response({"result": True, "data": data, "message": ''})


@api_view(['GET'])
def data_migrate(request):
    regular_contract_payments_auto_tasks()
    return api_success()
