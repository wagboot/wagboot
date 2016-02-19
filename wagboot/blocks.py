# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import six
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpResponseRedirect
from django.shortcuts import resolve_url
from django.template.loader import render_to_string
from django.utils.http import is_safe_url
from django.views.generic.edit import FormMixin, FormMixinBase
from wagtail.wagtailcore import blocks
from wagtail.wagtailcore.blocks import DeclarativeSubBlocksMetaclass

from wagboot import choices


class BlockMixin(object):
    self_render = True
    standalone = False

    def get_context(self, value):
        context = super(BlockMixin, self).get_context(value)

        context.update({
            'choices': choices
        })
        return context


class MetaFormBlockMixin(FormMixinBase, DeclarativeSubBlocksMetaclass):
    pass


class FormBlockMixin(BlockMixin, FormMixin):
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
    _rendered_content = None

    def render(self, value):
        if not self._rendered_content:
            raise ValueError("Before rendering content process_request should have been called")
        return self._rendered_content

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

    def process_request(self, request, value, prefix):
        self.request = request
        self.prefix = prefix
        self.block_value = value
        form = self.get_form()
        if self.request.method.lower() == 'post' and self._is_data_present():
            if form.is_valid():
                return self.form_valid(form)

        template = getattr(self.meta, 'template', None)

        context = self.get_context(value)
        context.update({
            'form': form
        })

        if template:
            self._rendered_content = render_to_string(template, context)
        else:
            raise ValueError("This block must have a template")


class LoginBlock(six.with_metaclass(MetaFormBlockMixin, FormBlockMixin, blocks.StructBlock)):
    default_next_page = blocks.PageChooserBlock()

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


class LogoutBlock(six.with_metaclass(MetaFormBlockMixin, FormBlockMixin, blocks.StructBlock)):
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

    def process_request(self, request, value, prefix):
        self.request = request
        self.prefix = prefix
        self.block_value = value

        if self.request.method.lower() == 'post' and self._is_data_present():
            logout(request)
            return HttpResponseRedirect(self.get_success_url())

        template = getattr(self.meta, 'template', None)

        context = self.get_context(value)
        context.update({
            'prefix': self.prefix,
        })

        self._rendered_content = render_to_string(template, context)

        return None
