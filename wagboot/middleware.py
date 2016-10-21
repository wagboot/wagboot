# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import django

from wagboot.redirects import extract_redirect_data_from_request

if django.VERSION >= (1, 10):
    from django.utils.deprecation import MiddlewareMixin
else:
    MiddlewareMixin = object


class RedirectMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        redirect = extract_redirect_data_from_request(request)
        if redirect:
            return redirect
        return response
