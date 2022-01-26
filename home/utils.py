import csv
import io
import json
import requests

from home.models import ContentPage, HomePage
from taggit.models import Tag
from wagtail.core import blocks
from wagtail.images.models import Image
from io import BytesIO
from django.core.files.images import ImageFile
from wagtail.images.blocks import ImageChooserBlock


def import_content_csv(file, splitmessages=True, newline=None, purge=True, locale="en"):
    def get_rich_text_body(row):
        body = []
        row = row.splitlines()
        for line in row:
            if len(line) != 0:
                body = body + [("paragraph", RichText(line))]
        return body

    def get_body(raw, image_title=None):
        struct_blocks = []
        if image_title:
            im = Image.objects.get(title=image_title).id
            block = blocks.StructBlock(
                [
                    ("image", ImageChooserBlock()),
                ]
            )
            block_value = block.to_python({"image": im})
            struct_blocks.append(("Whatsapp_Message", block_value))
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
                    struct_blocks.append(("Whatsapp_Message", block_value))
            return struct_blocks
        else:
            if raw:
                block = blocks.StructBlock(
                    [
                        ("message", blocks.TextBlock()),
                    ]
                )
                block_value = block.to_python({"message": raw})
                struct_blocks.append(("Whatsapp_Message", block_value))
                return struct_blocks

    def create_tags(row, page):
        tags = row["translation_tag"].split(",")
        for tag in tags:
            created_tag, _ = Tag.objects.get_or_create(name=tag.strip())
            page.tags.add(created_tag)

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
            "parent",
        ):
            if row[field]:
                row[field] = str(row[field]).strip()
        return row

    home_page = HomePage.objects.get(locale__pk=locale.pk)
    csv_file = file.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(csv_file))
    for row in reader:
        row = clean_row(row)
        contentpage = ContentPage(
            title=row["web_title"],
            subtitle=row["web_subtitle"],
            body=get_rich_text_body(row["web_body"]),
            enable_whatsapp=True,
            whatsapp_title=row["whatsapp_title"],
            whatsapp_body=get_body(row["whatsapp_body"], row["image_name"]),
            locale=home_page.locale,
        )
        create_tags(row, contentpage)
        add_parent(row, contentpage, home_page)
        contentpage.save_revision().publish()
        try:
            pages = contentpage.tags.first().home_contentpagetag_items.all()
            for page in pages:
                if page.content_object.pk != contentpage.pk:
                    contentpage.translation_key = page.content_object.translation_key
                    contentpage.save_revision().publish()
        except Exception as e:
            print(e)
