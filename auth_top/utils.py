from functools import wraps
from copy import deepcopy

from django.utils.decorators import available_attrs

from gearfarm.utils.simple_responses import api_invalid_app_id, api_bad_request, api_unauthorized
from auth_top.serializers import TopUserViewSerializer
from auth_top.models import TopUser

APP_USER_TYPE_DICT = {
    "gear_farm": ['employee'],
    "gear_developer": ['freelancer'],
    "gear_test": ['employee', 'freelancer'],
    "gear_client": ['client'],
    "gear_document": ['employee', 'freelancer'],
    "gear_tracker": ['employee'],
    "gear_prototype": ['employee', 'freelancer', 'client'],
}

APP_LOGIN_TYPE_DICT = {
    "gear_farm": ['phone', 'gitlab', 'feishu'],
    "gear_developer": ['phone', 'gitlab', 'feishu'],
    "gear_test": ['phone', 'gitlab', 'feishu'],
    "gear_client": ['phone'],
    "gear_document": ['phone', 'gitlab', 'feishu'],
    "gear_tracker": ['phone', 'gitlab', 'feishu'],
    "gear_prototype": ['phone', 'gitlab', 'feishu'],
}


def get_top_user_data(user=None, developer=None, top_user=None):
    if not top_user:
        if user:
            top_user, create = TopUser.objects.get_or_create(user=user)
        if developer:
            top_user, create = TopUser.objects.get_or_create(developer=developer)
    if top_user:
        return TopUserViewSerializer(top_user).data


def request_data_app_id_user_type_check():
    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):
            app_id = request.data['app_id']
            if app_id not in APP_USER_TYPE_DICT.keys():
                return api_invalid_app_id()
            user_type = request.data['user_type']
            app_user_types = deepcopy(APP_USER_TYPE_DICT[app_id])
            if user_type not in app_user_types:
                return api_bad_request("当前用户类型不支持")
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def request_data_app_id_check():
    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):
            app_id = request.data.get('app_id', None)
            if app_id not in APP_USER_TYPE_DICT.keys():
                return api_invalid_app_id()
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def build_params_app_id_user_type(view_func):
    """
    """

    @wraps(view_func, assigned=available_attrs(view_func))
    def _wrapped_view(request, *args, **kwargs):
        if request.path.startswith('/open_api/v1/client'):
            if request.method == 'POST':
                data = request.data
                data['app_id'] = 'gear_client'
                data['user_type'] = 'client'
            elif request.method == 'GET':
                data = request.GET
                # 记住旧的方式
                _mutable = data._mutable
                # 设置_mutable为True
                data._mutable = True
                # 改变你想改变的数据
                data['app_id'] = 'gear_client'
                data['user_type'] = 'client'
                # 恢复_mutable原来的属性
                data._mutable = _mutable
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def request_params_app_id_user_type_check():
    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):
            params = request.GET
            app_id = params['app_id']
            user_type = params['user_type']

            if app_id not in APP_USER_TYPE_DICT.keys():
                return api_invalid_app_id()

            app_user_types = deepcopy(APP_USER_TYPE_DICT[app_id])
            if user_type not in app_user_types:
                return api_bad_request("当前用户类型不支持")

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def request_params_app_id_check():
    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):
            params = request.GET
            app_id = params.get('app_id', None)

            if app_id not in APP_USER_TYPE_DICT.keys():
                return api_invalid_app_id()

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def request_params_app_id_request_top_user_type_check():
    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):
            params = request.GET
            app_id = params['app_id']
            user_type = request.top_user.user_type

            if app_id not in APP_USER_TYPE_DICT.keys():
                return api_invalid_app_id()

            app_user_types = deepcopy(APP_USER_TYPE_DICT[app_id])
            if user_type not in app_user_types:
                return api_unauthorized("当前用户类型不支持")

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator
