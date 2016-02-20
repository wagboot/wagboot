# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import sass
from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
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
from wagboot.blocks import LoginBlock, LogoutBlock
from wagboot.managers import MenuManager, CssManager


@python_2_unicode_compatible
class MenuItem(Orderable, models.Model):
    parent = ParentalKey(to='wagboot.Menu', related_name='items')
    title = models.CharField(max_length=50)
    link_external = models.CharField("External link", blank=True, null=True, max_length=255)
    link_page = models.ForeignKey('wagtailcore.Page', null=True, blank=True, related_name='+')
    link_document = models.ForeignKey('wagtaildocs.Document', null=True, blank=True, related_name='+')
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
        FieldPanel('title'),
        FieldPanel('link_external'),
        PageChooserPanel('link_page'),
        DocumentChooserPanel('link_document'),
        FieldPanel('link_email'),
    ]

    @property
    def url(self):
        return self.link

    def __str__(self):
        return self.title

    def full_clean(self, exclude=None, validate_unique=True):
        fields = ['link_external', 'link_page', 'link_document', 'link_email']
        has_value = False
        for f in fields:
            if getattr(self, f):
                if has_value:
                    raise ValidationError({f: 'Only one link can be provided'})
                has_value = True
        if not has_value:
            raise ValidationError({fields[0]: 'Some link must be provided'})


@python_2_unicode_compatible
@register_snippet
class Menu(ClusterableModel):
    objects = MenuManager()
    name = models.CharField(max_length=255, null=False, blank=False)
    cta_name = models.CharField(max_length=50, null=True, blank=True)
    cta_url = models.CharField(max_length=250, blank=True, null=True)
    cta_page = models.ForeignKey('wagtailcore.Page', null=True, blank=True, related_name='+')

    def __str__(self):
        return self.name

    panels = [
        FieldPanel('name', classname='full title'),
        InlinePanel('items', label="Menu Items", min_num=1),
        FieldPanel('cta_name'),
        PageChooserPanel('cta_page'),
        FieldPanel('cta_url'),
    ]


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

BASE_BLOCKS = [
    (choices.BLOCK_JUMBOTRON, blocks.StructBlock([
        ('text', blocks.RichTextBlock()),
        ('background_image', ImageChooserBlock(required=False)),
        ('text_align', blocks.ChoiceBlock(choices=choices.JUMBOTRON_ALIGN_CHOICES, required=False)),
    ])),
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
]


class BaseGenericPage(Page):
    class Meta(object):
        abstract = True

    content_panels = Page.content_panels + [
        StreamFieldPanel('body')
    ]

    def get_context(self, request, *args, **kwargs):
        context = super(BaseGenericPage, self).get_context(request, *args, **kwargs)

        context.update({
            'choices': choices
        })

        return context

    def serve(self, request, *args, **kwargs):
        for num, stream_block in enumerate(self.body):
            if hasattr(stream_block.block, 'process_request'):
                result = stream_block.block.process_request(request, stream_block.value, "form-{}".format(num))
                if result:
                    return result
        return super(BaseGenericPage, self).serve(request, *args, **kwargs)


class AbstractGenericPage(BaseGenericPage):
    # You need to create body field like so:
    # body = StreamField(BASE_BLOCKS + GENERIC_PAGE_BLOCKS + YOUR_CUSTOM_BLOCKS)

    class Meta:
        abstract = True

# Example of page:
#
# class GenericPage(AbstractGenericPage):
#     body = StreamField(BASE_BLOCKS + GENERIC_PAGE_BLOCKS + YOUR_CUSTOM_BLOCKS)


class AbstractRestrictedPage(BaseGenericPage):
    # You need to create body field like so:
    #     body = StreamField(BASE_BLOCKS + GENERIC_PAGE_BLOCKS + YOUR_CUSTOM_BLOCKS)

    class Meta(object):
        abstract = True

    def _get_login_url(self, request):
        login_url = settings.LOGIN_URL
        try:
            restricted_pages_settings = RestrictedPagesSettings.for_site(request.site)
            if restricted_pages_settings.login_page:
                login_url = restricted_pages_settings.login_page.url
        except RestrictedPagesSettings.DoesNotExist:
            pass
        return login_url

    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def serve(self, request, *args, **kwargs):
        if not request.user.is_authenticated():
            return redirect_to_login(self.url, login_url=self._get_login_url(request))
        return super(AbstractRestrictedPage, self).serve(request, *args, **kwargs)


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


@register_setting
class WebsiteSettings(BaseSetting):
    default_css = models.ForeignKey(Css, null=True, blank=True,
                                    help_text="Custom CSS to add to HEAD of all pages "
                                              "(after extra_head and bootstrap css, before page css)")

    top_menu = models.ForeignKey(Menu, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
                                 help_text="For every generic page (optional)")
    bottom_menu = models.ForeignKey(Menu, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
                                    help_text="For every generic page (optional)")
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

    panels = [
        SnippetChooserPanel('top_menu'),
        SnippetChooserPanel('bottom_menu'),
        SnippetChooserPanel('default_css'),
        FieldPanel('bottom_extra_content', classname="full"),
        ImageChooserPanel('menu_logo'),
        ImageChooserPanel('square_logo'),
        FieldPanel('extra_head', classname="full"),
        FieldPanel('extra_body', classname="full"),
        FieldPanel('robots_txt', classname="full")
    ]


@register_setting
class RestrictedPagesSettings(BaseSetting):
    top_menu = models.ForeignKey(Menu, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
                                 help_text="To show separate menu on restricted pages (optional)")
    bottom_menu = models.ForeignKey(Menu, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
                                    help_text="To show separate bottom menu on restricted pages (optional)")

    login_page = models.ForeignKey('wagtailcore.Page', null=True, blank=True, related_name='+')

    panels = [
        SnippetChooserPanel('top_menu'),
        SnippetChooserPanel('bottom_menu'),
        PageChooserPanel('login_page')
    ]

    def full_clean(self, exclude=None, validate_unique=True):
        # Login url should not be a restricted page itself
        if self.login_page and issubclass(self.login_page.specific_class, AbstractRestrictedPage):
            raise ValidationError({'login_page': "Login page should not be a restricted page"})

