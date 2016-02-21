# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('wagboot', '0005_menuitem_title_is_optional'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='websitesettings',
            name='bottom_menu',
        ),
        migrations.RemoveField(
            model_name='websitesettings',
            name='top_menu',
        ),
    ]
