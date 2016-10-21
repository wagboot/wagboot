# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import warnings
from email.utils import formataddr

import six
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME, login, logout, get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.shortcuts import resolve_url
from django.template.loader import render_to_string
from django.utils.encoding import force_text, force_bytes, force_str
from django.utils.http import is_safe_url, urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.safestring import mark_safe
from django.views.generic.edit import FormMixin
from wagtail.wagtailcore import blocks
from wagtail.wagtailcore.blocks import DeclarativeSubBlocksMetaclass
from wagtail.wagtailimages.blocks import ImageChooserBlock

from wagboot import choices
from wagboot.forms import SetPasswordForm, PasswordResetForm
from wagboot.redirects import mark_request_for_redirect


class WagbootBlockMixin(object):
    """
    Provides additional functions and methods to custom blocks.

    - bases block context in rendering on page's context
    - adds .request to block
    - adds .block_value to block, to access actual data in methods during rendering
    - adds POST processing:
      - by using provided .prefix as a form prefix render a form on page (without action attribute)
      - override pre_render_action to do something when form gets submitted with POST
      - optionally override after_render_cleanup to delete something that was saved on a block during render
        or action processing

    Note: block must have a template for this mixin to work.

    """

    def pre_render_action(self):
        """
        Will be called before rendering template.
        Can do some actions and redirect page if its block needs redirect to another page.
        Should be overridden, by default does nothing.

        Can return dict which will be included in the context.

        :return: (optional) dict, additional context to be included during rendering.
        """

    def after_render_cleanup(self):
        """
        Will be called after rendering block if some property should be cleaned up.
        (Block is shared between block instances on the page)
        """
        del self.request
        del self.prefix
        del self.block_value

    def extract_request_data_from_context(self, value, context):
        """
        Used to save some data on the block instance for request processing.
        All this data must be cleared in after_render_cleanup.
        """

        if context is None or 'request' not in context:
            raise ValueError("This block must have access to request through context: {}".format(context))

        self.request = context['request']
        self.prefix = self._gen_prefix(value)
        self.block_value = value

    def get_context(self, value):
        context = super(WagbootBlockMixin, self).get_context(value)
        context.update({
            'prefix': self.prefix
        })
        return context

    def _gen_prefix(self, value):
        """
        Prefix generator is storing block number on request.
        Idea is - if we are generating same page all the blocks will be in the same order.
        """
        self.request._wagboot_block_counter = getattr(self.request, '_wagboot_block_counter', 0) + 1

        return 'block-{counter}'.format(counter=self.request._wagboot_block_counter)

    def redirect_page(self, url, permanent=False):
        mark_request_for_redirect(self.request, url, permanent)

    def render(self, value, context=None):
        """
        Return a text rendering of 'value', suitable for display on templates.

        Will call those methods (in this order):
        - extract_request_data_from_context():
            - saves request and actual block value for rendering
        - pre_render_action():
            - can do some processing of the GET or POST
            - may return dict to add to context before rendering
            - may redirect page (by calling redirect_page())
        - after_render_cleanup:
            - deletes saved request and other values on the object (actual block instance is reused between requests)

        :param value: Block value
        :param context: context of the page, must contain request.
        """
        if not getattr(self.meta, 'template', None):
            raise ValueError("This block must have a template")

        self.extract_request_data_from_context(value, context)

        add_context = self.pre_render_action()
        if add_context:
            if isinstance(add_context, dict):
                context.update(add_context)
            else:
                raise ValueError("pre_render_action may only return dict or nothing, got: {}".format(add_context))

        try:
            return super(WagbootBlockMixin, self).render(value, context=context)
        finally:
            self.after_render_cleanup()


class FormBlockMixin(WagbootBlockMixin, FormMixin):
    """
    Block that can process form data during rendering.

    Creates and includes form into context.

    If request method is POST, form will have data to validate (form will use prefix
    to distinguish between several forms on one page).
    If form validates block will default form_valid() requests redirect to get_success_url()

    Form needs to have .helper from crispy_forms
    If it does not have one - it will be created by get_form_helper() method.

    get_form_helper() creates default FormHelper and adds Submit input with text from get_submit_text() method.

    """
    success_message = None
    submit_text = 'Submit'

    def get_success_message(self):
        return self.success_message

    def get_success_url(self):
        raise NotImplementedError("Subclass must provide get_success_url and should not call super.")

    def form_invalid(self, form):
        """
        Subclass may override this method, but should not return anything.
        Block will re-render itself with validation errors.
        """
        # Not calling super because it calls render_to_response which is not needed
        return

    def form_valid(self, form):
        success_message = self.get_success_message()
        if success_message:
            messages.success(self.request, success_message)
        self.redirect_page(self.get_success_url())

    def _is_data_present(self):
        """
        Checks that fields with this form's prefix are present in submission.
        If not - this POST request is not for this form.
        :return: bool
        """
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

    def get_submit_text(self):
        return self.submit_text

    def get_form_helper(self):
        """
        Creates FormHelper for the given form.
        It is called only if there is no helper on the form already.

        Creates default FormHelper() and adds Submit input with get_submit_text() on it.
        :return FormHelper
        """
        helper = FormHelper()
        submit_text = self.get_submit_text()
        if submit_text:
            helper.add_input(Submit('submit_button', submit_text))
        return helper

    def pre_render_action(self):
        """
        Creates and processes form.
        form is returned as additional context.
        """
        form = self.get_form()
        if not hasattr(form, 'helper'):
            form.helper = self.get_form_helper()

        # In the ideal world we need to include form's media in the extrahead.
        # But it is very tricky. And I already really tried hard to do so.
        # Previous generation of these blocks was not ideal in other regards and was dropped.
        # So unless there are big troubles in having <link ..> in the body, we should not try to include media in
        # the head.
        form.helper.include_media = True

        if self.request.method.lower() == 'post' and self._is_data_present():
            if form.is_valid():
                should_be_none = self.form_valid(form)
            else:
                should_be_none = self.form_invalid(form)
            if should_be_none is not None:
                warnings.warn("form_valid and form_invalid in form blocks should not return anything. "
                              "Block will be re-rendered by render(). Got: {}".format(force_str(should_be_none)))
        context = super(FormBlockMixin, self).pre_render_action()
        context.update({
            'form': form
        })
        return context

try:
    # In Django <1.10 FormMixin has a meta class, and StructBlock has a meta class.
    # So our base must be complicated.
    from django.views.generic.edit import FormMixinBase

    class MetaFormBlockMixin(FormMixinBase, DeclarativeSubBlocksMetaclass):
        pass

    _BaseFormWithLegend = six.with_metaclass(MetaFormBlockMixin, FormBlockMixin, blocks.StructBlock)
except ImportError:
    # But in Django 1.10 FormMixin is simpler.
    class _BaseFormWithLegend(FormBlockMixin, blocks.StructBlock):
        pass


class FormWithLegendBlock(_BaseFormWithLegend):
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
    success_message = "You have signed in"
    submit_text = "Login"

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


class LogoutBlock(WagbootBlockMixin, blocks.StructBlock):
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
            messages.success(self.request, "You have been logged out")
            self.redirect_page(self.get_success_url())
        else:
            return super(LogoutBlock, self).pre_render_action()


class Empty(object):
    """
    Empty object to let NoFieldsBlock work with rendered content on it.
    """
    pass


class NoFieldsBlock(blocks.Block):
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

    token_generator = PasswordResetTokenGenerator()

    _use_https = True

    template_email_body_html = "wagboot/blocks/password_reset_email.html"
    template_email_body_text = "wagboot/blocks/password_reset_email.txt"

    class Meta:
        label = "Password reset"
        help_text = "Sends user email with link to reset password, redirects to a given page to login. " \
                    "Needs 'from_email' setup in website settings."
        template = "wagboot/blocks/password_reset.html"

    def _is_valid_reset_link(self):
        """
        Checks that we came to page with reset link in URL. Need to show password changing instead of email form.
        :return: bool
        """
        return bool(self._get_valid_user())

    def _get_uid64_and_token(self):
        data = self.request.POST if ('reset_uid' in self.request.POST) else self.request.GET
        return data.get('reset_uid'), data.get('reset_token')

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

        context.update({
            'valid_link': self._is_valid_reset_link(),
            'sent_reset_link': self._sent_reset_link
        })

        return context

    def get_initial(self):
        initial = super(PasswordResetBlock, self).get_initial()
        if self._is_valid_reset_link():
            uid64, token = self._get_uid64_and_token()
            initial.update({
                'reset_token': token,
                'reset_uid': uid64,
            })
        return initial

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
        from wagboot.models import WebsiteSettings
        if not WebsiteSettings.get_from_email(self.request.site):
            raise ValueError("Password reset block requires 'from_email' in website settings to be set")

        uid64, token = self._get_uid64_and_token()
        if uid64 and token and not self._is_valid_reset_link():
            # We have some tokens, but they are not good. We show email form, but need to tell the user about error
            messages.error(self.request, "This reset link has expired, you need to request password reset again")
        return super(PasswordResetBlock, self).pre_render_action()

    def get_submit_text(self):
        if self._is_valid_reset_link():
            return "Change Password"
        else:
            return "Reset Password"

    def form_valid(self, form):
        if self._is_valid_reset_link():
            # Set the password for user with this token to the one in the form
            form.save()
            messages.success(self.request, "Password has been changed, please login with a new password")
            return super(PasswordResetBlock, self).form_valid(form)
        else:
            user = form.get_user()
            self._sent_reset_link = True
            self._send_reset_link(user)
            messages.success(self.request, "Please check your email for instructions on resetting your password")
            # We do not redirect in this case, only show message in template

    def _send_reset_link(self, user):
        from wagboot.models import WebsiteSettings
        reset_link = "{protocol}://{domain}{url}?reset_token={token}&reset_uid={uid64}"

        reset_link = reset_link.format(protocol="https" if self._use_https else "http",
                                       domain=self.request.site.hostname,
                                       url=self.request.path_info,
                                       uid64=force_str(urlsafe_base64_encode(force_bytes(user.pk))),
                                       token=self.token_generator.make_token(user))

        from_email = WebsiteSettings.get_from_email(self.request.site, True)
        if not from_email:
            raise ValueError("Password reset block requires 'from_email' in website settings to be set")
        to_email = formataddr(("{}".format(user), user.email))
        subject = self.block_value['reset_email_subject'].replace('\n', '')

        context = {
            'reset_link': mark_safe(reset_link),
            'email_text': self.block_value['reset_email_text'],
            'site': self.request.site,
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
    success_message = "Password has been changed"

    submit_text = "Change Password"

    class Meta:
        label = "Password change"
        help_text = "Lets user change password by entering old password first"
        # template = "wagboot/blocks/password_change.html"

    def get_form_kwargs(self):
        kwargs = super(PasswordChangeBlock, self).get_form_kwargs()

        kwargs.update({
            'user': self.request.user
        })

        return kwargs

    def form_valid(self, form):
        form.save()
        return super(PasswordChangeBlock, self).form_valid(form)


class JumbotronBlock(blocks.StructBlock):
    text = blocks.RichTextBlock()
    background_image = ImageChooserBlock(required=False)
    text_align = blocks.ChoiceBlock(choices=choices.JUMBOTRON_ALIGN_CHOICES, required=False)

    class Meta:
        label = "Jumbotron"
        help_text = "Shows full-width block with a given text and background picture"
        icon = "image"
        template = "wagboot/blocks/jumbotron.html"


class FeaturesCarouselBlock(blocks.ListBlock):

    class Meta:
        label = "Features Carousel"
        help_text = "Shows carousel with 'features' of the product (do not use it)"
        icon = "bin"
        template = "wagboot/blocks/features_carousel.html"

    def __init__(self, *args, **kwargs):
        super(FeaturesCarouselBlock, self).__init__(blocks.StructBlock([
            ('image', ImageChooserBlock()),
            ('header', blocks.CharBlock(max_length=42)),
            ('short_text', blocks.TextBlock()),
            ('long_text', blocks.TextBlock()),
        ]))


class TextSmallImageBlock(blocks.StructBlock):
    text = blocks.RichTextBlock()
    image = ImageChooserBlock()

    class Meta:
        label = "Text and Small image"
        help_text = "Shows Text and small image to the right"
        icon = "doc-full"
        template = "wagboot/blocks/text_small_image.html"


class SmallImageTextBlock(blocks.StructBlock):
    image = ImageChooserBlock()
    text = blocks.RichTextBlock()

    class Meta:
        label = "Small image and Text"
        help_text = "Shows small image and text to the right"
        icon = "image"
        template = "wagboot/blocks/small_image_text.html"


class TextImageBlock(blocks.StructBlock):
    text = blocks.RichTextBlock()
    image = ImageChooserBlock()

    class Meta:
        label = "Text and Image"
        help_text = "Shows Text and image to the right"
        icon = "doc-full"
        template = "wagboot/blocks/text_image.html"


class ImageTextBlock(blocks.StructBlock):
    image = ImageChooserBlock()
    text = blocks.RichTextBlock()

    class Meta:
        label = "Image and Text"
        help_text = "Shows image and text to the right"
        icon = "image"
        template = "wagboot/blocks/image_text.html"


class TextBlock(blocks.StructBlock):
    text = blocks.RichTextBlock()
    text_align = blocks.ChoiceBlock(choices=choices.ALIGN_CHOICES, required=False)

    class Meta:
        label = "Text"
        help_text = "Shows text block"
        icon = "doc-full"
        template = "wagboot/blocks/text.html"
