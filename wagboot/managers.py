# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.db import models


class MenuManager(models.Manager):
    def get_by_natural_key(self, name):
        return self.get(menu_name=name)


class CssManager(models.Manager):
    def get_by_natural_key(self, name):
        return self.get(css_name=name)
