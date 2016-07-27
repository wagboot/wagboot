# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.conf.urls import url

from wagboot.views import robots_txt, redirect_to_login

urlpatterns = [
    url(r'^robots.txt', robots_txt, name='robots_txt'),
    url(r'^redirect-to-login', redirect_to_login, name='redirect_to_login'),
]
