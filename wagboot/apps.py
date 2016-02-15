# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.apps import AppConfig
from wagtail.wagtailimages.formats import register_image_format, Format, unregister_image_format


class WagbootConfig(AppConfig):
    name = 'wagboot'

    def ready(self):
        unregister_image_format('left')
        unregister_image_format('right')
        unregister_image_format('fullwidth')

        for align in ('centered', 'left', 'right', 'inline'):
            register_image_format(Format('{}-original'.format(align), '{}, original size'.format(align.capitalize()), 'richtext-image {}'.format(align), 'original'))
            for size in ('42', '50', '72', '100', '200', '500', '800'):
                register_image_format(
                    Format('{}-{}'.format(align, size),
                           '{}, {}px'.format(align.capitalize(), size),
                           'richtext-image {}'.format(align), 'width-{s}'.format(s=size)))
