# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals


class RedirectException(Exception):
    """
    Indicates to middleware that one of the blocks needs to redirect the whole page to a new url.

    Requires wagboot.middleware.RedirectMiddleware in settings.
    """
    def __init__(self, url, permanent=False):
        self.url = url
        self.permanent = permanent

    def __str__(self):
        return "This exception is not an error. It is required for wagboot blocks to redirect user after " \
               "some actions. To enable this functionality you need to enable wagboot.middleware.RedirectMiddleware " \
               "(redirect url: {self.url}, permanent: {self.permanent})".format(self=self)
