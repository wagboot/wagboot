# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wagboot', '0008_add_emails_to_settings'),
    ]

    operations = [
        migrations.AddField(
            model_name='websitesettings',
            name='container_class',
            field=models.CharField(default='container', max_length='42', choices=[('container', 'container - fixed width'), ('container-fluid', 'container-fluid - full width')]),
        ),
    ]
