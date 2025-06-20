from datetime import datetime, timedelta
from copy import deepcopy
import logging

from django.contrib.auth import login, logout
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view

from auth_top.models import TopToken, TopUser
from gearfarm.utils import simple_responses, simple_decorators
from gearfarm.utils.simple_responses import api_success, api_bad_request, api_suspended, api_request_params_required, \
    api_error, api_invalid_app_id, api_permissions_required
from gearfarm.utils.simple_decorators import request_params_required, request_data_fields_required
from farmbase.utils import gen_uuid, get_phone_verification_code
from notifications.tasks import send_feishu_message_to_individual
from geargitlab.gitlab_client import GitlabOauthClient
from oauth.aliyun_client import AliyunApi
from oauth.utils import get_feishu_client
from auth_top.serializers import TopUserViewSerializer
from auth_top.utils import request_data_app_id_user_type_check, APP_USER_TYPE_DICT, APP_LOGIN_TYPE_DICT, \
    request_params_app_id_request_top_user_type_check, build_params_app_id_user_type, request_params_app_id_check, \
    request_data_app_id_check
from auth_top.permissions_init import get_top_user_perms
from farmbase.permissions_utils import has_function_perm

logger = logging.getLogger()


@api_view(['GET'])
# @request_params_required(['app_id'])
@request_params_app_id_check()
def app_data(request):
    app_id = request.GET['app_id']
    data = {'user_types': APP_USER_TYPE_DICT[app_id], 'login_types': APP_LOGIN_TYPE_DICT[app_id]}
    return api_success(data)


@api_view(['GET'])
@build_params_app_id_user_type
@request_params_required(['phone', 'user_type'])
def phone_code(request):
    user_type = request.GET['user_type']
    phone = request.GET['phone']
    app_id = request.GET.get('app_id', None)
    if not phone:
        return api_bad_request(message="手机号必填")
    if user_type not in TopUser.USER_TYPES:
        return api_bad_request(message="user_type应该包含在{}中".format(TopUser.USER_TYPES))

    code_type = request.GET.get('code_type', 'login')

    top_user = TopUser.get_obj_by_phone(user_type, phone)
    if code_type == 'change_my_phone':
        if top_user and top_user.id != request.top_user.id:
            return api_bad_request("手机号已被其他人绑定")
    else:
        if not top_user:
            return api_bad_request(message="该手机号未绑定有效账户")

    if app_id == 'gear_tracker' and top_user.is_employee:
        if not has_function_perm(top_user.user, 'sign_up_for_gear_tracker'):
            return api_permissions_required("没有权限访问数据统计服务")

    code_cache_key = '{}-{}-{}-code'.format(user_type, code_type, phone)
    code_data = cache.get(code_cache_key, None)
    if code_data and code_data['time'] > timezone.now() - timedelta(minutes=1, seconds=30):
        return api_bad_request('不可频繁发送')

    code = get_phone_verification_code() if not settings.DEVELOPMENT else settings.DEVELOPMENT_DD_CODE
    cache.set(code_cache_key, {'code': code, 'time': timezone.now()}, 60 * 10)
    if settings.DEVELOPMENT:
        return api_success({'code': code})
    else:
        aliyun_client = AliyunApi(access_key_id=settings.ALIYUN_ACCESS_KEY_ID,
                                  access_key_secret=settings.ALIYUN_ACCESS_KEY_SECRET)
        aliyun_client.send_login_check_code_sms(phone, code, '【齿轮易创-SSO】')

    if settings.PRODUCTION and top_user.is_employee:
        feishu_user_id = top_user.authentication.profile.feishu_user_id
        if feishu_user_id:
            if feishu_user_id:
                send_feishu_message_to_individual(feishu_user_id, "你在登录【齿轮易创-SSO】, 验证码为:" + code)

    return api_success('发送成功')


@api_view(['GET'])
@request_params_required(['phone', 'app_id'])
@request_params_app_id_check()
def phone_login_code(request):
    phone = request.GET['phone']
    if not phone:
        return api_bad_request(message="手机号必填")
    app_id = request.GET.get('app_id', None)
    user_type = request.GET.get('user_type', None)
    if user_type and user_type not in TopUser.USER_TYPES:
        return api_bad_request(message="user_type应该包含在{}中".format(TopUser.USER_TYPES))
    if user_type:
        app_user_types = [user_type]
    else:
        app_user_types = APP_USER_TYPE_DICT[app_id]

    users_dict = {}
    for user_type in app_user_types:
        top_user = TopUser.get_obj_by_phone(user_type, phone)
        if top_user:
            users_dict[user_type] = deepcopy(top_user)
    if not users_dict:
        return api_bad_request(message="该手机号未绑定有效账户")

    phone_login_code_key = '{}-phone-login-{}-code'.format(app_id, phone)
    code_data = cache.get(phone_login_code_key, None)
    if code_data and code_data['time'] > timezone.now() - timedelta(minutes=1, seconds=30):
        return api_bad_request('不可频繁发送')

    code = get_phone_verification_code() if not settings.DEVELOPMENT else settings.DEVELOPMENT_DD_CODE
    cache.set(phone_login_code_key, {'code': code, 'time': timezone.now()}, 60 * 10)
    if settings.DEVELOPMENT:
        return api_success({'code': code})
    else:
        aliyun_client = AliyunApi(access_key_id=settings.ALIYUN_ACCESS_KEY_ID,
                                  access_key_secret=settings.ALIYUN_ACCESS_KEY_SECRET)
        aliyun_client.send_login_check_code_sms(phone, code, '【齿轮易创-SSO】')
        if 'employee' in users_dict:
            employee = users_dict['employee']
            if settings.PRODUCTION and employee:
                feishu_user_id = employee.authentication.profile.feishu_user_id
                if feishu_user_id:
                    if feishu_user_id:
                        send_feishu_message_to_individual(feishu_user_id, "你在登录【齿轮易创-SSO】, 验证码为:" + code)
    return api_success('发送成功')


@api_view(['POST'])
@request_data_fields_required(['phone', 'code', 'app_id'])
@request_data_app_id_check()
def phone_login_user_types(request):
    app_id = request.data['app_id']
    phone = request.data.get('phone')
    code = request.data.get('code')

    app_user_types = APP_USER_TYPE_DICT[app_id]
    users_dict = {}
    for user_type in app_user_types:
        top_user = TopUser.get_obj_by_phone(user_type, phone)
        if top_user:
            users_dict[user_type] = deepcopy(top_user)
    if not users_dict:
        return api_bad_request(message="该手机号未绑定有效账户")

    phone_login_code_key = '{}-phone-login-{}-code'.format(app_id, phone)
    # 几个万能验证码
    if not settings.PRODUCTION and code == settings.DEVELOPMENT_DD_CODE:
        pass
    else:
        code_data = cache.get(phone_login_code_key, None)
        if not code_data:
            return api_bad_request(message='验证码无效，请重新获取验证码')
        cache_code = code_data['code']
        if not str(cache_code) == str(code):
            return api_bad_request(message='验证码错误')

    # 手机验证码有效期10分钟 code可多次使用 所有不用存用户； gitlab、飞书 code只能使用一次 需要缓存中存下来查到的用户
    # phone_users_key = '{}-phone-login-{}-users'.format(app_id, phone)
    # cache.set(phone_users_key, users_dict, 60 * 10)
    #
    return api_success({'user_types': list(users_dict.keys())})


@api_view(['POST'])
@build_params_app_id_user_type
@request_data_fields_required(['phone', 'code', 'user_type', 'app_id'])
@request_data_app_id_check()
@request_data_app_id_user_type_check()
def phone_login(request):
    app_id = request.data['app_id']
    user_type = request.data['user_type']
    if user_type not in APP_USER_TYPE_DICT[app_id]:
        return api_bad_request(message="user_type应该包含在{}中".format(APP_USER_TYPE_DICT[app_id]))

    phone = request.data.get('phone')
    code = request.data.get('code')

    top_user = TopUser.get_obj_by_phone(user_type, phone)
    if not top_user:
        return api_bad_request(message="该手机号未绑定有效账户")

    code_cache_key = '{}-phone-login-{}-code'.format(app_id, phone)
    # 几个万能验证码
    if not settings.PRODUCTION and code == settings.DEVELOPMENT_DD_CODE:
        pass
    elif settings.PRODUCTION and code == '10311303':
        pass
    else:
        code_data = cache.get(code_cache_key, None)
        if not code_data:
            return api_bad_request(message='验证码无效，请重新获取验证码')
        cache_code = code_data['code']
        if not str(cache_code) == str(code):
            return api_bad_request(message='验证码错误')

    if app_id == 'gear_tracker' and top_user.is_employee:
        if not has_function_perm(top_user.user, 'sign_up_for_gear_tracker'):
            return api_permissions_required("没有权限访问数据统计服务")

    if top_user.is_employee:
        login(request, top_user.user)
    token, created = TopToken.get_or_create(top_user=top_user)
    return api_success({'token': token.key, 'user_type': top_user.user_type, 'user_info': top_user.user_info()})


@api_view(['GET'])
@request_params_required('redirect_uri')
def gitlab_login_oauth_uri(request):
    redirect_uri = request.GET.get('redirect_uri')
    if not redirect_uri:
        return api_request_params_required("redirect_uri")
    client = GitlabOauthClient()
    oauth_url = client.get_oauth_url(redirect_uri)
    return api_success({'oauth_url': oauth_url})


# 获取gitlab所有能登录的用户类型
@api_view(['POST'])
@request_data_fields_required(['code', 'redirect_uri', 'app_id'])
@request_data_app_id_check()
def gitlab_login_user_types(request):
    app_id = request.data['app_id']
    redirect_uri = request.data.get('redirect_uri')
    code = request.data.get('code')

    client = GitlabOauthClient()
    access_token = client.get_access_token(code, redirect_uri)
    if access_token:
        user_data = client.get_user_data(access_token)
        if user_data:
            gitlab_user_id = user_data['id']

            app_user_types = APP_USER_TYPE_DICT[app_id]
            users_dict = {}
            for user_type in app_user_types:
                top_user = TopUser.get_obj_by_gitlab_user_id(user_type, gitlab_user_id)
                if top_user:
                    users_dict[user_type] = deepcopy(top_user)
            if not users_dict:
                return api_bad_request(message="Gitlab账户暂未绑定有效账户该未绑定有效账户")

            # gitlab、飞书 code只能使用一次 需要缓存中存下来查到的用户
            gitlab_code_users_key = '{}-gitlab-login-{}-users'.format(app_id, code)
            cache.set(gitlab_code_users_key, users_dict, 60 * 15)
            return api_success({'user_types': list(users_dict.keys())})
    return api_error(message='获取Gitlab用户信息失败')


@api_view(['POST'])
@request_data_fields_required(['code', 'redirect_uri', 'user_type', 'app_id'])
@request_data_app_id_user_type_check()
def gitlab_login(request):
    app_id = request.data['app_id']
    user_type = request.data['user_type']
    redirect_uri = request.data.get('redirect_uri')
    code = request.data.get('code')

    gitlab_code_users_key = '{}-gitlab-login-{}-users'.format(app_id, code)
    users_dict = cache.get(gitlab_code_users_key, None)
    top_user = None
    if users_dict:
        top_user = users_dict.get(user_type, None)
    else:
        try:
            client = GitlabOauthClient()
            access_token = client.get_access_token(code, redirect_uri)
            if access_token:
                user_data = client.get_user_data(access_token)
                if user_data:
                    gitlab_user_id = user_data['id']
                    top_user = TopUser.get_obj_by_gitlab_user_id(user_type, gitlab_user_id)
            if not top_user:
                return api_error(message='从Gitlab获取用户信息失败')
        except Exception as e:
            logger.error(e)
            return api_error(message='从Gitlab获取用户信息失败')
    if not top_user:
        return api_bad_request(message="Gitlab账户暂未绑定有效账户, 或code已过期")

    if app_id == 'gear_tracker' and top_user.is_employee:
        if not has_function_perm(top_user.user, 'sign_up_for_gear_tracker'):
            return api_permissions_required("没有权限访问数据统计服务")
    if top_user.is_employee:
        login(request, top_user.user)
    token, created = TopToken.get_or_create(top_user=top_user)
    return api_success({'token': token.key, 'user_type': token.user_type})


@api_view(['GET'])
@request_params_required('redirect_uri')
def feishu_login_oauth_uri(request):
    redirect_uri = request.GET.get('redirect_uri')
    if not redirect_uri:
        return api_request_params_required("redirect_uri")
    client = get_feishu_client()
    oauth_url = client.get_oauth_url(redirect_uri)
    return api_success({'oauth_url': oauth_url})


# 获取飞书所有能登录的用户类型
@api_view(['POST'])
@request_data_fields_required(['code', 'app_id'])
@request_data_app_id_check()
def feishu_login_user_types(request):
    app_id = request.data['app_id']
    code = request.data.get('code')

    client = get_feishu_client()
    access_token = client.get_user_access_token(code)
    if access_token:
        user_data = client.get_user_detail_by_token(access_token)
        if user_data:
            feishu_user_id = user_data['user_id']

            app_user_types = APP_USER_TYPE_DICT[app_id]
            users_dict = {}
            for user_type in app_user_types:
                top_user = TopUser.get_obj_by_feishu_user_id(user_type, feishu_user_id)
                if top_user:
                    users_dict[user_type] = deepcopy(top_user)
                    mobile = user_data.get('mobile', '')
                    if mobile:
                        build_top_user_phone(top_user, mobile)

            if not users_dict:
                return api_bad_request(message="飞书账户暂未绑定有效账户该未绑定有效账户")

            # Gitlab、飞书 code只能使用一次 需要缓存中存下来查到的用户
            feishu_code_users_key = '{}-feishu-login-{}-users'.format(app_id, code)
            cache.set(feishu_code_users_key, users_dict, 60 * 15)
            return api_success({'user_types': list(users_dict.keys())})
    return api_error(message='获取飞书用户信息失败')


def build_top_user_phone(top_user, phone):
    if phone.startswith('+86'):
        phone = phone.replace('+86', '')
    if top_user.is_employee:
        user = top_user.user
        if not user.profile.phone_number:
            user.profile.phone_number = phone
            user.profile.save()

    elif top_user.is_developer:
        developer = top_user.developer
        if not developer.phone:
            developer.phone = phone
            developer.save()


@api_view(['POST'])
@request_data_fields_required(['code', 'user_type', 'app_id'])
@request_data_app_id_user_type_check()
def feishu_login(request):
    app_id = request.data['app_id']
    user_type = request.data['user_type']
    code = request.data.get('code')

    feishu_code_users_key = '{}-feishu-login-{}-users'.format(app_id, code)
    users_dict = cache.get(feishu_code_users_key, None)
    top_user = None
    if users_dict:
        top_user = users_dict.get(user_type, None)
    else:
        client = get_feishu_client()
        access_token = client.get_user_access_token(code)
        if access_token:
            user_data = client.get_user_detail_by_token(access_token)
            if user_data:
                feishu_user_id = user_data['user_id']
                top_user = TopUser.get_obj_by_feishu_user_id(user_type, feishu_user_id)
                mobile = user_data.get('mobile', '')
                if mobile:
                    build_top_user_phone(top_user, mobile)

        if not top_user:
            return api_error(message='从飞书获取用户信息失败')
    if not top_user:
        return api_bad_request(message="飞书账户未查找到有效账户，或code已过期")
    if app_id == 'gear_tracker' and top_user.is_employee:
        if not has_function_perm(top_user.user, 'sign_up_for_gear_tracker'):
            return api_permissions_required("没有权限访问数据统计服务")
    if top_user.is_employee:
        login(request, top_user.user)
    token, created = TopToken.get_or_create(top_user=top_user)
    return api_success({'token': token.key, 'user_type': token.user_type})


@api_view(['GET'])
@request_params_required(['app_id', ])
@request_params_app_id_request_top_user_type_check()
def sso_ticket(request):
    top_user = request.top_user
    ticket = 'sT{}{}'.format(top_user.id, gen_uuid(8))
    key_data = {'ticket': ticket,
                'created_at': timezone.now().strftime(settings.DATETIME_FORMAT), 'expired_seconds': 60 * 10,
                'top_user': {'id': top_user.id}}
    cache.set(ticket, key_data, 60 * 10)
    return api_success(key_data)


@api_view(['POST'])
@request_data_fields_required('ticket')
def sso_ticket_login(request):
    key = request.data.get('ticket')
    authentication_data = cache.get(key, None)
    if not authentication_data:
        return simple_responses.api_invalid_authentication_key()
    top_user_id = authentication_data['top_user']['id']
    top_user = get_object_or_404(TopUser, pk=top_user_id)
    if not top_user.is_active:
        return api_suspended()
    token, created = TopToken.get_or_create(top_user=top_user)
    if top_user.is_employee:
        login(request, top_user.user)
    return api_success(data={'token': token.key, 'user_type': token.user_type, 'user_info': top_user.user_info()})


@api_view(['GET'])
@build_params_app_id_user_type
@request_params_required(['user_type', 'code_type'])
def phone_change_code(request):
    top_user = request.top_user
    user_type = request.GET['user_type']

    if user_type not in TopUser.USER_TYPES:
        return api_bad_request(message="user_type应该包含在{}中".format(TopUser.USER_TYPES))

    code_type = request.GET.get('code_type', '')
    if code_type not in ['origin_phone_code', 'new_phone_code']:
        return api_bad_request(message="code_type应该包含在{}中".format(['origin_phone_code', 'new_phone_code']))

    if code_type == 'origin_phone_code':
        phone = top_user.phone
    elif code_type == 'new_phone_code':
        phone = request.GET.get('phone', None)
        if not phone:
            return api_bad_request(message="手机号必填")
        exists_top_user = TopUser.get_obj_by_phone(user_type, phone)
        if exists_top_user and exists_top_user.id != request.top_user.id:
            return api_bad_request("手机号已被其他人绑定")
    else:
        return api_bad_request(message="code_type应该包含在{}中".format(['origin_phone_code', 'new_phone_code']))

    code_cache_key = '{}-{}-{}-code'.format(user_type, code_type, phone)
    code_data = cache.get(code_cache_key, None)
    if code_data and code_data['time'] > timezone.now() - timedelta(minutes=1, seconds=30):
        return api_bad_request('不可频繁发送')

    code = get_phone_verification_code() if not settings.DEVELOPMENT else settings.DEVELOPMENT_DD_CODE
    cache.set(code_cache_key, {'code': code, 'time': timezone.now()}, 60 * 10)
    if settings.DEVELOPMENT:
        return api_success({'code': code})
    else:
        aliyun_client = AliyunApi(access_key_id=settings.ALIYUN_ACCESS_KEY_ID,
                                  access_key_secret=settings.ALIYUN_ACCESS_KEY_SECRET)
        aliyun_client.send_login_check_code_sms(phone, code, '【齿轮易创-SSO】')

    if settings.PRODUCTION and top_user.is_employee:
        feishu_user_id = top_user.authentication.profile.feishu_user_id
        if feishu_user_id:
            if feishu_user_id:
                send_feishu_message_to_individual(feishu_user_id, "你在登录【齿轮易创-SSO】, 验证码为:" + code)

    return api_success('发送成功')


@api_view(['POST'])
@build_params_app_id_user_type
@request_data_fields_required(['phone', 'origin_code', 'new_code'])
def change_my_phone(request):
    client = request.client
    top_user = request.top_user

    origin_phone = top_user.phone
    user_type = request.data.get('user_type')
    phone = request.data.get('phone')

    origin_code = request.data.get('origin_code')
    new_code = request.data.get('new_code')

    if not all([phone, origin_code, new_code]):
        return api_bad_request("手机号、验证码不能为空")

    exists_top_user = TopUser.get_obj_by_phone(user_type, phone)
    if exists_top_user and exists_top_user.id != request.top_user.id:
        return api_bad_request("手机号已被其他人绑定")

    origin_code_key = '{}-{}-{}-code'.format(user_type, 'origin_phone_code', origin_phone)
    code_key = '{}-{}-{}-code'.format(user_type, 'new_phone_code', phone)

    origin_code_data = cache.get(origin_code_key, None)
    if not origin_code_data:
        return api_bad_request(message='原手机验证码无效，请重新获取验证码')

    code_data = cache.get(code_key, None)
    if not code_data:
        return api_bad_request(message='新手机号验证码无效，请重新获取验证码')

    origin_cache_code = origin_code_data['code']
    if not origin_cache_code == origin_code:
        return api_bad_request(message='原手机验证码错误')

    cache_code = code_data['code']
    if not cache_code == new_code:
        return api_bad_request(message='新手机验证码错误')

    top_user.set_phone(phone)
    data = TopUserViewSerializer(top_user).data
    return api_success(data)


@api_view(['POST'])
def sso_logout(request):
    top_user = request.top_user
    TopToken.get_or_create(top_user=top_user, refresh=True)
    if top_user.is_employee:
        logout(request)
    return api_success({"detail": '退出成功'})


@api_view(['GET'])
def my_info(request):
    top_user = request.top_user
    data = TopUserViewSerializer(top_user).data
    return api_success(data)


@api_view(["GET"])
@request_params_required('app_id')
@request_params_app_id_check()
def my_perms(request):
    app_id = request.GET['app_id']
    top_user = request.top_user
    data = TopUserViewSerializer(top_user).data
    perms = get_top_user_perms(top_user, app_id)
    data['perms'] = perms
    return api_success(data)
