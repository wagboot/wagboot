# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.http import HttpResponse, HttpResponseRedirect

from wagboot.models import WebsiteSettings


def robots_txt(request):
    website_settings = WebsiteSettings.for_site(request.site)

    return HttpResponse(content=website_settings.robots_txt or "Allow /\n", content_type="text/plain")


def redirect_to_login(request):
    """
    We don't have fixed login view.
    So this view redirects to the currently selected login page in WebsiteSettings.login_page.
    If it does not exists it redirects to root.
    """

    login_url = WebsiteSettings.get_login_url(request.site)
    return HttpResponseRedirect(login_url or '/')

