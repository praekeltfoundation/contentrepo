import csv
from wagtail.core import blocks
from django.core.management.base import BaseCommand
from home.models import ContentPage, HomePage
from wagtail.core.rich_text import RichText
from taggit.models import Tag


class Command(BaseCommand):
    help = "Imports content via CSV"

    def add_arguments(self, parser):
        parser.add_argument("path")

    def handle(self, *args, **options):
        def get_rich_text_body(row):
            body = []
            row = row.splitlines()
            for line in row:
                if len(line) != 0:
                    body = body + [("paragraph", RichText(line))]
            return body

        def get_text_body(raw):
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

        def create_tags(row, page):
            tags = row[12].split(" ")
            for tag in tags:
                created_tag, _ = Tag.objects.get_or_create(name=tag)
                page.tags.add(created_tag)

        path = options["path"]
        home_page = HomePage.objects.first()
        with open(path, "rt") as f:
            reader = csv.reader(f)
            for row in reader:
                contentpage = ContentPage(
                    title=row[0],
                    subtitle=row[1],
                    body=get_rich_text_body(row[2]),
                    whatsapp_title=row[3],
                    whatsapp_body=get_text_body(row[5]),
                )
                create_tags(row, contentpage)
                if row[13]:
                    parent = ContentPage.objects.filter(title=row[13])[0]
                    parent.add_child(instance=contentpage)
                else:
                    home_page.add_child(instance=contentpage)
                contentpage.save_revision()

            self.stdout.write(self.style.SUCCESS("Successfully imported Content Pages"))
