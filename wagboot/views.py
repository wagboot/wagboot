# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.http import HttpResponse

from wagboot.models import WebsiteSettings


def robots_txt(request):
    website_settings = WebsiteSettings.for_site(request.site)

    return HttpResponse(content=website_settings.robots_txt or "Allow /\n", content_type="text/plain")
