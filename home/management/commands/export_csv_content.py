import csv
import sys

from django.core.management.base import BaseCommand

from home.models import ContentPage, HomePage


class Command(BaseCommand):
    help = "Export content to CSV"
    fieldnames = [
        "parent",
        "web_title",
        "web_subtitle",
        "web_body",
        "whatsapp_title",
        "whatsapp_body",
        "messenger_title",
        "messenger_body",
        "viber_title",
        "viber_body",
        "image_name",
        "translation_tag",
        "tags",
        "quick_replies",
        "triggers",
        "locale",
    ]

    def handle(self, *args, **options):
        def write_rows(rows):
            writer = csv.DictWriter(
                sys.stdout,
                fieldnames=self.fieldnames,
            )
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

        def get_whatsapp_messages(page):
            wa_msgs = []
            for msg in page.whatsapp_body._raw_data:
                wa_msgs.append(msg["value"]["message"])
            return format_messages(wa_msgs)

        def get_messenger_messages(page):
            messenger_msgs = []
            for msg in page.messenger_body._raw_data:
                messenger_msgs.append(msg["value"]["message"])
            return format_messages(messenger_msgs)

        def get_viber_messages(page):
            viber_msgs = []
            for msg in page.viber_body._raw_data:
                viber_msgs.append(msg["value"]["message"])
            return format_messages(viber_msgs)

        def get_parent_page(page):
            if not HomePage.objects.filter(id=page.get_parent().id).exists():
                return page.get_parent().title

        def format_messages(message_list):
            message_delimiter = "\n\n\n"
            return message_delimiter.join(message_list)

        def format_list_from_query(unformatted_query):
            list_delimiter = ", "
            return list_delimiter.join(str(x) for x in unformatted_query)

        def get_rows(page):
            dict_row = {}
            dict_row["parent"] = get_parent_page(page)
            dict_row["web_title"] = page.title
            dict_row["web_subtitle"] = page.subtitle
            dict_row["web_body"] = page.body
            dict_row["whatsapp_title"] = page.whatsapp_title
            dict_row["whatsapp_body"] = get_whatsapp_messages(page)
            dict_row["messenger_title"] = page.messenger_title
            dict_row["messenger_body"] = get_messenger_messages(page)
            dict_row["viber_title"] = page.viber_title
            dict_row["viber_body"] = get_viber_messages(page)
            dict_row["translation_tag"] = str(page.translation_key)
            dict_row["tags"] = format_list_from_query(page.tags.all())
            dict_row["quick_replies"] = format_list_from_query(page.quick_replies.all())
            dict_row["triggers"] = format_list_from_query(page.triggers.all())
            dict_row["locale"] = page.locale
            return dict_row

        rows = []
        for page in ContentPage.objects.filter(id=1194).all():
            rows.append(get_rows(page))

        write_rows(rows)
