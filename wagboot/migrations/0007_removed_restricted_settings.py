# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wagtailcore', '0023_alter_page_revision_on_delete_behaviour'),
        ('wagboot', '0006_removed_menus_from_settings'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='restrictedpagessettings',
            name='bottom_menu',
        ),
        migrations.RemoveField(
            model_name='restrictedpagessettings',
            name='login_page',
        ),
        migrations.RemoveField(
            model_name='restrictedpagessettings',
            name='site',
        ),
        migrations.RemoveField(
            model_name='restrictedpagessettings',
            name='top_menu',
        ),
        migrations.AddField(
            model_name='websitesettings',
            name='login_page',
            field=models.ForeignKey(blank=True, to='wagtailcore.Page', related_name='+', on_delete=django.db.models.deletion.SET_NULL, null=True, help_text='Login page for restricted pages'),
        ),
        migrations.DeleteModel(
            name='RestrictedPagesSettings',
        ),
    ]
