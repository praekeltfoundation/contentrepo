import csv
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
        parser.add_argument("--newline", default=False)

    def handle(self, *args, **options):
        def get_rich_text_body(row):
            body = []
            row = row.splitlines()
            for line in row:
                if len(line) != 0:
                    body = body + [("paragraph", RichText(line))]
            return body

        def get_text_body(raw, type_of_message):
            if options["splitmessages"] == "yes":
                struct_blocks = []
                if options["newline"]:
                    rows = raw.split(options["newline"])
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
                    return [(type_of_message, block_value)]

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
            for field in (
                "web_title",
                "web_subtitle",
                "web_body",
                "whatsapp_title",
                "whatsapp_body",
                "parent",
            ):
                if field in row and row[field]:
                    row[field] = str(row[field]).strip()
            return row

        def add_web(row):
            # if 'web_title' not in row.keys():
            if "web_title" not in row.keys() or not row["web_title"]:
                return
            page = ContentPage(
                title=row["web_title"],
                subtitle=row["web_subtitle"],
                body=get_rich_text_body(row["web_body"]),
                enable_web=True,
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
                    whatsapp_body=get_text_body(
                        row["whatsapp_body"], "Whatsapp_Message"
                    ),
                )
            else:
                page.enable_whatsapp = True
                page.whatsapp_title = row["whatsapp_title"]
                page.whatsapp_body = get_text_body(
                    row["whatsapp_body"], "Whatsapp_Message"
                )
                return page

        def add_messenger(row, page=None):
            if "messenger_title" not in row.keys() or not row["messenger_title"]:
                return page

            if not page:
                return ContentPage(
                    title=row["messenger_title"],
                    enable_messenger=True,
                    messenger_title=row["messenger_title"],
                    messenger_body=get_text_body(
                        row["messenger_body"], "messenger_block"
                    ),
                )
            else:
                page.enable_messenger = True
                page.messenger_title = row["messenger_title"]
                page.messenger_body = get_text_body(
                    row["messenger_body"], "messenger_block"
                )
                return page

        def add_viber(row, page=None):
            if "viber_title" not in row.keys() or not row["viber_title"]:
                return page

            if not page:
                return ContentPage(
                    title=row["viber_title"],
                    enable_viberr=True,
                    viber_title=row["viber_title"],
                    viber_body=get_text_body(row["viber_body"], "viber_message"),
                )
            else:
                page.enable_viber = True
                page.viber_title = row["viber_title"]
                page.viber_body = get_text_body(row["viber_body"], "viber_message")
                return page

        if options["purge"] == "yes":
            ContentPage.objects.all().delete()

        path = options["path"]
        home_page = HomePage.objects.first()
        with open(path, "rt") as f:
            reader = csv.DictReader(f)
            for row in reader:
                row = clean_row(row)
                contentpage = add_web(row)
                contentpage = add_whatsapp(row, contentpage)
                contentpage = add_messenger(row, contentpage)
                contentpage = add_viber(row, contentpage)

                if contentpage:
                    create_tags(row, contentpage)
                    add_parent(row, contentpage, home_page)
                    # contentpage.save_revision().publish()

            self.stdout.write(self.style.SUCCESS("Successfully imported Content Pages"))
