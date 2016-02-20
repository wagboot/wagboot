# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wagtailcore', '0023_alter_page_revision_on_delete_behaviour'),
        ('wagboot', '0002_restrictedpagessettings_login_page'),
    ]

    operations = [
        migrations.AddField(
            model_name='menu',
            name='cta_page',
            field=models.ForeignKey(related_name='+', null=True, blank=True, to='wagtailcore.Page'),
        ),
    ]
