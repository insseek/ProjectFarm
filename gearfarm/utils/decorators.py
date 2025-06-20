# -*- coding:utf-8 -*-
import json
from functools import wraps

from django.utils import six
from django.utils.decorators import available_attrs

from gearfarm.utils.farm_response import json_response_bad_request, api_request_params_required, \
    json_response_request_params_required

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


def request_data_fields_required(param_names, raise_exception=False):
    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):
            request_params = request.data
            if isinstance(param_names, six.string_types):
                params = (param_names,)
            else:
                params = param_names
            for param in params:
                if param not in request_params:
                    return api_request_params_required(param)
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator
