# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wagboot', '0007_removed_restricted_settings'),
    ]

    operations = [
        migrations.AddField(
            model_name='websitesettings',
            name='from_email',
            field=models.EmailField(max_length=254, null=True, blank=True, help_text="Default 'from' email for emails sent to user (password resets, etc.)"),
        ),
        migrations.AddField(
            model_name='websitesettings',
            name='notifications_email',
            field=models.EmailField(max_length=254, null=True, blank=True, help_text='For system notifications'),
        ),
    ]
