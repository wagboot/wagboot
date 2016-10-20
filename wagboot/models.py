# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from email.utils import formataddr

import sass
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ValidationError
from django.db import models
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django_ace import AceWidget
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from six import python_2_unicode_compatible
from wagtail.contrib.settings.models import BaseSetting
from wagtail.contrib.settings.registry import register_setting
from wagtail.wagtailadmin.edit_handlers import FieldPanel, StreamFieldPanel, InlinePanel, PageChooserPanel
from wagtail.wagtailcore import blocks
from wagtail.wagtailcore.fields import RichTextField
from wagtail.wagtailcore.models import Page, Orderable
from wagtail.wagtaildocs.edit_handlers import DocumentChooserPanel
from wagtail.wagtailimages.blocks import ImageChooserBlock
from wagtail.wagtailimages.edit_handlers import ImageChooserPanel
from wagtail.wagtailsnippets.edit_handlers import SnippetChooserPanel
from wagtail.wagtailsnippets.models import register_snippet

from wagboot import choices
from wagboot.blocks import LoginBlock, LogoutBlock, PasswordResetBlock, PasswordChangeBlock, JumbotronBlock
from wagboot.managers import MenuManager, CssManager


@python_2_unicode_compatible
class MenuItem(Orderable, models.Model):
    parent = ParentalKey(to='wagboot.Menu', related_name='items')
    title = models.CharField(max_length=50, blank=True, null=True)
    link_external = models.CharField("External link", blank=True, null=True, max_length=255)
    link_page = models.ForeignKey('wagtailcore.Page', null=True, blank=True, related_name='+', on_delete=models.CASCADE)
    link_document = models.ForeignKey('wagtaildocs.Document', null=True, blank=True, related_name='+',
                                      on_delete = models.CASCADE)
    link_email = models.EmailField(blank=True, null=True)

    @property
    def link(self):
        if self.link_external:
            return self.link_external
        elif self.link_page:
            return self.link_page.url
        elif self.link_document:
            return self.link_document.url
        elif self.link_email:
            return "mailto:{}".format(self.link_email)
        else:
            return '/'

    panels = [
        PageChooserPanel('link_page'),
        DocumentChooserPanel('link_document'),
        FieldPanel('link_email'),
        FieldPanel('title'),
        FieldPanel('link_external'),
    ]

    @property
    def url(self):
        return self.link

    def __str__(self):
        if self.title:
            return self.title
        if self.link_page:
            return self.link_page.title
        if self.link_email:
            return self.link_email
        if self.link_document:
            return self.link_document.title
        return "(unnamed)"

    def full_clean(self, exclude=None, validate_unique=True):
        fields = ['link_page', 'link_document', 'link_email', 'link_external']
        has_value = False
        for f in fields:
            if getattr(self, f):
                if has_value:
                    raise ValidationError({f: 'Only one link can be provided'})
                has_value = True
        if not has_value:
            raise ValidationError({fields[0]: 'Some link must be provided'})

        if self.link_external and not self.title:
            raise ValidationError({'title': "External link requires title"})


@python_2_unicode_compatible
@register_snippet
class Menu(ClusterableModel):
    objects = MenuManager()
    name = models.CharField(max_length=255, null=False, blank=False)
    cta_name = models.CharField(max_length=50, null=True, blank=True)
    cta_url = models.CharField(max_length=250, blank=True, null=True)
    cta_page = models.ForeignKey('wagtailcore.Page', null=True, blank=True, related_name='+', on_delete=models.SET_NULL)

    def __str__(self):
        return self.name

    panels = [
        FieldPanel('name', classname='full title'),
        InlinePanel('items', label="Menu Items", min_num=1),
        PageChooserPanel('cta_page'),
        FieldPanel('cta_name'),
        FieldPanel('cta_url'),
    ]

    def full_clean(self, exclude=None, validate_unique=True):
        if self.cta_name and not self.cta_url and not self.cta_page:
            raise ValidationError({'cta_name': "Set CTA page or URL"})
        if self.cta_url and not self.cta_name:
            raise ValidationError({'cta_name': "Set CTA link name"})
        if self.cta_url and self.cta_url:
            raise ValidationError({
                'cta_page': "Only CTA page or URL should be set",
                'cta_url': "Only CTA page or URL should be set"
            })


@python_2_unicode_compatible
@register_snippet
class Css(ClusterableModel):
    objects = CssManager()
    name = models.CharField(max_length=255, null=False, blank=False)
    css = models.TextField(blank=True, null=True)
    _compiled_css = models.TextField(blank=True, null=True, editable=False)

    class Meta(object):
        verbose_name = 'CSS stylesheet'
        verbose_name_plural = 'CSS stylesheets'

    def __str__(self):
        return self.name

    panels = [
        FieldPanel('css', classname="full", widget=AceWidget(mode='css',
                                                             width="100%",
                                                             height="1000px",
                                                             showprintmargin=False)),
        FieldPanel('name', classname='full title'),
    ]

    def get_css(self):
        return self._compiled_css

    def full_clean(self, exclude=None, validate_unique=True):
        try:
            sass.compile(string=self.css or "")
        except sass.CompileError as e:
            raise ValidationError({'css': "{}".format(e)})

    def save(self, **kwargs):
        try:
            self._compiled_css = sass.compile(string=self.css or "")
        except Exception as e:
            self._compiled_css = "/*{}*/".format(e)
        super(Css, self).save(**kwargs)

try:
    from reversion import revisions as reversion
    reversion.register(Css)
except ImportError:
    # django_reversion is not available
    pass


class SettingsMixin(object):

    @classmethod
    def get_attr_for_site(cls, attr, site):
        """
        Lookups Settings for given site and returns requested field.
        :type attr: basestring
        :type site: django.contrib.sites.models.Site
        """
        try:
            return getattr(cls.for_site(site), attr)
        except cls.DoesNotExist:
            pass


@register_setting
class WebsiteSettings(SettingsMixin, BaseSetting):
    default_css = models.ForeignKey(Css, null=True, blank=True,
                                    help_text="Custom CSS to add to HEAD of all pages "
                                              "(after extra_head and bootstrap css, before page css)")

    container_class = models.CharField(max_length=42, choices=[('container', 'container - fixed width'),
                                                               ('container-fluid', 'container-fluid - full width')],
                                       default='container')

    bottom_extra_content = RichTextField(help_text="Will be added to the right side of bottom menu",
                                         blank=True, null=True)
    menu_logo = models.ForeignKey('wagtailimages.Image', null=True, on_delete=models.SET_NULL, related_name='+',
                                  help_text="Will be shown in top left corner unchanged")
    square_logo = models.ForeignKey('wagtailimages.Image', null=True, on_delete=models.SET_NULL,
                                    help_text="Square logo (for website icon)", related_name='+')
    extra_head = models.TextField(blank=True, null=True,
                                  help_text="Raw HTML, will be included at the end of the HEAD")

    extra_body = models.TextField(blank=True, null=True, help_text="Raw HTML, will be included at the end of the BODY")

    robots_txt = models.TextField(default="Allow /\nDisallow /cms\nDisallow /admin\n",
                                  help_text="robots.txt file. Default: Allow /\nDisallow /cms\nDisallow /admin\n "
                                            "(each on separate line)")

    login_page = models.ForeignKey('wagtailcore.Page', null=True, blank=True, related_name='+',
                                   on_delete=models.SET_NULL, help_text="Login page for restricted pages")

    from_email = models.EmailField(blank=True, null=True, help_text="Default 'from' email for emails sent to "
                                                                    "user (password resets, etc.)")
    notifications_email = models.EmailField(blank=True, null=True, help_text="For system notifications")

    panels = [
        SnippetChooserPanel('default_css'),
        FieldPanel('bottom_extra_content', classname="full"),
        ImageChooserPanel('menu_logo'),
        ImageChooserPanel('square_logo'),
        FieldPanel('extra_head', classname="full"),
        FieldPanel('extra_body', classname="full"),
        FieldPanel('robots_txt', classname="full"),
        PageChooserPanel('login_page'),
        FieldPanel('from_email'),
        FieldPanel('container_class'),
    ]

    def full_clean(self, exclude=None, validate_unique=True):
        # Login url should not be a restricted page itself
        if self.login_page and issubclass(self.login_page.specific_class, AbstractRestrictedPage):
            raise ValidationError({"login_page": "Login page should not be a restricted page"})

    @classmethod
    def get_login_url(cls, site):
        login_page = cls.get_attr_for_site('login_page', site)
        if login_page:
            return login_page.url
        return None

    @classmethod
    def get_from_email(cls, site, formatted=False):
        from_email = cls.get_attr_for_site('from_email', site)
        if from_email and formatted:
            return formataddr((site.site_name or site.hostname, from_email))
        return from_email


BASE_BLOCKS = [
    (choices.BLOCK_JUMBOTRON, JumbotronBlock()),
    (choices.BLOCK_TEXT_SMALL_IMAGE, blocks.StructBlock([
        ('text', blocks.RichTextBlock()),
        ('image', ImageChooserBlock()),
    ], label="Text, small image")),
    (choices.BLOCK_SMALL_IMAGE_TEXT, blocks.StructBlock([
        ('image', ImageChooserBlock()),
        ('text', blocks.RichTextBlock()),
    ], label="Small image, text")),
    (choices.BLOCK_IMAGE_TEXT, blocks.StructBlock([
        ('image', ImageChooserBlock()),
        ('text', blocks.RichTextBlock()),
    ], label="Image, text")),
    (choices.BLOCK_TEXT_IMAGE, blocks.StructBlock([
        ('text', blocks.RichTextBlock()),
        ('image', ImageChooserBlock()),
    ], label="Text, image")),
    (choices.BLOCK_TEXT, blocks.StructBlock([
        ('text', blocks.RichTextBlock()),
        ('text_align', blocks.ChoiceBlock(choices=choices.ALIGN_CHOICES, required=False)),
    ], label="Text")),
    (choices.BLOCK_FEATURES_CAROUSEL, blocks.ListBlock(blocks.StructBlock([
        ('image', ImageChooserBlock()),
        ('header', blocks.CharBlock(max_length=42)),
        ('short_text', blocks.TextBlock()),
        ('long_text', blocks.TextBlock()),
    ]), label="Features Carousel")),
]

GENERIC_PAGE_BLOCKS = [
    (choices.BLOCK_LOGIN, LoginBlock()),
    (choices.BLOCK_LOGOUT, LogoutBlock()),
    (choices.BLOCK_PASSWORD_RESET, PasswordResetBlock()),
]

RESTRICTED_PAGE_BLOCKS = [
    (choices.BLOCK_PASSWORD_CHANGE, PasswordChangeBlock()),
]


class BaseGenericPage(Page):
    top_menu = models.ForeignKey(Menu, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
                                 help_text="Specific top menu for this and child pages")

    bottom_menu = models.ForeignKey(Menu, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
                                    help_text="Specific bottom menu for this and child pages")

    class Meta(object):
        abstract = True

    content_panels = Page.content_panels + [
        StreamFieldPanel('body')
    ]
    settings_panels = Page.settings_panels + [
        SnippetChooserPanel('top_menu'),
        SnippetChooserPanel('bottom_menu'),
    ]

    def get_context(self, request, *args, **kwargs):
        context = super(BaseGenericPage, self).get_context(request, *args, **kwargs)

        context.update({
            'choices': choices,
            'top_menu': self.get_top_menu(),
            'bottom_menu': self.get_bottom_menu,
            # 'extra_media': self.extra_media
        })

        return context

    def get_top_menu(self):
        """
        Goes up the hierarchy of pages and gets first top_menu.
        :return: Menu
        """
        page = self
        for safety in range(100):
            if not page:
                return
            top_menu = getattr(page.specific, 'top_menu', None)
            if top_menu:
                return top_menu
            page = page.get_parent()

    def get_bottom_menu(self):
        """
        Goes up the hierarchy of pages and gets first bottom_menu.
        :return: Menu
        """
        page = self
        for safety in range(100):
            if not page:
                return
            bottom_menu = getattr(page.specific, 'bottom_menu', None)
            if bottom_menu:
                return bottom_menu
            page = page.get_parent()

    # def serve(self, request, *args, **kwargs):
    #     try:
    #         self.extra_media = []
    #         for num, stream_block in enumerate(self.body):
    #             if isinstance(stream_block.block, WagbootBlockMixin):
    #                 prefix = "block-{}".format(num)
    #                 result = stream_block.block.process_request(request, stream_block.value, prefix)
    #                 if result:
    #                     return result
    #                 media = stream_block.block.get_media(request, stream_block.value, prefix)
    #                 if media:
    #                     self.extra_media.append(media)
    #         return super(BaseGenericPage, self).serve(request, *args, **kwargs)
    #     finally:
    #         # If this object is ever shared do not leave old data around
    #         del self.extra_media


class AbstractGenericPage(BaseGenericPage):
    show_in_sitemap = models.BooleanField(verbose_name="Show in sitemap.xml",
                                          default=True,
                                          help_text="Whether this page will be shown in sitemap.xml")

    # You need to create body field like so:
    # body = StreamField(BASE_BLOCKS + GENERIC_PAGE_BLOCKS + YOUR_CUSTOM_BLOCKS)

    promote_panels = BaseGenericPage.promote_panels + [
        FieldPanel('show_in_sitemap'),
    ]

    class Meta:
        abstract = True

    def get_sitemap_urls(self):
        if self.show_in_sitemap:
            return super(AbstractGenericPage, self).get_sitemap_urls()
        return []

# Example of page:
#
# class GenericPage(AbstractGenericPage):
#     body = StreamField(BASE_BLOCKS + GENERIC_PAGE_BLOCKS + YOUR_CUSTOM_BLOCKS)


class AbstractRestrictedPage(BaseGenericPage):
    # You need to create body field like so:
    #     body = StreamField(BASE_BLOCKS + GENERIC_PAGE_BLOCKS + YOUR_CUSTOM_BLOCKS)

    class Meta(object):
        abstract = True

    # @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def serve(self, request, *args, **kwargs):
        if not request.user.is_authenticated():
            return redirect_to_login(self.url, login_url=WebsiteSettings.get_login_url(request.site))
        return super(AbstractRestrictedPage, self).serve(request, *args, **kwargs)

    def get_sitemap_urls(self):
        return []


class AbstractClearPage(Page):
    """
    Page without much formatting or menu, for terms of service etc.
    """

    body = RichTextField()

    content_panels = Page.content_panels + [
        FieldPanel('body', classname="full")
    ]

    class Meta(object):
        abstract = True

    def get_sitemap_urls(self):
        return []


class AbstractAliasPage(Page):
    """
    Page that redirects to another page.
    """
    alias_for_page = models.ForeignKey('wagtailcore.Page', related_name='aliases', on_delete=models.PROTECT)

    content_panels = Page.content_panels + [
        PageChooserPanel('alias_for_page')
    ]

    def serve(self, request, *args, **kwargs):
        return redirect(self.alias_for_page.url, permanent=False)

    class Meta(object):
        abstract = True
