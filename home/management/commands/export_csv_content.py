import csv
import sys

from django.core.management.base import BaseCommand

from home.models import ContentPage, ContentPageTag, HomePage


class Command(BaseCommand):
    help = "Export content to CSV"

    def handle(self, *args, **options):
        def write_rows(rows):
            writer = csv.DictWriter(
                sys.stdout,
                fieldnames=[
                    "web_title",
                    "web_subtitle",
                    "web_body",
                    "whatsapp_title",
                    "whatsapp_body",
                    "tags",
                    "parent",
                ],
            )
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

        def get_whatsapp_messages(page):
            wa_msgs = []
            for msg in page.whatsapp_body._raw_data:
                wa_msgs.append(msg["value"]["message"])
            return wa_msgs

        def get_tags(page):
            tags = []
            for tag in ContentPageTag.objects.filter(content_object_id=page.id):
                tags.append(tag.tag.name)
            return tags

        def get_parent_page(page):
            if not HomePage.objects.filter(id=page.get_parent().id).exists():
                return page.get_parent().title

        rows = []
        for page in ContentPage.objects.all():
            row = {
                "web_title": page.title,
                "web_subtitle": page.subtitle,
                "web_body": page.body,
                "whatsapp_title": page.whatsapp_title,
                "whatsapp_body": "\n".join(get_whatsapp_messages(page)),
                "tags": ",".join(get_tags(page)),
                "parent": get_parent_page(page),
            }
            rows.append(row)

        write_rows(rows)
