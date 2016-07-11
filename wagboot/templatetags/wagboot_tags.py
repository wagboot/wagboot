# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django import template
from wagtail.wagtailimages.templatetags.wagtailimages_tags import ImageNode

register = template.Library()


@register.filter()
def add_class_to_field(bound_field, klass):
    existing = bound_field.field.widget.attrs.get('class')
    if existing:
        klass = "{} {}".format(existing, klass)

    return bound_field.as_widget(attrs={"class": klass})


# This works the same as wagtail built-in, but accepts variable in filter spec
# Should not be needed after this is resolved https://github.com/torchbox/wagtail/issues/2090
@register.tag(name="image_with_variables")
def image(parser, token):
    from wagtail.wagtailimages.templatetags.wagtailimages_tags import image
    image_node = image(parser=parser, token=token)
    return ImageNodeWithVariables(image_expr=image_node.image_expr,
                                  output_var_name=image_node.output_var_name,
                                  attrs=image_node.attrs,
                                  filter_spec=image_node.filter_spec)


class ImageNodeWithVariables(ImageNode):
    def render(self, context):
        try:
            self.filter_spec = template.Variable(self.filter_spec).resolve(context)
        except template.VariableDoesNotExist:
            pass
        return super(ImageNodeWithVariables, self).render(context)
