import csv
import json
from wagtail.core import blocks
from django.core.management.base import BaseCommand
from home.models import ContentPage, HomePage
from wagtail.core.rich_text import RichText
from taggit.models import Tag


class Command(BaseCommand):
    help = "Imports content via CSV"

    def add_arguments(self, parser):
        parser.add_argument("--path")
        parser.add_argument("--splitmessages", default="yes")
        parser.add_argument("--purge", default="no")

    def handle(self, *args, **options):
        def get_rich_text_body(row):
            body = []
            row = row.splitlines()
            for line in row:
                if len(line) != 0:
                    body = body + [("paragraph", RichText(line))]
            return body

        def get_text_body(raw):
            if options["splitmessages"] == "yes":
                struct_blocks = []
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
                    return [("Whatsapp_Message", block_value)]

        def create_tags(row, page):
            tags = row["tags"].split(",")
            for tag in tags:
                created_tag, _ = Tag.objects.get_or_create(name=tag.strip())
                page.tags.add(created_tag)

        def add_parent(row, page, home_page):
            if row["parent"]:
                parent = ContentPage.objects.filter(title=row["parent"])[0]
                parent.add_child(instance=page)
            else:
                home_page.add_child(instance=page)

        def clean_row(row):
            for field in ("web_title", "web_subtitle", "web_body", "whatsapp_title", "whatsapp_body", "parent"):
                if row[field]:
                    row[field] = str(row[field]).strip()
            return row

        if options["purge"] == "yes":
            ContentPage.objects.all().delete()

        path = options["path"]
        home_page = HomePage.objects.first()
        with open(path, "rt") as f:
            reader = csv.DictReader(f)
            for row in reader:
                row = clean_row(row)
                contentpage = ContentPage(
                    title=row["web_title"],
                    subtitle=row["web_subtitle"],
                    body=get_rich_text_body(row["web_body"]),
                    whatsapp_title=row["whatsapp_title"],
                    whatsapp_body=get_text_body(row["whatsapp_body"]),
                )
                create_tags(row, contentpage)
                add_parent(row, contentpage, home_page)
                contentpage.save_revision()

            self.stdout.write(self.style.SUCCESS("Successfully imported Content Pages"))
