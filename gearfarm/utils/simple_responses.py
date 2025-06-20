# -*- coding:utf-8 -*-
import json
from django.http import JsonResponse

from rest_framework.response import Response
from rest_framework.status import HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_401_UNAUTHORIZED, \
    HTTP_402_PAYMENT_REQUIRED, HTTP_400_BAD_REQUEST, \
    HTTP_500_INTERNAL_SERVER_ERROR, HTTP_200_OK
from rest_framework import status
from rest_framework.pagination import PageNumberPagination

RESPONSE_STATUS = [200, 400, 401, 403, 404, 500]
RESULT_CODE_DICT = {
    200: {
        '0': '成功',
    },
    400: {
        '10000': '请求参数无效',
        '10001': '资源存在，无需重复创建',
        '10002': '参数缺失',
    },
    401: {
        '10100': '用户需要登录：Token无效或缺失',
        '10101': '用户冻结',
        '10102': 'Token无效',
        '10103': 'Token缺失',
        '10104': 'Authentication Key无效',
        '10105': 'Token过期'
    },
    403: {
        '10300': '没有权限访问',
        '10301': '权限密钥无效',
    },
    404: {
        '10400': '所请求的资源不存在'
    },
    500: {
        '10500': '系统错误'
    }
}


# 基于rest_framework的Response
def api_success(data=None, headers=None, result_status=None):
    result_status = result_status or HTTP_200_OK
    return Response(data, status=result_status, headers=headers)


def api_created_success(data=None, headers=None):
    return Response(data, status=status.HTTP_201_CREATED, headers=headers)


def api_bad_request(message='', data=None):
    if not data:
        if not message:
            message = '请求参数有误'
        data = {'detail': str(message)}
    return Response(data, status=HTTP_400_BAD_REQUEST)


def api_request_params_required(params):
    if not params:
        message = '检查请求参数是否完整'
    else:
        if isinstance(params, str):
            params = (params,)
        message = '参数：{}为必填'.format('，'.join(params))
    return Response({'detail': str(message)}, status=HTTP_400_BAD_REQUEST)


def api_repeated_request(message=''):
    if not message:
        message = '资源存在，无需重复创建'
    return Response({'detail': str(message)}, status=HTTP_400_BAD_REQUEST)


def api_unauthorized(message=''):
    if not message:
        message = 'Token无效或缺失'
    return Response({'detail': str(message)}, status=HTTP_401_UNAUTHORIZED)


def api_invalid_authentication_key(message=''):
    if not message:
        message = 'Authentication Key无效'
    return Response({'detail': str(message)}, status=HTTP_401_UNAUTHORIZED)


def api_authentication_expired(message=''):
    if not message:
        message = 'Token过期'
    return Response({'detail': str(message)}, status=HTTP_401_UNAUTHORIZED)


def api_suspended(message=''):
    if not message:
        message = '用户冻结'
    return Response({'detail': str(message)}, status=HTTP_401_UNAUTHORIZED)


def api_permissions_required(permissions=None):
    if not permissions:
        message = '没有权限访问'
    else:
        if isinstance(permissions, str):
            permissions = (permissions,)
        message = '缺失权限：{}'.format('，'.join(permissions))
    return Response({'detail': str(message)}, status=HTTP_403_FORBIDDEN)


def api_invalid_permission_key(message=''):
    if not message:
        message = '权限验证失败'
    return Response({'detail': str(message)}, status=HTTP_403_FORBIDDEN)


def api_invalid_app_id(message=''):
    if not message:
        message = 'app_id无效'
    return Response({'detail': str(message)}, status=HTTP_403_FORBIDDEN)


def api_not_found(message=''):
    if not message:
        message = '所请求的资源不存在'
    return Response({'detail': str(message)}, status=HTTP_404_NOT_FOUND)


def api_error(message=''):
    if not message:
        message = '系统错误'
    return Response({'detail': str(message)}, status=HTTP_500_INTERNAL_SERVER_ERROR)


# 基于Django的JsonResponse
def json_response_success(data=None):
    return JsonResponse(data, status=200, json_dumps_params={'ensure_ascii': False})


def json_response_bad_request(message=''):
    if not message:
        message = '检查请求参数'
    return JsonResponse({'detail': str(message)}, status=400, json_dumps_params={'ensure_ascii': False})


def json_response_repeated_request(message=''):
    if not message:
        message = '资源存在，无需重复创建'
    return JsonResponse({'detail': str(message)}, status=400, json_dumps_params={'ensure_ascii': False})


def json_response_unauthorized(message=''):
    if not message:
        message = 'Token无效或缺失'
    return JsonResponse({'detail': str(message)}, status=401, json_dumps_params={'ensure_ascii': False})


def json_response_invalid_authentication_key(message=''):
    if not message:
        message = 'Authentication Key无效'
    return JsonResponse({'detail': str(message)}, status=401, json_dumps_params={'ensure_ascii': False})


def json_response_authentication_expired(message=''):
    if not message:
        message = 'Token过期'
    return JsonResponse({'detail': str(message)}, status=401, json_dumps_params={'ensure_ascii': False})


def json_response_suspended(message=''):
    if not message:
        message = '用户冻结'
    return JsonResponse({'detail': str(message)}, status=401, json_dumps_params={'ensure_ascii': False})


def json_response_request_params_required(params):
    if not params:
        message = '检查请求参数是否完整'
    else:
        if isinstance(params, str):
            params = (params,)
        message = '缺失参数：{}'.format('，'.join(params))
    return JsonResponse({'detail': str(message)}, status=400, json_dumps_params={'ensure_ascii': False})


def json_response_permissions_required(permissions=None):
    if not permissions:
        message = '没有权限访问'
    else:
        if isinstance(permissions, str):
            permissions = (permissions,)
        message = '缺失权限：{}'.format('，'.join(permissions))
    return JsonResponse({'detail': str(message)}, status=403, json_dumps_params={'ensure_ascii': False})


def json_response_invalid_permission_key(message=''):
    if not message:
        message = '权限验证失败'
    return JsonResponse({'detail': str(message)}, status=403, json_dumps_params={'ensure_ascii': False})


def json_response_not_found(message=''):
    if not message:
        message = '所请求的资源不存在'
    return JsonResponse({'detail': str(message)}, status=404, json_dumps_params={'ensure_ascii': False})


def json_response_error(message=''):
    if not message:
        message = '系统错误'
    return JsonResponse({'detail': str(message)}, status=500, json_dumps_params={'ensure_ascii': False})


def build_pagination_response(request, queryset, serializer_class):
    data, headers = build_pagination_queryset_data(request, queryset, serializer_class)
    return api_success(data=data, headers=headers)


def build_pagination_queryset_data(request, queryset, serializer_class):
    page = request.GET.get('page', None)
    page_size = request.GET.get('page_size', None)
    total = len(queryset)
    headers = None
    if page and page_size:
        paginator = PageNumberPagination()
        paginator.page_size_query_param = 'page_size'
        queryset = paginator.paginate_queryset(queryset, request)
        pagination_params = json.dumps({'total': total, 'page': int(page), 'page_size': int(page_size)})
        headers = {'X-Pagination': pagination_params,
                   'Access-Control-Expose-Headers': 'X-Pagination'}
    data = serializer_class(queryset, many=True).data
    return data, headers
