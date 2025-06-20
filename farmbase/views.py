from django.conf import settings
from django.shortcuts import redirect

from gearfarm.utils.farm_response import json_response_not_found, json_response_success


def not_found(request, *args, **kwargs):
    return json_response_not_found("页面不见了")


def home(request):
    if not settings.DEVELOPMENT:
        return redirect('/dashboard/')
    return json_response_success("Hello World")
