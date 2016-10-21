# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.http import HttpResponsePermanentRedirect
from django.http import HttpResponseRedirect


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
               "some actions. To enable this functionality you need to include wagboot blocks into page subclasses " \
               "of BaseGenericPage only. " \
               "(redirect was for url: {self.url}, permanent: {self.permanent})".format(self=self)

    def create_redirect_response(self):
        if self.permanent:
            return HttpResponsePermanentRedirect(redirect_to=self.url)
        return HttpResponseRedirect(redirect_to=self.url)
