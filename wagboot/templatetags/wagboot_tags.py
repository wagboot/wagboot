# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django import template

register = template.Library()


@register.filter()
def add_class_to_field(bound_field, klass):
    existing = bound_field.field.widget.attrs.get('class')
    if existing:
        klass = "{} {}".format(existing, klass)

    return bound_field.as_widget(attrs={"class": klass})
