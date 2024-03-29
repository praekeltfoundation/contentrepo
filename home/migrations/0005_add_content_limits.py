# Generated by Django 3.1.7 on 2021-04-21 20:16

import wagtail.blocks
import wagtail.fields
import wagtail.images.blocks
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0004_auto_20210329_0955'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contentpage',
            name='messenger_body',
            field=wagtail.fields.StreamField([('paragraph', wagtail.blocks.RichTextBlock(help_text='Each paragraph cannot extend over the messenger message limit of 2000 characters')), ('image', wagtail.images.blocks.ImageChooserBlock())], blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='contentpage',
            name='viber_body',
            field=wagtail.fields.StreamField([('paragraph', wagtail.blocks.RichTextBlock(help_text='Each paragraph cannot extend over the viber message limit of 7000 characters')), ('image', wagtail.images.blocks.ImageChooserBlock())], blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='contentpage',
            name='whatsapp_body',
            field=wagtail.fields.StreamField([('paragraph', wagtail.blocks.RichTextBlock(help_text='Each paragraph cannot extend over the whatsapp message limit of 4096 characters')), ('image', wagtail.images.blocks.ImageChooserBlock())], blank=True, null=True),
        ),
    ]
