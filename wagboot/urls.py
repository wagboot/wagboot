# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.conf.urls import url

urlpatterns = [
    url(r'^robots.txt', 'wagboot.views.robots_txt', name='robots_txt'),
    url(r'^redirect-to-login', 'wagboot.views.redirect_to_login', name='redirect_to_login'),
]
