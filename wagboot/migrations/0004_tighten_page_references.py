# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('wagboot', '0003_menu_cta_page'),
    ]

    operations = [
        migrations.AlterField(
            model_name='menu',
            name='cta_page',
            field=models.ForeignKey(related_name='+', to='wagtailcore.Page', null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL),
        ),
        migrations.AlterField(
            model_name='restrictedpagessettings',
            name='login_page',
            field=models.ForeignKey(related_name='+', to='wagtailcore.Page', null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL),
        ),
    ]
