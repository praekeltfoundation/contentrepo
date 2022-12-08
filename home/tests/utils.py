from taggit.models import Tag
from wagtail import blocks
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.images.blocks import ImageChooserBlock

from home.models import (  # isort:skip
    ContentPage,
    ContentPageRating,
    ContentQuickReply,
    HomePage,
    MediaBlock,
    QuickReplyContent,
    VariationBlock,
)


def create_page(
    title="Test Title",
    parent=None,
    tags=[],
    is_whatsapp_template=False,
    add_variation=False,
    has_quick_replies=False,
):
    block = blocks.StructBlock(
        [
            ("message", blocks.TextBlock()),
            ("image", ImageChooserBlock()),
            ("media", MediaBlock()),
            ("document", DocumentChooserBlock()),
            ("variation_messages", blocks.ListBlock(VariationBlock())),
        ]
    )
    variation_messages = []
    if add_variation:
        variation_messages = [
            {
                "variation_restrictions": [{"type": "gender", "value": "female"}],
                "message": f"{title} - female variation",
            }
        ]
    block_value = block.to_python(
        {
            "message": "Test WhatsApp Message 1",
            "image": None,
            "media": None,
            "document": None,
            "variation_messages": variation_messages,
        }
    )
    # Option 1
    # quick_replies = []
    # if has_quick_replies:
    #     quick_replies = ["tag 1", "tag 2"]

    contentpage = ContentPage(
        title=title,
        subtitle="Test Subtitle",
        enable_whatsapp=True,
        whatsapp_title="WA Title",
        whatsapp_body=[("Whatsapp_Message", block_value)],
        is_whatsapp_template=is_whatsapp_template,
        # quick_replies = quick_replies, #Option 1 continued
    )
    # Option 2
    # if has_quick_replies:
    #     tag1 = ContentQuickReply(name="tag 1")
    #     tag2 = ContentQuickReply(name="tag 2")
    #     QuickReplyContent(tag=tag1, content_object=contentpage)
    #     QuickReplyContent(tag=tag2, content_object=contentpage)
    for tag in tags:
        created_tag, _ = Tag.objects.get_or_create(name=tag)
        contentpage.tags.add(created_tag)
    if parent:
        parent = ContentPage.objects.filter(title=parent)[0]
        parent.add_child(instance=contentpage)
    else:
        home_page = HomePage.objects.first()
        home_page.add_child(instance=contentpage)
    contentpage.save_revision()
    return contentpage


def create_page_rating(page, helpful=True, comment=""):
    return ContentPageRating.objects.create(
        **{
            "page": page,
            "revision": page.get_latest_revision(),
            "helpful": helpful,
            "comment": comment,
        }
    )
