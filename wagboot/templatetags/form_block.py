# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django import template
from django.utils.safestring import mark_safe

from wagboot.blocks import FormBlockMixin

register = template.Library()


@register.simple_tag(takes_context=True)
def form_block(context, block):
    if isinstance(block.block, FormBlockMixin):
        current_prefix = getattr(context, '_formblock_count', 0)
        context._formblock_count = current_prefix + 1
        return mark_safe(block.block.process_and_render(value=block.value,
                                                        page_context=context,
                                                        prefix='formblock-{}'.format(current_prefix)))
    return mark_safe(block.render())
