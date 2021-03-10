from django.db import models
from modelcluster.fields import ParentalKey
from modelcluster.contrib.taggit import ClusterTaggableManager
from taggit.models import TaggedItemBase
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
class HomePage(Page):
    subpage_types = [
        'ContentPage',
    ]


class ContentPageTag(TaggedItemBase):
    content_object = ParentalKey(
        'ContentPage', on_delete=models.CASCADE, related_name='tagged_items')


class ContentPage(Page):
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

    promote_panels = Page.promote_panels + [
        FieldPanel('tags'),
    ]
    settings_panels = Page.settings_panels + [
        FieldPanel("enable_web"),
        FieldPanel("enable_whatsapp"),
        FieldPanel("enable_messenger"),
    ]
    edit_handler = TabbedInterface(
        [
            ObjectList(web_panels, heading='Web'),
            ObjectList(whatsapp_panels, heading="Whatsapp"),
            ObjectList(messenger_panels, heading="Messenger"),
            ObjectList(promote_panels, heading='Promotional'),
            ObjectList(settings_panels, heading='Settings'),
        ]
    )
