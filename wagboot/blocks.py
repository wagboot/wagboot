# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import six
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.shortcuts import resolve_url
from django.template.loader import render_to_string
from django.utils.http import is_safe_url
from django.views.generic.edit import FormMixin, FormMixinBase
from wagtail.wagtailcore import blocks
from wagtail.wagtailcore.blocks import DeclarativeSubBlocksMetaclass

from wagboot import choices


_RENDERED_CONTENT = 'wagboot_rendered_content'


class ProcessBlockMixin(object):
    self_render = True
    standalone = False

    def get_context(self, value):
        context = super(ProcessBlockMixin, self).get_context(value)

        context.update({
            'choices': choices
        })
        return context

    def get_media(self, request, value, prefix):
        """
        Can provide additional media to extrahead block.
        """
        self.save_request_data(request, value, prefix)

    def render(self, value):
        content = getattr(value, _RENDERED_CONTENT)
        if not content:
            raise ValueError("Rendered content was not found, this is a bug")
        return content

    def pre_render_action(self):
        """
        Will be called before rendering template.
        Can do some actions and return HttpResponse that will returned instead of the whole page.
        If just renders the page must return None.
        Should be overridden, by default does nothing.

        All properties added to self must be cleaned in after_render_cleanup (blocks instances are shared).
        :return:
        """
        return None

    def after_render_cleanup(self):
        """
        Will be called after rendering block if some property should be cleaned up.
        (Block is shared between block instances on the page)
        """
        del self.request
        del self.prefix
        del self.block_value

    def save_request_data(self, request, value, prefix):
        self.request = request
        self.prefix = prefix
        self.block_value = value

    def get_context(self, value):
        context = super(ProcessBlockMixin, self).get_context(value)
        context.update({
            'request': self.request,
            'user': self.request.user,
            'prefix': self.prefix
        })
        return context



    def process_request(self, request, value, prefix):
        """
        Will be called by BaseGenericPage before rendering all blocks.
        If it returns HttpResponse (from pre_render_action) this response will be served instead of the page.

        :param request: HttpRequest
        :param value: Block value
        :param prefix: prefix (for forms), unique for every block on page.
        :return: None or HttpResponse
        """
        try:
            self.save_request_data(request, value, prefix)

            template = getattr(self.meta, 'template', None)
            if not template:
                raise ValueError("This block must have a template")

            try:
                response = self.pre_render_action()
                if response:
                    return response
            except ValidationError as e:
                for error in e.messages:
                    messages.error(request, "{}".format(error))

            context = self.get_context(value)

            if getattr(self.block_value, _RENDERED_CONTENT, None):
                raise ValueError("Rendered content already exists, this is a bug")
            setattr(value, _RENDERED_CONTENT, render_to_string(template, context))
        finally:
            self.after_render_cleanup()


class MetaFormBlockMixin(FormMixinBase, DeclarativeSubBlocksMetaclass):
    pass


class FormBlockMixin(ProcessBlockMixin, FormMixin):
    """
    Block that can process form data during rendering.

    It must be rendered with {% active_block block %} template tag.

    Instead of Block.render(value) this block will be rendered and processed
    in ActiveBlock.process_and_render(value, page_context) method.

    This method should look for 'POST' data submission, do operations and optionally can redirect whole page.

    Redirect is done by raising ActiveBlockRedirect(url) exception in process_and_render(..)

    It works only if page itself has used @active_block_redirect decorator on .serve().

    Generally page with active blocks should be rendered like this:

    {% for block in page.body %}
        {% if block.is_active %}
            {% active_block block %}
        {% else %}
            process blocks as usual.
        {% endif %}
    {% endfor %}

    Form block should be created this way:

    import six
    from wagtail.wagtailcore import blocks

    class MyStructFormBlock(six.with_metaclass(MetaFormBlockMixin, FormBlockMixin, blocks.StructBlock)):
        form_class = ...

    """

    def get_media(self, request, value, prefix):
        media = super(FormBlockMixin, self).get_media(request, value, prefix)
        form_class = self.get_form_class()
        if form_class:
            form_media = self.get_form(form_class).media
            if media:
                media += form_media
            else:
                media = form_media
        return media

    def form_invalid(self, form):
        raise ValueError("form_invalid is not used in FormBlock")

    def _is_data_present(self):
        """
        Checks that fields with this form's prefix are present in submission.
        If not - this POST request is not for this form.
        :return: bool
        """
        if not self.prefix:
            return True
        return any(key.startswith(self.prefix) for key in self.request.POST.keys())

    def get_form_kwargs(self):
        kwargs = super(FormBlockMixin, self).get_form_kwargs()
        if not self._is_data_present():
            # This is not our data :-( It is for some other form block on the page
            if 'data' in kwargs:
                del kwargs['data']
            if 'files' in kwargs:
                del kwargs['files']
        return kwargs

    def pre_render_action(self):
        self.form = self.get_form()
        if self.request.method.lower() == 'post' and self._is_data_present():
            if self.form.is_valid():
                return self.form_valid(self.form)

    def after_render_cleanup(self):
        super(FormBlockMixin, self).after_render_cleanup()
        del self.form

    def get_context(self, value):
        context = super(FormBlockMixin, self).get_context(value)
        context.update({
            'form': self.form
        })
        return context


class LoginBlock(six.with_metaclass(MetaFormBlockMixin, FormBlockMixin, blocks.StructBlock)):
    default_next_page = blocks.PageChooserBlock()
    legend = blocks.RichTextBlock(required=False, help_text="Text to the right of login form")

    form_class = AuthenticationForm

    class Meta:
        label = "Login Form"
        help_text = "Logs user in, and redirects to requested or default page"
        icon = "user"
        template = "wagboot/blocks/login.html"

    def _get_next_url(self):
        next_url = '/'
        if self.block_value['default_next_page']:
            next_url = self.block_value['default_next_page'].url
        return next_url

    def get_form_kwargs(self):
        kwargs = super(LoginBlock, self).get_form_kwargs()
        kwargs.update({
            'request': self.request
        })
        return kwargs

    def form_valid(self, form):
        # Okay, security check complete. Log the user in.
        login(self.request, form.get_user())
        return super(LoginBlock, self).form_valid(form)

    def get_success_url(self):
        redirect_to = self.request.POST.get(REDIRECT_FIELD_NAME,
                                            self.request.GET.get(REDIRECT_FIELD_NAME,
                                                                 self._get_next_url()))
        if not is_safe_url(url=redirect_to, host=self.request.get_host()):
            redirect_to = resolve_url(settings.LOGIN_REDIRECT_URL)

        return redirect_to


class LogoutBlock(ProcessBlockMixin, blocks.StructBlock):
    confirm_logout = blocks.BooleanBlock(default=True,
                                         required=False,
                                         help_text="Show page before log out")

    next_page = blocks.PageChooserBlock(required=False)


    class Meta:
        label = "Logout block"
        help_text = "Logs user out. Redirects to the given page or root of the website"
        icon = "user"
        template = "wagboot/blocks/logout.html"

    def get_success_url(self):
        next_url = '/'
        if self.block_value['next_page']:
            next_url = self.block_value['next_page'].url
        return next_url

    def pre_render_action(self):
        if self.request.method.lower() == 'post' and self.request.POST.get('{}-logout'.format(self.prefix)):
            logout(self.request)
            return HttpResponseRedirect(self.get_success_url())
