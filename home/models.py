from django.db import models
from modelcluster.fields import ParentalKey
from modelcluster.contrib.taggit import ClusterTaggableManager
from taggit.models import TaggedItemBase
from wagtail.api import APIField
from wagtail.core.models import Page
from wagtail.core.fields import StreamField
from wagtail.core import blocks
from wagtail.images.blocks import ImageChooserBlock
from wagtail.admin.edit_handlers import (
    FieldPanel,
    MultiFieldPanel,
    StreamFieldPanel,
    ObjectList,
    TabbedInterface,
)
from wagtail_content_import.models import ContentImportMixin


class HomePage(Page):
    subpage_types = [
        'ContentPage',
    ]


class ContentPageTag(TaggedItemBase):
    content_object = ParentalKey(
        'ContentPage', on_delete=models.CASCADE, related_name='tagged_items')


class ContentPage(Page, ContentImportMixin):
    parent_page_type = [
        'HomePage',
    ]

    # general page attributes
    tags = ClusterTaggableManager(through=ContentPageTag)
    enable_web = models.BooleanField(
        default=False,
        help_text='When enabled, the API will include the web content')
    enable_whatsapp = models.BooleanField(
        default=False,
        help_text='When enabled, the API will include the whatsapp content')
    enable_messenger = models.BooleanField(
        default=False,
        help_text='When enabled, the API will include the messenger content')
    enable_viber = models.BooleanField(
        default=False,
        help_text='When enabled, the API will include the viber content')

    # Web page setup
    subtitle = models.CharField(max_length=200, blank=True, null=True)
    body = StreamField([
        ('paragraph', blocks.RichTextBlock()),
        ('image', ImageChooserBlock()),

    ], blank=True, null=True)

    # Web panels
    web_panels = [
        MultiFieldPanel(
            [
                FieldPanel("title"),
                FieldPanel("subtitle"),
                StreamFieldPanel("body"),
            ],
            heading="Web",
        ),
    ]

    # whatsapp page setup
    whatsapp_title = models.CharField(max_length=200, blank=True, null=True)
    whatsapp_subtitle = models.CharField(max_length=200, blank=True, null=True)
    whatsapp_body = StreamField([
        ('paragraph', blocks.RichTextBlock()),
        ('image', ImageChooserBlock()),
    ], blank=True, null=True)

    # whatsapp panels
    whatsapp_panels = [
        MultiFieldPanel(
            [
                FieldPanel("whatsapp_title"),
                FieldPanel("whatsapp_subtitle"),
                StreamFieldPanel("whatsapp_body"),
            ],
            heading="Whatsapp",
        ),
    ]

    # messenger page setup
    messenger_title = models.CharField(max_length=200, blank=True, null=True)
    messenger_subtitle = models.CharField(max_length=200, blank=True, null=True)
    messenger_body = StreamField([
        ('paragraph', blocks.RichTextBlock()),
        ('image', ImageChooserBlock()),
    ], blank=True, null=True)

    # messenger panels
    messenger_panels = [
        MultiFieldPanel(
            [
                FieldPanel("messenger_title"),
                FieldPanel("messenger_subtitle"),
                StreamFieldPanel("messenger_body"),
            ],
            heading="Messenger",
        ),
    ]


    # viber page setup
    viber_title = models.CharField(max_length=200, blank=True, null=True)
    viber_subtitle = models.CharField(max_length=200, blank=True, null=True)
    viber_body = StreamField([
        ('paragraph', blocks.RichTextBlock()),
        ('image', ImageChooserBlock()),
    ], blank=True, null=True)

    # viber panels
    viber_panels = [
        MultiFieldPanel(
            [
                FieldPanel("viber_title"),
                FieldPanel("viber_subtitle"),
                StreamFieldPanel("viber_body"),
            ],
            heading="Viber",
        ),
    ]

    promote_panels = Page.promote_panels + [
        FieldPanel('tags'),
    ]
    settings_panels = Page.settings_panels + [
        FieldPanel("enable_web"),
        FieldPanel("enable_whatsapp"),
        FieldPanel("enable_messenger"),
        FieldPanel("enable_viber"),
    ]
    edit_handler = TabbedInterface(
        [
            ObjectList(web_panels, heading='Web'),
            ObjectList(whatsapp_panels, heading="Whatsapp"),
            ObjectList(messenger_panels, heading="Messenger"),
            ObjectList(viber_panels, heading="Viber"),
            ObjectList(promote_panels, heading='Promotional'),
            ObjectList(settings_panels, heading='Settings'),
        ]
    )

    api_fields = [
        APIField('title'),
        APIField('subtitle'),
        APIField('body'),
        APIField('whatsapp_title'),
        APIField('whatsapp_subtitle'),
        APIField('whatsapp_body'),
        APIField('messenger_title'),
        APIField('messenger_subtitle'),
        APIField('messenger_body'),
        APIField('viber_title'),
        APIField('viber_subtitle'),
        APIField('viber_body'),
    ]
