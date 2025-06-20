import logging
import re

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

from auth_top.authentication import TokenAuthentication


class CsrfExemptMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # self.csrf_exempt_urls = tuple(re.compile(url) for url in settings.CSRF_EXEMPT_URLS)
        # for url in self.csrf_exempt_urls:
        #     if url.match(request.path):
        #         request.csrf_processing_done = True
        #         request._dont_enforce_csrf_checks = True
        request.csrf_processing_done = True
        request._dont_enforce_csrf_checks = True

        # 尝试Token认证 拿到用户
        # try:
        #     result = TokenAuthentication().authenticate(request)
        #     if result:
        #         request.csrf_processing_done = True
        #         request._dont_enforce_csrf_checks = True
        # except Exception as e:
        #     pass
