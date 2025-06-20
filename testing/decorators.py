# -*- coding:utf-8 -*-
import json
from functools import wraps

from django.shortcuts import get_object_or_404
from django.utils import six
from django.utils.decorators import available_attrs

from gearfarm.utils.simple_responses import json_response_bad_request, api_request_params_required, \
    json_response_request_params_required, json_response_not_found


def csrf_ignore(view_func):
    """
    Skips the CSRF checks by setting the 'csrf_processing_done' to true.
    """

    def wrapped_view(*args, **kwargs):
        request = args[0]
        request.csrf_processing_done = True
        return view_func(*args, **kwargs)

    return wraps(view_func, assigned=available_attrs(view_func))(wrapped_view)


def request_params_required(param_names, raise_exception=False):
    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):
            request_params = request.GET
            if isinstance(param_names, six.string_types):
                params = (param_names,)
            else:
                params = param_names
            for param in params:
                if param not in request_params:
                    return json_response_request_params_required(param)
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def request_body_fields_required(param_names, raise_exception=False):
    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):
            request_params = json.loads(request.body.decode())
            if isinstance(param_names, six.string_types):
                params = (param_names,)
            else:
                params = param_names
            for param in params:
                if param not in request_params:
                    return json_response_bad_request(message='请求body中缺失参数{}'.format(param))
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def project_test_cases_params_verify(view_func):
    @wraps(view_func, assigned=available_attrs(view_func))
    def _wrapped_view(request, *args, **kwargs):
        params = request.query_params
        project = params.get('project')
        platform = params.get('platform')
        module = params.get('module')
        if not any([project, platform, module]):
            return json_response_bad_request('项目, 平台, 模块必传一个')
        if module:
            from testing.models import ProjectTestCaseModule
            get_object_or_404(ProjectTestCaseModule, pk=module)

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def test_cases_params_verify(view_func):
    @wraps(view_func, assigned=available_attrs(view_func))
    def _wrapped_view(request, *args, **kwargs):
        params = request.query_params
        if not any([params.get('library'), params.get('module')]):
            return json_response_bad_request('用例库, 模块必传一个')
        if params.get('module'):
            from testing.models import TestCaseModule
            get_object_or_404(TestCaseModule, pk=params.get('module'))

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def project_test_plan_cases_params_verify(view_func):
    @wraps(view_func, assigned=available_attrs(view_func))
    def _wrapped_view(request, *args, **kwargs):
        params = request.query_params
        plan = params.get('plan')
        module = params.get('module')
        if not any([plan, module]):
            return json_response_bad_request('计划, 模块必传一个')
        if module:
            from testing.models import TestPlanModule
            get_object_or_404(TestPlanModule, pk=module)

        return view_func(request, *args, **kwargs)

    return _wrapped_view


# 项目测试用例批量复制、移动的参数验证    同一个项目的用例  到  另一个项目的一个模块一个平台
def project_test_cases_batch_copy_params_verify(required_params=['cases', 'target_module', 'platforms'],
                                                raise_exception=False):
    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):
            params = request.data
            for param in required_params:
                if param not in params:
                    return json_response_request_params_required(param)
            from testing.api import ProjectTestCaseModule, ProjectPlatform, ProjectTestCase

            queryset = ProjectTestCase.active_cases()
            target_module = get_object_or_404(ProjectTestCaseModule, pk=request.data.get('target_module'))

            target_module_modules = target_module.platforms.all()
            platforms_ids = request.data.get('platforms', [])
            platforms = []
            if platforms_ids:
                platforms = ProjectPlatform.objects.filter(pk__in=platforms_ids)
                for platform in platforms:
                    if not target_module_modules.filter(pk=platform.id).exists():
                        return json_response_bad_request("所选平台不属于目标模块")
            if not platforms:
                return json_response_bad_request("请选择有效平台")

            if 'cases' in required_params:
                cases_ids = request.data.get('cases', [])
                cases = queryset.filter(pk__in=cases_ids).order_by('created_at')
                project_ids = set(cases.values_list('project_id', flat=True))
                if len(project_ids) > 1:
                    return json_response_bad_request("所移动的用例 不属于同一个项目")
                if not len(project_ids):
                    return json_response_bad_request("没有选中任何有效用例")

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator
