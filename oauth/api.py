import json

from django.contrib.auth.models import User
from django.contrib.auth import login
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response

from auth_top.models import TopToken
from gearfarm.utils.farm_response import api_success, api_suspended, api_not_found, api_error, api_bad_request
from gearfarm.utils.decorators import request_params_required, request_data_fields_required

from gearfarm.utils import farm_response
from farmbase.models import Profile
from geargitlab.gitlab_client import GitlabOauthClient
from oauth.utils import get_feishu_client
from oauth import we_chat
from developers.models import Developer


@api_view(['POST'])
def gitlab_bind_redirect_data(request):
    redirect_uri = request.data.get('redirect_uri')
    if not redirect_uri:
        return Response({"result": False, "message": "redirect_uri参数为必填"})
    redirect_uri = redirect_uri
    client = GitlabOauthClient()
    oauth_url = client.get_oauth_url(redirect_uri)
    return Response({"result": True, "data": {'oauth_url': oauth_url}})


@api_view(['POST'])
def gitlab_bind(request):
    redirect_uri = request.data.get('redirect_uri')
    code = request.data.get('code')
    if not (redirect_uri and code):
        return Response({"result": False, "message": "code与redirect_uri参数为必传"})
    redirect_uri = redirect_uri
    client = GitlabOauthClient()
    access_token = client.get_access_token(code, redirect_uri)
    if access_token:
        user_data = client.get_user_data(access_token)
        if user_data:
            gitlab_user_id = user_data['id']
            # 登录用户
            if request.user.is_authenticated:
                # 已绑定gitlab
                if request.user.profile.gitlab_user_id:
                    return Response({"result": True, "data": None})
                # 未绑定gitlab 该git账户没有被绑定
                elif not Profile.objects.filter(gitlab_user_id=gitlab_user_id).exists():
                    request.user.profile.gitlab_user_id = gitlab_user_id
                    request.user.profile.save()
                    return Response({"result": True, "data": None})
            return Response({"result": False, "message": "绑定失败，当前用户未登录"})
    return Response({"result": False, "message": "绑定失败，获取Gitlab用户信息失败"})


@api_view(['POST'])
def gitlab_login_redirect_data(request):
    redirect_uri = request.data.get('redirect_uri')
    if not redirect_uri:
        return Response({"result": False, "message": "redirect_uri参数为必填"})

    redirect_uri = redirect_uri
    client = GitlabOauthClient()
    oauth_url = client.get_oauth_url(redirect_uri)
    return Response({"result": True, "data": {'oauth_url': oauth_url}})


@api_view(['POST'])
def gitlab_login(request):
    redirect_uri = request.data.get('redirect_uri')
    code = request.data.get('code')
    if not (redirect_uri and code):
        return Response({"result": False, "message": "code与redirect_uri参数为必传"})
    redirect_uri = redirect_uri

    client = GitlabOauthClient()
    access_token = client.get_access_token(code, redirect_uri)
    if access_token:
        user_data = client.get_user_data(access_token)
        if user_data:
            gitlab_user_id = user_data['id']
            user = User.objects.filter(profile__gitlab_user_id=gitlab_user_id).first()
            if user:
                if not user.is_active:
                    return api_suspended()
                login(request, user)
                token, created = TopToken.get_or_create(user=user)
                return api_success(data={'token': token.key, 'user_type': token.user_type})
            return api_not_found(message='登录失败, Gitlab账户暂未绑定Farm账户')
    return api_error(message='获取gitlab用户信息失败')


@api_view(['POST'])
def gitlab_oauth_unbind(request):
    top_user = request.top_user
    if top_user.is_employee:
        request.user.profile.gitlab_user_id = None
        request.user.profile.save()
    elif top_user.is_developer:
        request.developer.gitlab_user_id = None
        request.developer.save()
    return api_success()


@api_view(['POST'])
def feishu_bind_redirect_data(request):
    redirect_uri = request.data.get('redirect_uri')
    if not redirect_uri:
        return api_bad_request(message="redirect_uri参数为必填")
    redirect_uri = redirect_uri
    client = get_feishu_client()
    oauth_url = client.get_oauth_url(redirect_uri)
    return api_success({'oauth_url': oauth_url})


@api_view(['POST'])
def feishu_bind(request):
    code = request.data.get('code')
    if not code:
        return Response({"result": False, "message": "code参数为必传"})
    client = get_feishu_client()
    access_token = client.get_user_access_token(code)
    if access_token:
        user_data = client.get_user_detail_by_token(access_token)
        if user_data:
            feishu_user_id = user_data['user_id']
            top_user = request.top_user
            if top_user.is_employee:
                # 登录用户
                user = top_user.user
                if user.is_authenticated:
                    if Profile.objects.exclude(user_id=user.id).filter(feishu_user_id=feishu_user_id).exists():
                        return farm_response.api_bad_request("该飞书已经被绑定")
                    profile = user.profile
                    profile.feishu_user_id = feishu_user_id
                    profile.save()
                    # # 李帆平是开发人员
                    # if user.username == '李帆平':
                    #     user.profile.send_feishu_message(json.dumps(user_data, ensure_ascii=False))
                    if not profile.phone_number:
                        mobile = user_data.get('mobile', '')
                        if mobile:
                            if mobile.startswith('+86'):
                                mobile = mobile.replace('+86', '')
                            profile.phone_number = mobile
                            profile.save()
                    return api_success(user_data)
            elif top_user.is_developer:
                if Developer.objects.exclude(pk=top_user.developer.id).filter(feishu_user_id=feishu_user_id).exists():
                    return farm_response.api_bad_request("该飞书已经被绑定")
                profile = top_user.developer
                profile.feishu_user_id = feishu_user_id
                profile.save()
                if not profile.phone:
                    mobile = user_data.get('mobile', '')
                    if mobile:
                        if mobile.startswith('+86'):
                            mobile = mobile.replace('+86', '')
                        profile.phone = mobile
                        profile.save()
                return api_success(user_data)
            else:
                return api_bad_request(message='只有内部员工、工程师支持绑定飞书')

            return Response({"result": False, "message": "绑定失败，当前用户未登录"})
    return Response({"result": False, "message": "绑定失败，获取飞书用户信息失败"})


@api_view(['POST'])
def feishu_unbind(request):
    top_user = request.top_user
    if top_user.is_employee:
        request.user.profile.feishu_user_id = None
        request.user.profile.save()
    elif top_user.is_developer:
        request.developer.feishu_user_id = None
        request.developer.save()
    return api_success()


@api_view(['POST'])
def feishu_login_redirect_data(request):
    redirect_uri = request.data.get('redirect_uri')
    if not redirect_uri:
        return Response({"result": False, "message": "redirect_uri参数为必填"})
    redirect_uri = redirect_uri
    client = get_feishu_client()
    oauth_url = client.get_oauth_url(redirect_uri)
    return Response({"result": True, "data": {'oauth_url': oauth_url}})


@api_view(['POST'])
def feishu_login(request):
    code = request.data.get('code')
    if not code:
        return Response({"result": False, "message": "code参数为必传"})

    client = get_feishu_client()
    access_token = client.get_user_access_token(code)
    if access_token:
        user_data = client.get_user_detail_by_token(access_token)
        if user_data:
            feishu_user_id = user_data['user_id']
            user = User.objects.filter(profile__feishu_user_id=feishu_user_id).first()
            if user:
                if not user.is_active:
                    return api_suspended()
                if not user.profile.phone_number:
                    mobile = user_data.get('mobile', '')
                    if mobile:
                        if mobile.startswith('+86'):
                            mobile = mobile.replace('+86', '')
                        user.profile.phone_number = mobile
                        user.profile.save()
                login(request, user)

                token, created = TopToken.get_or_create(user=user)
                return api_success(data={'token': token.key, 'user_type': token.user_type})
            return Response({"result": False, 'message': '登录失败, 飞书账户暂未绑定Farm账户', 'data': user_data})
    return Response({"result": False, 'message': '获取飞书用户信息失败'})


@api_view(['GET'])
def feishu_users(request):
    from django.core.cache import cache
    cache.delete('feishu_tenant_access_token')
    return Response({"result": True, 'data': []})


@api_view(['POST'])
@request_data_fields_required("url")
def wechat_sign_data(request):
    url = request.data.get("url")
    data = we_chat.get_default_sign_data(url)
    return api_success(data)
