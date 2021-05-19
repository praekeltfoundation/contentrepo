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
from wagtail.admin.forms import WagtailAdminPageForm


class ContentPageForm(WagtailAdminPageForm):

    def clean(self):
        cleaned_data = super().clean()
        whatsapp_body = cleaned_data.get("whatsapp_body")
        messenger_body = cleaned_data.get("messenger_body")
        viber_body = cleaned_data.get("viber_body")
        total_count = 0
        for block in whatsapp_body:
            if block.block_type == "paragraph":
                total_count += len(block.render())
        if total_count >= 4096:
            self.add_error(
                None, 'Whatsapp body exceeds 4096 characters')
        total_count = 0
        for block in messenger_body:
            if block.block_type == "paragraph":
                total_count += len(block.render())
        if total_count >= 2000:
            self.add_error(
                None, 'Messenger body exceeds 2000 characters')
        for block in viber_body:
            if block.block_type == "paragraph":
                total_count += len(block.render())
        if total_count >= 7000:
            self.add_error(
                None, 'Viber body exceeds 7000 characters')
        return cleaned_data


class HomePage(Page):
    subpage_types = [
        'ContentPage',
    ]


class ContentPageTag(TaggedItemBase):
    content_object = ParentalKey(
        'ContentPage',
        on_delete=models.CASCADE, related_name='tagged_items')


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
        ('image', ImageChooserBlock()), ],
        blank=True,
        null=True)

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
    whatsapp_title = models.CharField(
        max_length=200, blank=True, null=True)
    whatsapp_subtitle = models.CharField(
        max_length=200, blank=True, null=True)
    whatsapp_body = StreamField([
        ('paragraph', blocks.TextBlock(help_text="Each paragraph cannot extend over the whatsapp message limit of 4096 characters")),
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
    messenger_title = models.CharField(
        max_length=200, blank=True, null=True)
    messenger_subtitle = models.CharField(
        max_length=200, blank=True, null=True)
    messenger_body = StreamField([
        ('paragraph',
         blocks.TextBlock(help_text="Each paragraph cannot extend over the messenger message limit of 2000 characters")),
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
    viber_title = models.CharField(
        max_length=200, blank=True, null=True)
    viber_subtitle = models.CharField(
        max_length=200, blank=True, null=True)
    viber_body = StreamField([
        ('paragraph',
         blocks.TextBlock(help_text="Each paragraph cannot extend over the viber message limit of 7000 characters")),
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
    ]
    base_form_class = ContentPageForm
