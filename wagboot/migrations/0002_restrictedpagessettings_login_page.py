# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wagtailcore', '0023_alter_page_revision_on_delete_behaviour'),
        ('wagboot', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='restrictedpagessettings',
            name='login_page',
            field=models.ForeignKey(related_name='+', blank=True, to='wagtailcore.Page', null=True),
        ),
    ]
