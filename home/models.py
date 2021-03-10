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
    tags = ClusterTaggableManager(through=ContentPageTag, blank=True)
    # Web page setup
    subtitle = models.CharField(max_length=200)
    body = StreamField([
        ('paragraph', blocks.RichTextBlock()),
        ('image', ImageChooserBlock()),

    ])

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

    # IM page setup
    im_subtitle = models.CharField(max_length=200)
    im_body = StreamField([
        ('paragraph', blocks.RichTextBlock()),
        ('image', ImageChooserBlock()),

    ])

    # im_panels
    im_panels = [
        MultiFieldPanel(
            [
                FieldPanel("im_subtitle"),
                StreamFieldPanel("im_body"),
            ],
            heading="Messaging",
        ),
    ]

    promote_panels = Page.promote_panels + [
        FieldPanel('tags'),
    ]
    edit_handler = TabbedInterface(
        [
            ObjectList(web_panels, heading='Web'),
            ObjectList(im_panels, heading="Messaging"),
            ObjectList(promote_panels, heading='Promotional'),
            ObjectList(Page.settings_panels, heading='Settings'),
        ]
    )
