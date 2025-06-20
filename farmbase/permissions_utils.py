from functools import wraps

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render, redirect
from django.shortcuts import render
from django.utils import six
from django.core.cache import cache
from django.utils.decorators import available_attrs
from django.http.response import HttpResponseForbidden
from django.conf import settings

from farmbase.models import FunctionPermission


def has_function_perms(user, perms):
    if isinstance(perms, six.string_types):
        perms = (perms,)
    for perm in perms:
        if not has_function_perm(user, perm):
            return False
    return True


def has_any_function_perms(user, perms):
    if isinstance(perms, six.string_types):
        perms = (perms,)
    for perm in perms:
        if has_function_perm(user, perm):
            return True
    return False


def has_function_perm(user, perm, without_superuser=True):
    if not user.is_active:
        return False
    if without_superuser and user.is_superuser:
        return True
    func_perm = FunctionPermission.objects.filter(codename=perm)
    if not func_perm.exists():
        return False
    if user.is_authenticated:
        user_func_perm_list = get_user_function_perm_codename_list(user)
        if user_func_perm_list and perm in user_func_perm_list:
            return True
    return False


def get_user_function_perm_codename_list(user, superuser_with_all=False):
    if user.is_active:
        if user.is_superuser and superuser_with_all:
            user_func_perms = FunctionPermission.objects.all()
        else:
            user_func_perms = user.func_perms.all()
            for group in user.groups.all():
                user_func_perms = user_func_perms | group.func_perms.all()
        # cancelled_permissions = cache.get('user-{}-cancelled-permissions'.format(user.id), [])
        # if cancelled_permissions:
        #     user_func_perms = user_func_perms.exclude(codename__in=cancelled_permissions)
        return list(set(user_func_perms.values_list('codename', flat=True)))


def get_user_function_perms(user):
    user_func_perms = user.func_perms.all()
    for group in user.groups.all():
        user_func_perms = user_func_perms | group.func_perms.all()
    # cancelled_permissions = cache.get('user-{}-cancelled-permissions'.format(user.id), [])
    # if cancelled_permissions:
    #     user_func_perms = user_func_perms.exclude(codename__in=cancelled_permissions)
    return user_func_perms.distinct()


def has_view_function_module_perm(user, module_name):
    if user.is_active and user.is_superuser:
        return True
    if user.is_authenticated:
        user_permissions = get_user_function_perm_codename_list(user)
        func_perms = FunctionPermission.objects.filter(module__codename=module_name).values_list('codename',
                                                                                                 flat=True)
        if not func_perms or set(user_permissions).intersection(set(func_perms)):
            return True
    return False


def func_perm_required(perm, raise_exception=False):
    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):

            if isinstance(perm, six.string_types):
                perms = (perm,)
            else:
                perms = perm
            # First check if the user has the permission (even anon users)
            if has_function_perms(request.user, perms):
                return view_func(request, *args, **kwargs)

            # In case the 403 handler should be called raise the exception
            if raise_exception:
                raise PermissionDenied
            return redirect("/403/")

        return _wrapped_view

    return decorator


def func_perm_any_required(perm, raise_exception=False):
    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):

            if isinstance(perm, six.string_types):
                perms = (perm,)
            else:
                perms = perm
            # First check if the user has the permission (even anon users)
            if has_any_function_perms(request.user, perms):
                return view_func(request, *args, **kwargs)

            # In case the 403 handler should be called raise the exception
            if raise_exception:
                raise PermissionDenied
            return redirect("/403/")

        return _wrapped_view

    return decorator


def superuser_required(raise_exception=False):
    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):
            # First check if the user has the permission (even anon users)
            if request.user.is_active and request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # In case the 403 handler should be called raise the exception
            if raise_exception:
                raise PermissionDenied
            return redirect("/403/")

        return _wrapped_view

    return decorator


def build_user_perm_data(user):
    from farmbase.serializers import ProfileSimpleSerializer
    data = {
        "id": user.id,
        "username": user.username,
        'email': user.email,
        "groups": list(user.groups.values_list('name', flat=True)),
        "group_list": list(user.groups.values('id', 'name')),
        "perms": get_user_function_perm_codename_list(user, superuser_with_all=True),
        "is_superuser": user.is_superuser,
        "profile": ProfileSimpleSerializer(user.profile, many=False).data
    }
    groups = data['groups']
    for key, value in settings.GROUP_NAME_DICT.items():
        data["is_" + key] = True if value in groups else False
    return data
