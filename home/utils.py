import csv
import io
import sys

from taggit.models import Tag
from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock
from wagtail.images.models import Image
from wagtail.models import Locale
from wagtail.rich_text import RichText

from home.models import ContentPage, HomePage


def import_content_csv(file, splitmessages=True, newline=None, purge=True, locale="en"):
    def get_rich_text_body(row):
        body = []
        row = row.splitlines()
        for line in row:
            if len(line) != 0:
                body = body + [("paragraph", RichText(line))]
        return body

    def get_body(raw, body_field, type_of_message):
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

        message_body = raw[body_field]
        if splitmessages:
            if newline:
                rows = message_body.split(newline)
                next_prompts = raw.get("next_prompt", "").split(newline)
            else:
                rows = message_body.splitlines()
                next_prompts = raw.get("next_prompt", "").splitlines()
            for i, row in enumerate(rows):
                data = {"message": row.strip()}
                msg_blocks = [("message", blocks.TextBlock())]

                if type_of_message == "Whatsapp_Message":
                    if len(next_prompts) > i:
                        data["next_prompt"] = next_prompts[i]
                        msg_blocks.append(("next_prompt", blocks.TextBlock()))
                    elif len(next_prompts) == 1:
                        data["next_prompt"] = next_prompts[0]
                        msg_blocks.append(("next_prompt", blocks.TextBlock()))

                if row:
                    block = blocks.StructBlock(msg_blocks)
                    block_value = block.to_python(data)
                    struct_blocks.append((type_of_message, block_value))
            return struct_blocks
        else:
            if message_body:
                block = blocks.StructBlock(
                    [
                        ("message", blocks.TextBlock()),
                    ]
                )
                block_value = block.to_python({"message": message_body})
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
            "next_prompt",
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
                whatsapp_body=get_body(row, "whatsapp_body", "Whatsapp_Message"),
                quick_replies=add_quick_replies(row["quick_replies"]),
                locale=home_page.locale,
            )
        else:
            page.enable_whatsapp = True
            page.whatsapp_title = row["whatsapp_title"]
            page.whatsapp_body = get_body(row, "whatsapp_body", "Whatsapp_Message")
            return page

    def add_messenger(row, page=None):
        if "messenger_title" not in row.keys() or not row["messenger_title"]:
            return page

        if not page:
            return ContentPage(
                title=row["messenger_title"],
                enable_messenger=True,
                messenger_title=row["messenger_title"],
                messenger_body=get_body(row, "messenger_body", "messenger_block"),
                messenger_quick_replies=add_quick_replies(row["quick_replies"]),
                locale=home_page.locale,
            )
        else:
            page.enable_messenger = True
            page.messenger_title = row["messenger_title"]
            page.messenger_body = get_body(row, "messenger_body", "messenger_block")
            return page

    def add_viber(row, page=None):
        if "viber_title" not in row.keys() or not row["viber_title"]:
            return page

        if not page:
            return ContentPage(
                title=row["viber_title"],
                enable_viberr=True,
                viber_title=row["viber_title"],
                viber_body=get_body(row, "viber_body", "viber_message"),
                viber_quick_replies=add_quick_replies(row["quick_replies"]),
                locale=home_page.locale,
            )
        else:
            page.enable_viber = True
            page.viber_title = row["viber_title"]
            page.viber_body = get_body(row, "viber_body", "viber_message")
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


def export_content_csv():
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

    def write_rows(rows):
        writer = csv.DictWriter(
            sys.stdout,
            fieldnames=fieldnames,
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
    for page in ContentPage.objects.all():
        rows.append(get_rows(page))

    write_rows(rows)
