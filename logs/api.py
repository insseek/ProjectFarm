import json
import re
from copy import deepcopy

from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view

from gearfarm.utils import farm_response
from logs.models import Log, BrowsingHistory
from logs.serializers import LogSerializer, BrowsingHistorySerializer
from logs.tasks import get_browsing_history_visitor_address
from projects.models import ProjectPrototype
from reports.models import Report

from gearfarm.utils import farm_response
from gearfarm.utils import simple_responses


def get_paginate_queryset(data, page, page_size):
    if page and page_size:
        page = int(page)
        page_size = int(page_size)
        start_index = int(page - 1) * int(page_size)
        end_index = int(page) * int(page_size)
        if start_index < 0:
            start_index = 0
        if end_index < 0:
            end_index = 0
        data = data[start_index:end_index]
    return data


class LogList(APIView):
    """
    List all log, or create a new log.
    """

    @method_decorator(cache_page(60 * (0 if settings.DEVELOPMENT else 1)))
    def get(self, request, format=None):
        response_choices = farm_response
        if request.path.startswith('/api/v1/testing'):
            response_choices = simple_responses
        params = request.GET
        if not {"app_label", 'model', 'object_id'}.issubset(set(params.keys())):
            return response_choices.api_bad_request(
                "参数为必填 [app_label, model, object_id]")
        content_type = ContentType.objects.filter(app_label=params['app_label'], model=params['model'])
        if not content_type.exists():
            return farm_response.api_not_found("model不存在")
        content_type = content_type.first()
        object_id = int(params['object_id'])

        codename = params.get('codename', '')
        if codename:
            codename = re.sub(r'[;；,，]', ' ', codename).split()
        queryset = Log.objects.filter(content_type_id=content_type.id, object_id=object_id)
        if codename:
            queryset = queryset.filter(codename__in=codename)

        reverse = False
        order_by = params.get('order_by', 'created_at')
        order_dir = params.get('order_dir', 'desc')
        if order_dir == 'desc':
            reverse = True
            order_by = '-' + order_by
        queryset = queryset.order_by(order_by)
        # 获取分组后排序列表
        created_date_list = [created_date for created_date in set(queryset.values_list('created_date', flat=True)) if
                             created_date]
        sorted_date_list = sorted(created_date_list, reverse=reverse)
        total = len(sorted_date_list)
        page = params.get('page', None)
        page_size = params.get('page_size', None)
        if total and page and page_size:
            sorted_date_list = get_paginate_queryset(sorted_date_list, page, page_size)
            end_date = sorted_date_list[0] if reverse else sorted_date_list[-1]
            start_date = sorted_date_list[-1] if reverse else sorted_date_list[0]
            queryset = queryset.filter(created_date__lte=end_date, created_date__gte=start_date)
        result = []
        for date in sorted_date_list:
            date_queryset = queryset.filter(created_date=date)
            if date_queryset.exists():
                data = LogSerializer(date_queryset, many=True).data
                result.append({"date": date.strftime(settings.DATE_FORMAT), 'data': data})
                queryset = queryset.exclude(created_date=date)
        headers = None
        if page and page_size:
            pagination_params = json.dumps({'total': total, 'page': int(page), 'page_size': int(page_size)})
            headers = {'X-Pagination': pagination_params,
                       'Access-Control-Expose-Headers': 'X-Pagination'}
        return response_choices.api_success(data=result, headers=headers)


class BrowsingHistoryList(APIView):
    """
    List all BrowsingHistory, or create a new BrowsingHistory.
    """

    @method_decorator(cache_page(60 * 15))
    def get(self, request, format=None):
        params = request.GET
        if not {"app_label", 'model', 'object_id'}.issubset(set(params.keys())):
            return farm_response.api_bad_request(
                "参数为必填 [app_label, model, object_id]")

        content_type = ContentType.objects.filter(app_label=params['app_label'], model=params['model'])
        if not content_type.exists():
            return farm_response.api_not_found("model不存在")
        content_type = content_type.first()
        object_id = int(params['object_id'])

        logs = BrowsingHistory.objects.filter(content_type_id=content_type.id,
                                              object_id=object_id).order_by('-created_at')

        # 获取分组后排序列表
        created_date_list = [created_date for created_date in set(logs.values_list('created_date', flat=True)) if
                             created_date]
        sorted_date_list = sorted(created_date_list, reverse=True)
        total = len(sorted_date_list)
        page = params.get('page', None)
        page_size = params.get('page_size', None)
        if total and page and page_size:
            page = int(page)
            page_size = int(page_size)
            # 获取分页 起始 和 结束位置
            group_start = int(page - 1) * int(page_size)
            group_end = int(page) * int(page_size) - 1
            if group_start < 0:
                group_start = 0
            if group_end < 0:
                group_end = 0
            end_date = sorted_date_list[group_start]
            start_date = sorted_date_list[group_end]
            sorted_date_list = sorted_date_list[group_start:group_end + 1]
            logs = logs.filter(created_date__lte=end_date, created_date__gte=start_date)
        result = []
        for date in sorted_date_list:
            date_logs = logs.filter(created_date=date)
            if date_logs.exists():
                data = BrowsingHistorySerializer(date_logs, many=True).data
                result.append({"date": date.strftime('%Y.%m.%d'), 'data': data})
                logs = logs.exclude(created_date=date)
        return Response({'result': True, 'data': result, 'total': total, 'page': page})

    def post(self, request, format=None):
        request_data = deepcopy(request.data)
        if not {"app_label", 'model', 'object_id'}.issubset(set(request_data.keys())):
            return farm_response.api_bad_request(
                "参数为必填 [app_label, model, object_id]")
        content_type = ContentType.objects.filter(app_label=request_data['app_label'], model=request_data['model'])
        if not content_type.exists():
            return farm_response.api_not_found("model不存在")
        content_type = content_type.first()
        object_id = int(request_data['object_id'])
        request_data['content_type'] = content_type.id
        request_data['object_id'] = object_id

        model_class = content_type.model_class()
        current_object = get_object_or_404(model_class, id=object_id)

        visitor = request.user
        top_user = request.top_user
        ip_address = request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR')
        browsing_seconds = request_data.get('browsing_seconds', None)
        browsing_history = BrowsingHistory.build_log(visitor, current_object, ip_address, browsing_seconds,
                                                     top_user=top_user)
        if browsing_history:
            if not settings.DEVELOPMENT:
                get_browsing_history_visitor_address.delay(browsing_history.id)
            return farm_response.api_success(data=BrowsingHistorySerializer(browsing_history).data)
        return farm_response.api_bad_request()


@api_view(['POST'])
def finish_browsing_history(request, id):
    browsing_history = get_object_or_404(BrowsingHistory, pk=id)
    browsing_history.done_at = timezone.now()
    if request.data.get('browsing_seconds', None):
        browsing_history.browsing_seconds = request.data['browsing_seconds']
    if not browsing_history.user_id and request.top_user:
        browsing_history.user = request.top_user
    browsing_history.save()
    return Response({'result': True})
