import re
import logging
from itertools import chain
from datetime import datetime, timedelta
import urllib.parse

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.cache import cache
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from rest_framework import HTTP_HEADER_ENCODING, exceptions

from gearfarm.utils import farm_response
from auth_top.models import TopUser, TopToken
from auth_top.authentication import TokenAuthentication
from gearfarm.utils.farm_response import json_response_suspended, json_response_permissions_required, \
    json_response_login_required, \
    json_response_unauthorized, json_response_authentication_expired, json_response_bad_request
from developers.models import Developer


class RequireLoginMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        self.get_response = get_response

        self.login_required_api_prefix = settings.LOGIN_REQUIRED_API_PREFIX

        self.exceptions = tuple(re.compile(url) for url in settings.LOGIN_REQUIRED_URLS_EXCEPTIONS)
        self.api_exceptions = tuple(re.compile(url) for url in settings.LOGIN_REQUIRED_API_EXCEPTIONS)
        self.open_api_exceptions = tuple(re.compile(url) for url in settings.LOGIN_REQUIRED_OPEN_API_EXCEPTIONS)
        self.one_time_auth_open_api_post_exceptions = tuple(
            re.compile(url) for url in settings.ONE_TIME_AUTH_OPEN_API_POST_EXCEPTIONS)

    def process_view(self, request, view_func, view_args, view_kwargs):
        request.developer = None
        request.client = None
        request.top_user = None

        is_login_required = True

        # 不需要验证登录的url     路由、 Farm接口、 工程师端的接口
        # An exception match should immediately return None
        for url in chain(self.exceptions, self.api_exceptions, self.open_api_exceptions):
            if url.match(request.path):
                is_login_required = False
                break

        # session用户已登录 Farm用户 判断用户冻结状态 或模拟状态
        if request.user.is_authenticated:
            if not request.user.is_active:
                return json_response_suspended()
            token, created = TopToken.get_or_create(user=request.user)
            request.top_user = token.top_user
            # 是否为模拟用户
            if request.user.is_superuser:
                key = "{superuser}-impersonator".format(superuser=request.user.username)
                impersonator_username = cache.get(key, None)
                if impersonator_username and request.path not in ['/api/users/impersonate',
                                                                  '/api/users/impersonate/exit']:
                    if request.method not in ['GET', 'get']:
                        return json_response_bad_request('模拟模式下 只允许查看 不允许修改')
                    request.user = User.objects.get(username=impersonator_username)
                    token, created = TopToken.get_or_create(user=request.user)
                    request.top_user = token.top_user
                    request.is_impersonator = True
                    request.impersonator = impersonator_username
            return None

        # 如果session中没有得到登录用户， 尝试通过Token认证 获取当前登录的user、developer
        token_key = None
        token_authentication = TokenAuthentication()
        try:
            token_key = token_authentication.authenticate_key(request)
        except:
            pass

        request.is_impersonator = False
        # 临时登录 ONE_TIME_AUTH 找到真实的Token
        if token_key and token_key.startswith(settings.ONE_TIME_AUTH_PREFIX):
            # real_token_data = {"token": real_token.key, 'user_type': real_token.user_type, 'editable': False}
            real_token_data = cache.get(token_key)
            if real_token_data:
                if not real_token_data.get('editable'):
                    if request.method not in ['GET', 'get']:
                        api_post_allowed = False
                        if request.path.endswith('logout'):
                            api_post_allowed = True
                        else:
                            for url in self.one_time_auth_open_api_post_exceptions:
                                if url.match(request.path):
                                    api_post_allowed = True
                                    break
                        if not api_post_allowed:
                            return json_response_permissions_required('模拟模式下 只允许查看 不允许修改')
                token_key = real_token_data['token']
                request.is_impersonator = True

        if token_key:
            try:
                result = token_authentication.authenticate_credentials(token_key)
                if result:
                    auth, token = result
                    request.top_user = auth
                    user_type = auth.user_type
                    if user_type == 'employee':
                        request.user = auth.user
                    elif user_type == 'freelancer':
                        request.developer = auth.developer
                    elif user_type == 'client':
                        request.client = auth.client
            except exceptions.AuthenticationFailed as e:
                if e.detail and e.detail.lower() == 'invalid token.':
                    if is_login_required:
                        return farm_response.json_response_invalid_authentication_key()
                elif e.detail and e.detail.lower() == 'user inactive or deleted.':
                    if is_login_required:
                        return farm_response.json_response_suspended()
                if is_login_required:
                    raise
                else:
                    pass
            except Exception as e:
                if is_login_required:
                    raise
                else:
                    pass

        # 不需要验证登录的url     路由、 Farm接口、 工程师端的接口
        if not is_login_required:
            return None

        # 原型评论服务指出多种类型用户登录
        http_origin = request.META.get('HTTP_ORIGIN', None)
        if http_origin:
            if http_origin in ['https://chilunyc.com',
                               settings.GEAR_PROTOTYPE_SITE_URL] or 'prototype.chilunyc.com' in http_origin:
                if request.top_user:
                    return None

        # 工程师端的接口 工程师登录才能使用
        if request.path.startswith('/open_api/v1/developer'):
            if not request.developer:
                return json_response_unauthorized("工程师登录验证失败，请检查Token")
            if not request.is_impersonator:
                request.developer.last_login = timezone.now()
                request.developer.save()
            return None
        # 客户web端的接口 客户登录才能使用
        elif request.path.startswith('/open_api/v1/client'):
            if not request.client:
                return json_response_unauthorized("客户登录验证失败，请检查Token")
            return None
        # Test端的接口 内部员工、工程师登录
        elif request.path.startswith('/api/v1/testing/'):
            if not (request.developer or request.user.is_authenticated):
                return json_response_unauthorized("TesT端登录验证失败，请检查Token, 只支持内部员工、工程师登录")
            return None
        # 文档的接口 内部员工、工程师登录
        elif request.path.startswith('/api/v1/document'):
            if not (request.developer or request.user.is_authenticated):
                return json_response_unauthorized("文档系统登录验证失败，请检查Token, 只支持内部员工、工程师登录")
            return None
        # SSO端的接口 内部员工、工程师登录
        elif request.path.startswith('/api/v1/auth_top'):
            if not request.top_user:
                return json_response_unauthorized("SSO端登录验证失败，请检查Token")
            return None

        if request.user and request.user.is_authenticated:
            if not request.top_user.is_active:
                return json_response_suspended()
            return None

        # 未登录用户 接口返回失败接口、页面返回未登录页面
        if request.path.startswith(self.login_required_api_prefix):
            return json_response_login_required()
        return login_required(view_func)(request, *view_args, **view_kwargs)

    def process_response(self, request, response):
        if getattr(request, 'impersonator', False):
            impersonator_username = request.impersonator
            response.__setitem__('X-Impersonator', urllib.parse.quote(impersonator_username))

            expose_headers = 'X-Impersonator'
            if response.has_header('Access-Control-Expose-Headers'):
                origin_expose_headers = response.__getitem__('Access-Control-Expose-Headers')
                if origin_expose_headers:
                    expose_headers = origin_expose_headers + ',' + expose_headers
            response.__setitem__('Access-Control-Expose-Headers', expose_headers)
        return response
