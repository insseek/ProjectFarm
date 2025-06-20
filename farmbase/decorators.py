# -*- coding:utf-8 -*-
from functools import wraps
from django.utils.decorators import available_attrs, decorator_from_middleware


def csrf_ignore(view_func):
    """
    Skips the CSRF checks by setting the 'csrf_processing_done' to true.
    """

    def wrapped_view(*args, **kwargs):
        request = args[0]
        request.csrf_processing_done = True
        return view_func(*args, **kwargs)

    return wraps(view_func, assigned=available_attrs(view_func))(wrapped_view)
