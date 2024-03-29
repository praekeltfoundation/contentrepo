# Generated by Django 3.1.7 on 2021-03-11 14:24

import django.db.models.deletion
import modelcluster.contrib.taggit
import modelcluster.fields
import wagtail.blocks
import wagtail.fields
import wagtail.images.blocks
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('taggit', '0003_taggeditem_add_unique_index'),
        ('wagtailcore', '0059_apply_collection_ordering'),
        ('home', '0002_create_homepage'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContentPage',
            fields=[
                ('page_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='wagtailcore.page')),
                ('enable_web', models.BooleanField(default=False, help_text='When enabled, the API will include the web content')),
                ('enable_whatsapp', models.BooleanField(default=False, help_text='When enabled, the API will include the whatsapp content')),
                ('enable_messenger', models.BooleanField(default=False, help_text='When enabled, the API will include the messenger content')),
                ('subtitle', models.CharField(blank=True, max_length=200, null=True)),
                ('body', wagtail.fields.StreamField([('paragraph', wagtail.blocks.RichTextBlock()), ('image', wagtail.images.blocks.ImageChooserBlock())], blank=True, null=True)),
                ('whatsapp_title', models.CharField(blank=True, max_length=200, null=True)),
                ('whatsapp_subtitle', models.CharField(blank=True, max_length=200, null=True)),
                ('whatsapp_body', wagtail.fields.StreamField([('paragraph', wagtail.blocks.RichTextBlock()), ('image', wagtail.images.blocks.ImageChooserBlock())], blank=True, null=True)),
                ('messenger_title', models.CharField(blank=True, max_length=200, null=True)),
                ('messenger_subtitle', models.CharField(blank=True, max_length=200, null=True)),
                ('messenger_body', wagtail.fields.StreamField([('paragraph', wagtail.blocks.RichTextBlock()), ('image', wagtail.images.blocks.ImageChooserBlock())], blank=True, null=True)),
            ],
            options={
                'abstract': False,
            },
            bases=('wagtailcore.page',),
        ),
        migrations.CreateModel(
            name='ContentPageTag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content_object', modelcluster.fields.ParentalKey(on_delete=django.db.models.deletion.CASCADE, related_name='tagged_items', to='home.contentpage')),
                ('tag', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='home_contentpagetag_items', to='taggit.tag')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='contentpage',
            name='tags',
            field=modelcluster.contrib.taggit.ClusterTaggableManager(help_text='A comma-separated list of tags.', through='home.ContentPageTag', to='taggit.Tag', verbose_name='Tags'),
        ),
    ]
