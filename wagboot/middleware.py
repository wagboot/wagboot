# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.http import HttpResponsePermanentRedirect
from django.http import HttpResponseRedirect

from wagboot.exceptions import RedirectException


class RedirectMiddleware(object):

    @staticmethod
    def process_exception(request, exception):
        if isinstance(exception, RedirectException):
            if exception.permanent:
                return HttpResponsePermanentRedirect(redirect_to=exception.url)
            return HttpResponseRedirect(redirect_to=exception.url)
