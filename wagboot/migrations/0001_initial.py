# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.db.models.deletion
import modelcluster.fields
import wagtail.wagtailcore.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wagtaildocs', '0004_capitalizeverbose'),
        ('wagtailimages', '0010_change_on_delete_behaviour'),
        ('wagtailcore', '0023_alter_page_revision_on_delete_behaviour'),
    ]

    operations = [
        migrations.CreateModel(
            name='Css',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('css', models.TextField(null=True, blank=True)),
                ('_compiled_css', models.TextField(null=True, editable=False, blank=True)),
            ],
            options={
                'verbose_name_plural': 'CSS stylesheets',
                'verbose_name': 'CSS stylesheet',
            },
        ),
        migrations.CreateModel(
            name='Menu',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('cta_name', models.CharField(null=True, max_length=50, blank=True)),
                ('cta_url', models.CharField(null=True, max_length=250, blank=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='MenuItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sort_order', models.IntegerField(null=True, editable=False, blank=True)),
                ('title', models.CharField(max_length=50)),
                ('link_external', models.CharField(null=True, blank=True, max_length=255, verbose_name='External link')),
                ('link_email', models.EmailField(null=True, max_length=254, blank=True)),
                ('link_document', models.ForeignKey(null=True, related_name='+', blank=True, to='wagtaildocs.Document')),
                ('link_page', models.ForeignKey(null=True, related_name='+', blank=True, to='wagtailcore.Page')),
                ('parent', modelcluster.fields.ParentalKey(related_name='items', to='wagboot.Menu')),
            ],
            options={
                'ordering': ['sort_order'],
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='RestrictedPagesSettings',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bottom_menu', models.ForeignKey(null=True, related_name='+', blank=True, help_text='To show separate bottom menu on restricted pages (optional)', on_delete=django.db.models.deletion.SET_NULL, to='wagboot.Menu')),
                ('site', models.OneToOneField(editable=False, to='wagtailcore.Site')),
                ('top_menu', models.ForeignKey(null=True, related_name='+', blank=True, help_text='To show separate menu on restricted pages (optional)', on_delete=django.db.models.deletion.SET_NULL, to='wagboot.Menu')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='WebsiteSettings',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bottom_extra_content', wagtail.wagtailcore.fields.RichTextField(help_text='Will be added to the right side of bottom menu', null=True, blank=True)),
                ('extra_head', models.TextField(help_text='Raw HTML, will be included at the end of the HEAD', null=True, blank=True)),
                ('extra_body', models.TextField(help_text='Raw HTML, will be included at the end of the BODY', null=True, blank=True)),
                ('robots_txt', models.TextField(help_text='robots.txt file. Default: Allow /\nDisallow /cms\nDisallow /admin\n (each on separate line)', default='Allow /\nDisallow /cms\nDisallow /admin\n')),
                ('bottom_menu', models.ForeignKey(null=True, related_name='+', blank=True, help_text='For every generic page (optional)', on_delete=django.db.models.deletion.SET_NULL, to='wagboot.Menu')),
                ('default_css', models.ForeignKey(null=True, blank=True, help_text='Custom CSS to add to HEAD of all pages (after extra_head and bootstrap css, before page css)', to='wagboot.Css')),
                ('menu_logo', models.ForeignKey(null=True, related_name='+', help_text='Will be shown in top left corner unchanged', on_delete=django.db.models.deletion.SET_NULL, to='wagtailimages.Image')),
                ('site', models.OneToOneField(editable=False, to='wagtailcore.Site')),
                ('square_logo', models.ForeignKey(null=True, related_name='+', help_text='Square logo (for website icon)', on_delete=django.db.models.deletion.SET_NULL, to='wagtailimages.Image')),
                ('top_menu', models.ForeignKey(null=True, related_name='+', blank=True, help_text='For every generic page (optional)', on_delete=django.db.models.deletion.SET_NULL, to='wagboot.Menu')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
