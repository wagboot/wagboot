# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from functools import wraps

from django.http import HttpResponseRedirect
from django.template.loader import render_to_string
from django.views.generic.edit import FormMixin, FormMixinBase
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


class DoRedirect(Exception):
    def __init__(self, url):
        self.url = url


def check_redirect(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except DoRedirect as r:
            return HttpResponseRedirect(r.url)

    return wrapper


class MetaFormBlockMixin(FormMixinBase, DeclarativeSubBlocksMetaclass):
    pass


class FormBlockMixin(FormMixin):
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
    is_form_block = True

    def render(self, value):
        raise ValueError("This block must be rendered with {% active_block block %}")

    def form_valid(self, form):
        raise NotImplementedError("This method must save data provided by valid form and return nothing "
                                  "(block will then redirect to success url)")

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

    def process_and_render(self, value, page_context, prefix):
        self.request = page_context['request']
        self.prefix = prefix
        form = self.get_form()
        if self.request.method.lower() == 'post' and self._is_data_present():
            if form.is_valid():
                should_be_empty = self.form_valid(form)
                if should_be_empty is not None:
                    raise Warning("form_valid should not return anything in FormBlock Got: {}".format(should_be_empty))
                raise DoRedirect(url=self.get_success_url())

        template = getattr(self.meta, 'template', None)

        context = self.get_context(value)
        context.update({
            'form': form,
            'page_context': page_context
        })

        if template:
            return render_to_string(template, context)
        else:
            raise ValueError("This block must have a template")
