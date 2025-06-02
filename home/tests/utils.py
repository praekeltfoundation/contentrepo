from taggit.models import Tag
from wagtail import blocks
from wagtail.blocks import StreamValue, StructValue  # type: ignore
from wagtail.blocks.list_block import ListValue  # type: ignore
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.images.blocks import ImageChooserBlock
from wagtail.models import Locale
from wagtail.rich_text import RichText  # type: ignore

from home.models import (  # isort:skip
    ContentPage,
    ContentPageRating,
    ContentQuickReply,
    HomePage,
    MediaBlock,
    VariationBlock,
    NextMessageButton,
    GoToPageButton,
    GoToFormButton,
    WhatsAppTemplate,
)
from typing import Any


def create_page(
    title: str = "Test Title",
    parent: Any | None = None,
    tags: tuple[str, ...] = (),
    is_new_whatsapp_template: bool = False,
    add_example_values: bool = False,
    add_variation: bool = False,
    has_quick_replies: bool = False,
    whatsapp_template_slug: str = "",
    has_buttons: bool = False,
    ContentPage: Any = ContentPage,
) -> Any:
    block = blocks.StructBlock(
        [
            ("message", blocks.TextBlock()),
            ("image", ImageChooserBlock()),
            ("media", MediaBlock()),
            ("document", DocumentChooserBlock()),
            ("variation_messages", blocks.ListBlock(VariationBlock())),
            (
                "buttons",
                blocks.StreamBlock(
                    [
                        ("next_message", NextMessageButton()),
                        ("go_to_page", GoToPageButton()),
                        ("go_to_form", GoToFormButton()),
                    ]
                ),
            ),
        ]
    )
    message = "Test WhatsApp Message 1"
    example_values = []
    if add_example_values:
        message = "Test WhatsApp Message with two variables, {{1}} and {{2}}"
        example_values = ["Example Value 1", "Example Value 2"]

    variation_messages = []
    if add_variation:
        variation_messages = [
            {
                "variation_restrictions": [{"type": "gender", "value": "female"}],
                "message": f"{title} - female variation",
            }
        ]
    whatsapp_message = block.to_python(
        {
            "message": message,
            "image": None,
            "list_items": [],
            "buttons": (
                [
                    {"type": "next_message", "value": {"title": "button 1"}},
                    {"type": "next_message", "value": {"title": "button 2"}},
                ]
                if has_buttons
                else []
            ),
            "media": None,
            "document": None,
            "example_values": example_values,
            "variation_messages": variation_messages,
        }
    )

    whatsapp_body = [
        ("Whatsapp_Message", whatsapp_message),
    ]

    if is_new_whatsapp_template:
        if add_example_values:
            message = "Test WhatsApp Message with two variables, {{1}} and {{2}}"
            template_example_values = [
                ("example_values", "Ev1"),
                ("example_values", "Ev2"),
            ]
        else:
            message = "Test Whatsapp Template message"
            template_example_values = []
        whatsapp_template = WhatsAppTemplate.objects.create(
            slug=whatsapp_template_slug,
            category="UTILITY",
            message=message,
            buttons=(
                [
                    {"type": "next_message", "value": {"title": "button 1"}},
                    {"type": "next_message", "value": {"title": "button 2"}},
                ]
                if has_buttons
                else []
            ),
            locale=Locale.objects.get(language_code="en"),
            example_values=template_example_values,
            submission_name="testname",
            submission_status="NOT_SUBMITTED_YET",
            submission_result="test result",
        )
        whatsapp_body.insert(0, ("Whatsapp_Template", whatsapp_template))

    contentpage = ContentPage(
        title=title,
        subtitle="Test Subtitle",
        enable_whatsapp=True,
        whatsapp_title="WA Title",
        whatsapp_body=whatsapp_body,
    )

    if has_quick_replies:
        created_qr, _ = ContentQuickReply.objects.get_or_create(name="button 1")
        contentpage.quick_replies.add(created_qr)
        created_qr, _ = ContentQuickReply.objects.get_or_create(name="button 2")
        contentpage.quick_replies.add(created_qr)
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


def create_page_rating(
    page: ContentPage, helpful: bool = True, comment: str = ""
) -> ContentPageRating:
    return ContentPageRating.objects.create(
        page=page,
        revision=page.get_latest_revision(),
        helpful=helpful,
        comment=comment,
    )


def unwagtail(val):  # type: ignore[no-untyped-def] # No type info
    """
    Recursively convert values from the various Wagtail StreamField types to
    something we can more easily assert on.
    """
    match val:
        case StreamValue():  # type: ignore[misc] # No type info
            return [(b.block_type, unwagtail(b.value)) for b in val]
        case StructValue():  # type: ignore[misc] # No type info
            return {k: unwagtail(v) for k, v in val.items()}
        case ListValue():  # type: ignore[misc] # No type info
            return [unwagtail(v) for v in val]
        case RichText():  # type: ignore[misc] # No type info
            return val.source
        case _:
            return val
