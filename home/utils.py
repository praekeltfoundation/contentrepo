import csv
import io

from home.models import ContentPage, HomePage
from taggit.models import Tag
from wagtail.core import blocks
from wagtail.core.rich_text import RichText
from wagtail.core.models import Locale
from wagtail.images.models import Image
from wagtail.images.blocks import ImageChooserBlock


def import_content_csv(file, splitmessages=True, newline=None, purge=True, locale="en"):
    def get_rich_text_body(row):
        body = []
        row = row.splitlines()
        for line in row:
            if len(line) != 0:
                body = body + [("paragraph", RichText(line))]
        return body

    def get_body(raw, type_of_message):
        struct_blocks = []
        if "image_title" in raw and raw["image_title"]:
            im = Image.objects.get(title=raw["image_title"]).id
            block = blocks.StructBlock(
                [
                    ("image", ImageChooserBlock()),
                ]
            )
            block_value = block.to_python({"image": im})
            struct_blocks.append((type_of_message, block_value))
        if splitmessages:
            if newline:
                rows = raw.split(newline)
            else:
                rows = raw.splitlines()
            for row in rows:
                if row:
                    block = blocks.StructBlock(
                        [
                            ("message", blocks.TextBlock()),
                        ]
                    )
                    block_value = block.to_python({"message": row})
                    struct_blocks.append((type_of_message, block_value))
            return struct_blocks
        else:
            if raw:
                block = blocks.StructBlock(
                    [
                        ("message", blocks.TextBlock()),
                    ]
                )
                block_value = block.to_python({"message": raw})
                struct_blocks.append((type_of_message, block_value))
                return struct_blocks

    def create_tags(row, page):
        tags = row["tags"].split(",")
        if "translation_tag" in row:
            tags.extend(row["translation_tag"].split(","))
        for tag in tags:
            created_tag, _ = Tag.objects.get_or_create(name=tag.strip())
            page.tags.add(created_tag)

    def add_quick_replies(row):
        replies = row.split(",")
        replies_body = []
        for reply in replies:
                replies_body = replies_body + [("quick_reply", reply)]
        return replies_body


    def add_parent(row, page, home_page):
        if row["parent"]:
            parent = ContentPage.objects.filter(
                title=row["parent"], locale=page.locale
            ).last()
            parent.add_child(instance=page)
        else:
            home_page.add_child(instance=page)

    def clean_row(row):
        for field in (
            "web_title",
            "web_subtitle",
            "web_body",
            "whatsapp_title",
            "whatsapp_body",
            "viber_title",
            "viber_body",
            "messenger_title",
            "messenger_body",
            "parent",
        ):
            if field in row and row[field]:
                row[field] = str(row[field]).strip()
        return row

    def add_web(row):
        if "web_title" not in row.keys() or not row["web_title"]:
            return
        page = ContentPage(
            title=row["web_title"],
            subtitle=row["web_subtitle"],
            body=get_rich_text_body(row["web_body"]),
            enable_web=True,
            locale=home_page.locale,
        )
        return page

    def add_whatsapp(row, page=None):
        if "whatsapp_title" not in row.keys() or not row["whatsapp_title"]:
            return page

        if not page:
            return ContentPage(
                title=row["whatsapp_title"],
                enable_whatsapp=True,
                whatsapp_title=row["whatsapp_title"],
                whatsapp_body=get_body(row["whatsapp_body"], "Whatsapp_Message"),
                whatsapp_quick_replies=add_quick_replies(row['quick_replies']),
                locale=home_page.locale,
            )
        else:
            page.enable_whatsapp = True
            page.whatsapp_title = row["whatsapp_title"]
            page.whatsapp_body = get_body(row["whatsapp_body"], "Whatsapp_Message")
            return page

    def add_messenger(row, page=None):
        if "messenger_title" not in row.keys() or not row["messenger_title"]:
            return page

        if not page:
            return ContentPage(
                title=row["messenger_title"],
                enable_messenger=True,
                messenger_title=row["messenger_title"],
                messenger_body=get_body(row["messenger_body"], "messenger_block"),
                messenger_quick_replies=add_quick_replies(row['quick_replies']),
                locale=home_page.locale,
            )
        else:
            page.enable_messenger = True
            page.messenger_title = row["messenger_title"]
            page.messenger_body = get_body(row["messenger_body"], "messenger_block")
            return page

    def add_viber(row, page=None):
        if "viber_title" not in row.keys() or not row["viber_title"]:
            return page

        if not page:
            return ContentPage(
                title=row["viber_title"],
                enable_viberr=True,
                viber_title=row["viber_title"],
                viber_body=get_body(row["viber_body"], "viber_message"),
                viber_quick_replies=add_quick_replies(row['quick_replies']),
                locale=home_page.locale,
            )
        else:
            page.enable_viber = True
            page.viber_title = row["viber_title"]
            page.viber_body = get_body(row["viber_body"], "viber_message")
            return page

    if purge == "yes":
        ContentPage.objects.all().delete()

    if isinstance(locale, str):
        locale = Locale.objects.get(language_code=locale)

    home_page = HomePage.objects.get(locale__pk=locale.pk)
    csv_file = file.read()
    if isinstance(csv_file, bytes):
        csv_file = csv_file.decode("utf-8")

    reader = csv.DictReader(io.StringIO(csv_file))
    for row in reader:
        row = clean_row(row)
        contentpage = add_web(row)
        contentpage = add_whatsapp(row, contentpage)
        contentpage = add_messenger(row, contentpage)
        contentpage = add_viber(row, contentpage)

        if contentpage:
            create_tags(row, contentpage)
            add_parent(row, contentpage, home_page)
            contentpage.save_revision().publish()
            try:
                pages = contentpage.tags.first().home_contentpagetag_items.all()
                for page in pages:
                    if page.content_object.pk != contentpage.pk:
                        contentpage.translation_key = (
                            page.content_object.translation_key
                        )
                        contentpage.save_revision().publish()
            except Exception as e:
                print(e)
        else:
            print(f"Content page not created for {row}")
