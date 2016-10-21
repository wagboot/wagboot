# -*- coding: utf-8 -*-
"""
Redirects in wagboot are done by adding special field to request.
This special field will be checked by middleware and response
will be replaced with HttpResponseRedirect.
"""
from __future__ import absolute_import, unicode_literals

import logging

from django.http import HttpResponsePermanentRedirect
from django.http import HttpResponseRedirect

REDIRECT_URL_FIELD = '_wagboot_redirect_url'
REDIRECT_PERMANENT_FIELD = '_wagboot_redirect_permanent'


def extract_redirect_data_from_request(request):
    if hasattr(request, REDIRECT_URL_FIELD) and hasattr(request, REDIRECT_PERMANENT_FIELD):
        if getattr(request, REDIRECT_PERMANENT_FIELD):
            return HttpResponsePermanentRedirect(redirect_to=getattr(request, REDIRECT_URL_FIELD))
        return HttpResponseRedirect(redirect_to=getattr(request, REDIRECT_URL_FIELD))
    return None


def mark_request_for_redirect(request, url, permanent):
    if extract_redirect_data_from_request(request):
        logging.warning("wagboot got duplicate redirect in one request, two active blocks on one page?")
        return
    setattr(request, REDIRECT_URL_FIELD, url)
    setattr(request, REDIRECT_PERMANENT_FIELD, permanent)
