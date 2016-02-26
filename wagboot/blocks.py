# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import random
import time
from email.utils import formataddr

import six
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME, login, logout, get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm, PasswordChangeForm
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.http import HttpResponseRedirect
from django.shortcuts import resolve_url
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.encoding import force_text, force_bytes
from django.utils.http import is_safe_url, urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.safestring import mark_safe
from django.views.generic.edit import FormMixin, FormMixinBase
from wagtail.wagtailcore import blocks
from wagtail.wagtailcore.blocks import DeclarativeSubBlocksMetaclass
from wagtail.wagtailcore.models import Site

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
        context = RequestContext(self.request, context)
        context.update({
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


class FormWithLegendBlock(six.with_metaclass(MetaFormBlockMixin, FormBlockMixin, blocks.StructBlock)):
    success_page = blocks.PageChooserBlock(help_text="Where to redirect after successful processing")
    legend = blocks.RichTextBlock(required=False, help_text="Text to the right of the form")

    form_class = None

    class Meta:
        # label = "Form"
        # help_text = "Shows form with legend on the right and redirects to the success_page"
        # icon = "fa-user-plus"
        template = "wagboot/blocks/form_with_legend.html"


    def get_success_url(self):
        # It is required, so should be present
        return self.block_value['success_page'].url


class LoginBlock(FormWithLegendBlock):

    form_class = AuthenticationForm

    class Meta:
        label = "Login Form"
        help_text = "Logs user in, and redirects to requested or default page"
        icon = "user"
        template = "wagboot/blocks/login.html"

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
                                                                 super(LoginBlock, self).get_success_url()))
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


class Empty(object):
    """
    Empty object to let NoFieldsBlock work with rendered content on it.
    """
    pass


class NoFieldsBlock(ProcessBlockMixin, blocks.Block):
    """
    Used to show some data based on logged-in user (or request) but which does not have any additional setting.
    In wagtail page editing shows label and help_text.
    """

    class Meta:
        # Set these fields:
        # label =
        # help_text =
        # icon =
        # template =
        default = Empty()
        form_classname = ''
        form_template = "wagboot/blocks/no_fields_form.html"

    def to_python(self, value):
        return Empty()

    def get_prep_value(self, value):
        return {}

    def value_from_datadict(self, data, files, prefix):
        return Empty()

    def render_form(self, value, prefix='', errors=None):
        return render_to_string(self.meta.form_template, {
            'help_text': getattr(self.meta, 'help_text', None),
            'classname': self.meta.form_classname,
            'label': self.meta.label,
        })


_RESET_TOKEN = 'reset-token'
_RESET_UID = 'reset-uid'


class EmailBlock(blocks.FieldBlock):
    def __init__(self, required=True, help_text=None, max_length=None, min_length=None, **kwargs):
        self.field = forms.EmailField(
            required=required,
            help_text=help_text,
            max_length=max_length,
            min_length=min_length
        )
        super(EmailBlock, self).__init__(**kwargs)


class PasswordResetBlock(FormWithLegendBlock):

    reset_email_subject = blocks.CharBlock(help_text="Subject of password reset email",
                                           default="Password reset")

    reset_email_text = blocks.RichTextBlock(help_text="Text of password reset email (link for reset will be displayed "
                                                      "after it)")

    reset_email_from = EmailBlock(help_text="Enter 'reply to' email for password reset emails")

    token_generator = PasswordResetTokenGenerator()

    _use_https = True

    template_email_body_html = "wagboot/blocks/password_reset_email.html"
    template_email_body_text = "wagboot/blocks/password_reset_email.txt"


    class Meta:
        label = "Password reset"
        help_text = "Sends user email with link to reset password, redirects to a given page to login"
        template = "wagboot/blocks/password_reset.html"

    def _is_valid_reset_link(self):
        """
        Checks that we came to page with reset link in URL. Need to show password changing instead of email form.
        :return: bool
        """
        return bool(self._get_valid_user())


    def _get_uid64_and_token(self):
        data = self.request.POST if (_RESET_UID in self.request.POST) else self.request.GET
        return data.get(_RESET_UID), data.get(_RESET_TOKEN)

    def get_form_class(self):
        if self._is_valid_reset_link():
            return SetPasswordForm
        else:
            return PasswordResetForm

    def get_form_kwargs(self):
        kwargs = super(PasswordResetBlock, self).get_form_kwargs()
        if self._is_valid_reset_link():
            kwargs.update({
                'user': self._get_valid_user()
            })

        return kwargs

    def get_user_model(self):
        return get_user_model()

    _sent_reset_link = False

    def get_context(self, value):
        context = super(PasswordResetBlock, self).get_context(value)

        uid64, token = self._get_uid64_and_token()

        context.update({
            'uid64': uid64,
            'token': token,
            'uid_name': _RESET_UID,
            'token_name': _RESET_TOKEN,
            'valid_link': self._is_valid_reset_link(),
            'sent_reset_link': self._sent_reset_link
        })

        return context

    def _get_valid_user(self):
        uid64, token = self._get_uid64_and_token()
        if uid64 and token:
            UserModel = self.get_user_model()
            try:
                uid = force_text(urlsafe_base64_decode(uid64))
                user = UserModel._default_manager.get(pk=uid)
            except (TypeError, ValueError, OverflowError, UserModel.DoesNotExist):
                user = None
            if user is not None and self.token_generator.check_token(user, token):
                return user

    def pre_render_action(self):
        uid64, token = self._get_uid64_and_token()
        if uid64 and token and not self._is_valid_reset_link():
            # We have some tokens, but they are not good. We show email form, but need to tell the user about error
            messages.error(self.request, "This reset link has expired, you need to request password reset again")
        return super(PasswordResetBlock, self).pre_render_action()

    def get_user_by_email(self, email):
        UserModel = self.get_user_model()
        return UserModel.objects.filter(email=email.lower(), is_active=True).first()

    def form_valid(self, form):
        if self._is_valid_reset_link():
            # Set the password for user with this token to the one in the form
            form.save()
            messages.success(self.request, "Password has been changed, please login with a new password")
            return super(PasswordResetBlock, self).form_valid(form)
        else:
            user = self.get_user_by_email(form.cleaned_data['email'])
            time.sleep(random.SystemRandom().randint(20, 80)/10.0)
            if user:
                self._sent_reset_link = True
                self._send_reset_link(user)
                messages.success(self.request, "Please check your email for instructions on resetting your password")
            else:
                messages.error(self.request, "No user with such email has been found")

            # We do not redirect in this case, only show message in template

    def _send_reset_link(self, user):
        reset_link = "{protocol}://{domain}{url}?{token_name}={token}&{uid_name}={uid64}"
        site = Site.find_for_request(self.request)

        reset_link = reset_link.format(protocol="https" if self._use_https else "http",
                                       domain=site.hostname,
                                       url=self.request.path_info,
                                       uid_name=_RESET_UID,
                                       uid64=urlsafe_base64_encode(force_bytes(user.pk)),
                                       token_name=_RESET_TOKEN,
                                       token=self.token_generator.make_token(user))

        from_email = formataddr((site.site_name or site.hostname, self.block_value['reset_email_from']))
        to_email = formataddr(("{}".format(user), user.email))
        subject = self.block_value['reset_email_subject'].replace('\n', '')

        context = {
            'reset_link': mark_safe(reset_link),
            'email_text': self.block_value['reset_email_text'],
            'site': site,
            'user': user
        }

        html_body = render_to_string(self.template_email_body_html, context=context)
        text_body = render_to_string(self.template_email_body_text, context=context)

        send_mail(subject=subject,
                  message=text_body,
                  html_message=html_body,
                  from_email=from_email,
                  recipient_list=[to_email])

    def after_render_cleanup(self):
        super(PasswordResetBlock, self).after_render_cleanup()
        self._sent_reset_link = False


class PasswordChangeBlock(FormWithLegendBlock):
    form_class = PasswordChangeForm

    class Meta:
        label = "Password change"
        help_text = "Lets user change password by entering old password first"
        template = "wagboot/blocks/password_change.html"

