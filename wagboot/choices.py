# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

LEFT = 'left'
LEFT_FULL = 'left-full'
RIGHT = 'right'
CENTER = 'center'

ALIGN_CHOICES = [
    (LEFT, 'Left'),
    (CENTER, 'Centered'),
    (RIGHT, 'Right'),
]
JUMBOTRON_ALIGN_CHOICES = [
    (LEFT, 'Left'),
    (CENTER, 'Centered'),
    (RIGHT, 'Right'),
    (LEFT_FULL, 'Left, full width'),
]
BLOCK_FEATURES_CAROUSEL = 'features_carousel'
BLOCK_IMAGE_TEXT = 'image_text'
BLOCK_JUMBOTRON = 'jumbotron'
BLOCK_LOGIN = 'login'
BLOCK_LOGOUT = 'logout'
BLOCK_SMALL_IMAGE_TEXT = 'small_image_text'
BLOCK_TEXT = 'text'
BLOCK_TEXT_IMAGE = 'text_image'
BLOCK_TEXT_SMALL_IMAGE = 'text_small_image'

STANDALONE_BLOCKS = [BLOCK_JUMBOTRON, BLOCK_FEATURES_CAROUSEL]
