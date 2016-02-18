# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django import template
from django.utils.safestring import mark_safe

from wagboot.blocks import FormBlockMixin

register = template.Library()


@register.simple_tag(takes_context=True)
def form_block(context, block):
    if isinstance(block.block, FormBlockMixin):
        return mark_safe(block.block.process_and_render(value=block.value, page_context=context))
    return mark_safe(block.render())
