from wagtail.core import blocks
from home.models import ContentPage, ContentPageRating, HomePage
from taggit.models import Tag

def create_page(title="Test Title", parent=None, tags=[]):
    block = blocks.StructBlock(
        [
            ("message", blocks.TextBlock()),
        ]
    )
    block_value = block.to_python({"message": "test content WA"})
    contentpage = ContentPage(
        title=title,
        subtitle="Test Subtitle",
        body="The body",
        enable_whatsapp=True,
        whatsapp_title="WA Title",
        whatsapp_body=[
            ("Whatsapp_Message", block_value),
            ("Whatsapp_Message", block_value),
        ],
    )
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
    return ContentPageRating.objects.create(**{
        "page": page,
        "revision": page.get_latest_revision(),
        "helpful": helpful,
        "comment": comment
    })
