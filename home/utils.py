import csv
import io
from datetime import datetime
from typing import Tuple, List

from openpyxl.styles import Border, Color, Font, NamedStyle, PatternFill, Side
from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet
from taggit.models import Tag
from wagtail import blocks
from wagtail.documents.models import Document
from wagtail.images.blocks import ImageChooserBlock
from wagtail.images.models import Image
from wagtail.models import Locale
from wagtail.query import PageQuerySet
from wagtail.rich_text import RichText
from wagtailmedia.models import Media

from home.models import ContentPage, HomePage

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
    "translation_tag",
    "tags",
    "quick_replies",
    "triggers",
    "locale",
    "next_prompt",
    "image_link",
    "doc_link",
    "media_link",
    "related_pages",
]
export_filename = f'exported_content_{datetime.now().strftime("%Y%m%d")}'


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


def get_messages(platform_body: blocks.StreamValue) -> List[dict]:
    """Formats the platform body objects into a list of dictionaries"""
    msgs = []
    for msg in platform_body:
        msgs.append(
            {
                "msg": msg.value["message"] if "message" in msg.value else None,
                "img": msg.value["image"] if "image" in msg.value else None,
                "doc": msg.value["document"] if "document" in msg.value else None,
                "med": msg.value["media"] if "media" in msg.value else None,
                "next_prompt": msg.value["next_prompt"]
                if "next_prompt" in msg.value
                else None,
            }
        )
    return msgs


def get_related_pages(page: ContentPage) -> List[str]:
    """Formats the related pages as a list of strings"""
    related_pages = []
    for related_page in page.related_pages:
        related_pages.append(related_page.value.title)
    return related_pages


def get_parent_page(page: ContentPage) -> str:
    """Get parent page title as string"""
    if not HomePage.objects.filter(id=page.get_parent().id).exists():
        return page.get_parent().title


def format_list_from_query_set(unformatted_query: PageQuerySet) -> List[str]:
    "Return list of str from a PageQuerySet"
    list_delimiter = ", "
    return list_delimiter.join(str(x) for x in unformatted_query if str(x) != "")


def get_image_link(messenging_platform_messages: dict, index: int) -> str:
    """Iterate over a dict of all whatsapp, messenger and viber messages to find a valid image,
    if an image is found in any of the platforms, the url will be saved to the sheet.
    This will take the one found, can be extended to a list of urls
    """
    image_names = []
    for platform_messages in messenging_platform_messages.values():
        if platform_messages and len(platform_messages) < index - 1:
            image_names.append(platform_messages[index]["med"])

    image_name = next(
        (image_name for image_name in image_names if image_name is not None), None
    )
    image = Image.objects.filter(title=image_name).first()
    if image:
        return image.usage_url
    return ""


def get_doc_link(messenging_platform_messages: dict, index: int) -> str:
    """Iterate over a dict of all whatsapp, messenger and viber messages to find a valid document,
    if a document is found in any of the platforms, the url will be saved to the sheet
    This will take the one found, can be extended to a list of urls
    """
    doc_names = []
    for platform_messages in messenging_platform_messages.values():
        if platform_messages and len(platform_messages) < index - 1:
            doc_names.append(platform_messages[index]["doc"])

    document_name = next(
        (doc_name for doc_name in doc_names if doc_name is not None), None
    )
    document = Document.objects.filter(title=document_name).first()
    if document:
        return document.usage_url
    return ""


def get_media_link(messenging_platform_messages: dict, index: int) -> str:
    """Iterate over a dict of all whatsapp, messenger and viber messages to find a valid media,
    if a media is found in any of the platforms, the url will be saved to the sheet
    This will take the one found, can be extended to a list of urls
    """
    med_names = []
    for platform_messages in messenging_platform_messages.values():
        if platform_messages and len(platform_messages) < index - 1:
            med_names.append(platform_messages[index]["med"])

    media_name = next(
        (med_name for med_name in med_names if med_name is not None), None
    )
    media = Media.objects.filter(title=media_name).first()
    if media:
        return media.usage_url
    return ""


def get_next_prompts(messenging_platform_messages: dict, index: int) -> str:
    """Iterate over a dict of all whatsapp, messenger and viber messages to find next prompts,
    if a next prompt is found in any of the platforms, the url will be saved to the sheet
    This will take the one found, can be extended to a list of urls
    """
    next_prompts = []
    for platform_messages in messenging_platform_messages.values():
        if platform_messages and len(platform_messages) < index - 1:
            next_prompts.append(platform_messages[index]["next_prompt"])

    next_prompt = next(
        (next_prompt for next_prompt in next_prompts if next_prompt is not None), None
    )
    if next_prompt:
        return next_prompt
    return ""


def style_sheet(wb: Workbook, sheet: Worksheet) -> Tuple[Workbook, Worksheet]:
    """Sets the style for the workbook adding any formatting that will make the sheet more aesthetically pleasing"""
    # Padding
    sheet.insert_cols(1)

    # Colours
    blue = Color(rgb="0099CCFF")

    # Boarders
    right_border = Border(right=Side(border_style="thin", color="FF000000"))

    # Fills
    blue_fill = PatternFill(patternType="solid", fgColor=blue)

    # Named Styles
    header_style = NamedStyle(name="header_style")
    menu_style = NamedStyle(name="menu_style")

    # Set attributes to styles
    header_style.font = Font(bold=True, size=12)
    menu_style.fill = blue_fill
    menu_style.font = Font(bold=True, size=10)

    # Add named styles to wb
    wb.add_named_style(header_style)
    wb.add_named_style(menu_style)

    # Set menu style for any "Menu" row
    for row in sheet.iter_rows():
        if isinstance(row[1].value, str) and "Menu" in row[1].value:
            for cell in row:
                cell.style = menu_style

    # Set header style for row 1 and 2
    for row in sheet["1:2"]:
        for cell in row:
            cell.style = header_style

    # Set dividing border for side panel
    for cell in sheet["G:G"]:
        cell.border = right_border
    return wb, sheet


def set_level_numbers(rows: List[list]) -> List[list]:
    """Sets the level number in the side panel to indicate depth of the page in a visual way"""
    menu = 0
    sub_1 = 0
    sub_2 = 0
    sub_3 = 0
    sub_4 = 0
    for row in rows:
        if row[0] == "x":
            if row[5] == 1:
                menu += 1
                row[0] = f"Menu {menu}"
                sub_1 = 0
                sub_2 = 0
                sub_3 = 0
                sub_4 = 0
            else:
                row[0] = ""
        elif row[1] == "x":
            if row[5] == 1:
                sub_1 += 1
                row[1] = f"Sub {menu}.{sub_1}"
                sub_2 = 0
                sub_3 = 0
                sub_4 = 0
            else:
                row[1] = ""
        elif row[2] == "x":
            if row[5] == 1:
                sub_2 += 1
                row[2] = f"Sub {menu}.{sub_1}.{sub_2}"
                sub_3 = 0
                sub_4 = 0
            else:
                row[2] = ""
        elif row[3] == "x":
            if row[5] == 1:
                sub_3 += 1
                row[3] = f"Sub {menu}.{sub_1}.{sub_2}.{sub_3}"
                sub_4 = 0
            else:
                row[3] = ""
        elif row[4] == "x":
            if row[5] == 1:
                sub_4 += 1
                row[4] = f"Sub {menu}.{sub_1}.{sub_2}.{sub_3}.{sub_4}"
            else:
                row[4] = ""
    return rows


def get_rows(page: ContentPage) -> List[list]:
    """Sets up row for each page including the side panel.
    Each page is returned as a list of rows"""
    actual_depth = (
        page.depth - 3
    )  # main menu is depth 3 (is this always true? root -> home -> main menu)
    padding = [""] * 6
    padding[actual_depth] = "x"
    messenging_platform_messages = {
        "whatsapp": get_messages(page.whatsapp_body),
        "viber": get_messages(page.viber_body),
        "messenger": get_messages(page.messenger_body),
    }

    rows = []
    most_messages = max(
        [len(messages) for messages in messenging_platform_messages.values()]
        + [len(page.body)]
    )
    basic_row = padding + [
        get_parent_page(page),
        page.title,
        page.subtitle,
        str(page.body),
        page.whatsapp_title,
        messenging_platform_messages["whatsapp"][0]["msg"]
        if len(messenging_platform_messages["whatsapp"]) == 1
        else "",
        page.messenger_title,
        messenging_platform_messages["messenger"][0]["msg"]
        if len(messenging_platform_messages["messenger"]) == 1
        else "",
        page.viber_title,
        messenging_platform_messages["viber"][0]["msg"]
        if len(messenging_platform_messages["viber"]) == 1
        else "",
        str(page.translation_key),
        format_list_from_query_set(page.tags.all()),
        format_list_from_query_set(page.quick_replies.all()),
        format_list_from_query_set(page.triggers.all()),
        str(page.locale),
        get_next_prompts(messenging_platform_messages, 0),
        get_image_link(messenging_platform_messages, 0),
        get_doc_link(messenging_platform_messages, 0),
        get_media_link(messenging_platform_messages, 0),
        format_list_from_query_set(get_related_pages(page)),
    ]
    if most_messages == 0:
        # if a page has no content
        basic_row[5] = 0
        return [basic_row]

    for message_index in range(most_messages):
        if message_index == 0:
            row = basic_row
        else:
            row = padding + [""] * len(fieldnames)
            row[21] = get_next_prompts(messenging_platform_messages, message_index)
            row[22] = get_image_link(messenging_platform_messages, message_index)
            row[23] = get_doc_link(messenging_platform_messages, message_index)
            row[24] = get_media_link(messenging_platform_messages, message_index)
        row[5] = message_index + 1

        if message_index < len(messenging_platform_messages["whatsapp"]):
            row[11] = messenging_platform_messages["whatsapp"][message_index]["msg"]

        if message_index < len(messenging_platform_messages["messenger"]):
            row[13] = messenging_platform_messages["messenger"][message_index]["msg"]

        if message_index < len(messenging_platform_messages["viber"]):
            row[15] = messenging_platform_messages["viber"][message_index]["msg"]
        rows.append(row)
    return rows


def add_children(temp_sheet: List[list], children: PageQuerySet) -> List[list]:
    """Recursive function that traverses the children of a page with a depth first search algorithm"""
    for child in children:
        content_page = ContentPage.objects.filter(id=child.id).first()
        row = get_rows(content_page)
        temp_sheet.extend(row)
        if content_page.has_children:
            add_children(temp_sheet, content_page.get_children())
    return temp_sheet


def get_content_sheet() -> List[list]:
    content_sheet = []
    headings = [1, 2, 3, 4, 5, "Message"] + fieldnames
    content_sheet.append(headings)
    home = HomePage.objects.filter(locale_id=1).first()
    main_menu_pages = home.get_children()

    for page in main_menu_pages:
        content_page = ContentPage.objects.filter(id=page.id).first()
        content_sheet.extend(get_rows(content_page))
        if content_page.has_children:
            content_sheet = add_children(content_sheet, content_page.get_children())
    return set_level_numbers(content_sheet)


def remove_content_sheet_sidebar(content_sheet: List[list]) -> List[list]:
    for row in content_sheet:
        del row[:6]
    return content_sheet


def export_xlsx_content() -> None:
    """Export all the contentpages to an xlsx"""
    wb = Workbook()
    worksheet = wb.active
    worksheet.merge_cells("B1:F1")
    cell = worksheet.cell(row=1, column=2)
    cell.value = "Structure"
    content_sheet = get_content_sheet()
    for row in content_sheet:
        worksheet.append(row)
    wb, worksheet = style_sheet(wb, worksheet)
    wb.save(f"{export_filename}.xlsx")


def export_csv_content() -> None:
    content_sheet = get_content_sheet()
    content_sheet = remove_content_sheet_sidebar(content_sheet)
    with open(f"{export_filename}.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(content_sheet)
