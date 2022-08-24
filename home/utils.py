import copy
import csv
import io
from dataclasses import dataclass
from math import ceil
from typing import List, Tuple

from django.http import HttpResponse
from openpyxl.styles import Border, Color, Font, NamedStyle, PatternFill, Side
from openpyxl.utils import get_column_letter
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

EXPORT_FIELDNAMES = [
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


def style_sheet(wb: Workbook, sheet: Worksheet) -> Tuple[Workbook, Worksheet]:
    """Sets the style for the workbook adding any formatting that will make the sheet more aesthetically pleasing"""
    # Padding
    sheet.insert_cols(1)

    # Set columns based on best size
    # Adjustment is because the size in openxlsx and google sheets are not equivalent
    adjustment = 7
    column_widths_in_pts = {
        "padding": 35,
        "1": 47,
        "2": 35,
        "3": 35,
        "4": 44,
        "5": 54,
        "Message": 110,
        "parent": 110,
        "web_title": 110,
        "web_subtitle": 110,
        "web_body": 370,
        "whatsapp_title": 118,
        "whatsapp_body": 370,
        "messenger_title": 118,
        "messenger_body": 370,
        "viber_title": 118,
        "viber_body": 370,
        "translation_tag": 118,
        "tags": 118,
        "quick_replies": 118,
        "triggers": 118,
        "locale": 118,
        "next_prompt": 118,
        "image_link": 118,
        "doc_link": 118,
        "media_link": 118,
        "related": 118,
    }

    for index, column_width in enumerate(column_widths_in_pts.values(), 1):
        sheet.column_dimensions[get_column_letter(index)].width = ceil(
            column_width / adjustment
        )

    # Freeze heading row and side panel
    sheet.freeze_panes = sheet["H3"]

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
    header_style.font = Font(bold=True, size=10)
    menu_style.fill = blue_fill
    menu_style.font = Font(bold=True, size=10)

    # Add named styles to wb
    wb.add_named_style(header_style)
    wb.add_named_style(menu_style)

    # column widths

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

    # set font on all cells initially to 10pt and row height
    general_font = Font(size=10)
    for index, row in enumerate(sheet.iter_rows()):
        if index > 2:
            sheet.row_dimensions[index].height = 60
        for cell in row:
            cell.font = general_font
            alignment = copy.copy(cell.alignment)
            alignment.wrapText = True
            cell.alignment = alignment
    return wb, sheet


def get_rows(page: ContentPage, structure_string: str) -> List[list]:
    """Sets up row for each page including the side panel.
    Each page is returned as a list of rows, this accounts for pages with multiple messages"""
    rows = []
    base_row = ContentSheetRow.from_page(page, structure_string)
    rows.append(base_row.get_row())
    if base_row.tuple_of_extra_rows:
        for extra_row in base_row.tuple_of_extra_rows:
            rows.append(extra_row.get_row())
    return rows


def add_children(
    temp_sheet: List[list],
    children: PageQuerySet,
    queryset: PageQuerySet,
    parent_structure: str,
) -> List[list]:
    """Recursive function that traverses the children of a page with a depth first search algorithm"""
    for index, child in enumerate(children, 1):
        content_page = ContentPage.objects.filter(id=child.id).first()
        structure_string = f"{parent_structure.replace('Menu','Sub')}.{index}"
        row = get_rows(content_page, structure_string)
        if row:
            temp_sheet.extend(row)
        if content_page.has_children:
            add_children(
                temp_sheet, content_page.get_children(), queryset, structure_string
            )
    return temp_sheet


def get_content_sheet(queryset: PageQuerySet) -> List[list]:
    content_sheet = []
    headings = [1, 2, 3, 4, 5, "Message"] + EXPORT_FIELDNAMES
    content_sheet.append(headings)
    for locale in Locale.objects.all():
        home = HomePage.objects.filter(locale_id=locale.id).first()
        if home:
            main_menu_pages = home.get_children()
            for index, page in enumerate(main_menu_pages, 1):
                content_page = queryset.filter(id=page.id).first()
                if content_page:
                    structure_string = f"Menu {index}"
                    row = get_rows(content_page, structure_string)
                    content_sheet.extend(row)
                    if content_page.has_children:
                        content_sheet = add_children(
                            content_sheet,
                            content_page.get_children(),
                            queryset,
                            structure_string,
                        )
    return content_sheet


def remove_content_sheet_sidebar(content_sheet: List[list]) -> List[list]:
    for row in content_sheet:
        del row[:6]
    return content_sheet


def export_xlsx_content(queryset: PageQuerySet, response: HttpResponse) -> None:
    """Export contentpages within the queryset to an xlsx"""
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.merge_cells("B1:F1")
    cell = worksheet.cell(row=1, column=2)
    cell.value = "Structure"
    content_sheet = get_content_sheet(queryset)
    for row in content_sheet:
        worksheet.append(row)
    workbook, worksheet = style_sheet(workbook, worksheet)
    workbook.save(response)


def export_csv_content(queryset: PageQuerySet, response: HttpResponse) -> None:
    """Export contentpages within the queryset to a csv"""
    content_sheet = get_content_sheet(queryset)
    content_sheet = remove_content_sheet_sidebar(content_sheet)
    writer = csv.writer(response)
    for row in content_sheet:
        writer.writerow(row)


@dataclass
class ContentSheetRow:
    side_panel_column_1: str = ""
    side_panel_column_2: str = ""
    side_panel_column_3: str = ""
    side_panel_column_4: str = ""
    side_panel_column_5: str = ""
    side_panel_message_number: int = 0
    parent: str = ""
    web_title: str = ""
    web_subtitle: str = ""
    web_body: str = ""
    whatsapp_title: str = ""
    whatsapp_body: str = ""
    messenger_title: str = ""
    messenger_body: str = ""
    viber_title: str = ""
    viber_body: str = ""
    translation_tag: str = ""
    tags: str = ""
    quick_replies: str = ""
    triggers: str = ""
    locale: str = ""
    next_prompt: str = ""
    image_link: str = ""
    doc_link: str = ""
    media_link: str = ""
    related_pages: str = ""
    tuple_of_extra_rows: tuple = ()

    @classmethod
    def from_page(
        cls,
        page: ContentPage,
        structure_string: str,
        side_panel_message_number: int = 0,
    ):
        content_sheet_row = cls()
        messaging_platform_messages = {
            "whatsapp": content_sheet_row._get_messages(page.whatsapp_body),
            "viber": content_sheet_row._get_messages(page.viber_body),
            "messenger": content_sheet_row._get_messages(page.messenger_body),
        }

        content_sheet_row._set_messages(
            page, side_panel_message_number, messaging_platform_messages
        )
        content_sheet_row._set_structure(structure_string)

        if side_panel_message_number == 0:
            content_sheet_row.parent = content_sheet_row._get_parent_page(page)
            content_sheet_row.web_title = page.title
            content_sheet_row.web_subtitle = page.subtitle
            content_sheet_row.web_body = str(page.body)
            content_sheet_row.whatsapp_title = page.whatsapp_title
            content_sheet_row.messenger_title = page.messenger_title
            content_sheet_row.viber_title = page.viber_title
            content_sheet_row.translation_tag = str(page.translation_key)
            content_sheet_row.tags = content_sheet_row._format_list_from_query_set(page.tags.all())
            content_sheet_row.quick_replies = content_sheet_row._format_list_from_query_set(
                page.quick_replies.all()
            )
            content_sheet_row.triggers = content_sheet_row._format_list_from_query_set(page.triggers.all())
            content_sheet_row.locale = str(page.locale)
            content_sheet_row.related_pages = content_sheet_row._format_list_from_query_set(
                content_sheet_row._get_related_pages(page)
            )
        return content_sheet_row

    def get_row(self):
        """Returns object as an exportable row"""
        return [
            self.side_panel_column_1,
            self.side_panel_column_2,
            self.side_panel_column_3,
            self.side_panel_column_4,
            self.side_panel_column_5,
            self.side_panel_message_number,
            self.parent,
            self.web_title,
            self.web_subtitle,
            self.web_body,
            self.whatsapp_title,
            self.whatsapp_body,
            self.messenger_title,
            self.messenger_body,
            self.viber_title,
            self.viber_body,
            self.translation_tag,
            self.tags,
            self.quick_replies,
            self.triggers,
            self.locale,
            self.next_prompt,
            self.image_link,
            self.doc_link,
            self.media_link,
            self.related_pages,
        ]

    @staticmethod
    def _format_list_from_query_set(unformatted_query: PageQuerySet) -> str:
        list_delimiter = ", "
        return list_delimiter.join(str(x) for x in unformatted_query if str(x) != "")

    @staticmethod
    def _get_parent_page(page: ContentPage) -> str:
        """Get parent page title as string"""
        if not HomePage.objects.filter(id=page.get_parent().id).exists():
            return page.get_parent().title

    @staticmethod
    def _get_messages(platform_body: blocks.StreamValue) -> List[dict]:
        """Formats the platform body objects into a list of dictionaries"""
        msgs = []
        for msg in platform_body:
            msgs.append(
                {
                    "msg": msg.value["message"].strip()
                    if "message" in msg.value
                    else None,
                    "img": msg.value["image"] if "image" in msg.value else None,
                    "doc": msg.value["document"] if "document" in msg.value else None,
                    "med": msg.value["media"] if "media" in msg.value else None,
                    "next_prompt": msg.value["next_prompt"]
                    if "next_prompt" in msg.value
                    else None,
                }
            )
        return msgs

    def _set_structure(self, structure_string: str):
        """Sets the sidebar Menu/Sub level based on structure string length,
        for example, Sub 1.2.1 is a level 3 message"""
        if "menu" in structure_string.lower():
            self.side_panel_column_1 = structure_string
        elif len(structure_string) == 7:
            self.side_panel_column_2 = structure_string
        elif len(structure_string) == 9:
            self.side_panel_column_3 = structure_string
        elif len(structure_string) == 11:
            self.side_panel_column_4 = structure_string
        elif len(structure_string) == 13:
            self.side_panel_column_5 = structure_string

    def _set_messages(
        self,
        page: ContentPage,
        side_panel_message_number: int,
        messaging_platform_messages: dict,
    ):
        """Sets all message level content, including any message level content such as documents, images, next prompts and media.
        Takes the possibility of different numbers of messages on different platforms.
        Adds multiple messages as blank rows with only the extra messages and the message number to the row to match the template"""
        self.side_panel_message_number = side_panel_message_number + 1
        most_messages = max(
            [len(messages) for messages in messaging_platform_messages.values()]
            + [len(page.body)]
        )

        if len(messaging_platform_messages["whatsapp"]) == 1 or (
            side_panel_message_number == 0
            and len(messaging_platform_messages["whatsapp"]) > 1
        ):
            self.whatsapp_body = messaging_platform_messages["whatsapp"][0]["msg"]

        if len(messaging_platform_messages["messenger"]) == 1 or (
            side_panel_message_number == 0
            and len(messaging_platform_messages["messenger"]) > 1
        ):
            self.messenger_body = messaging_platform_messages["messenger"][0]["msg"]

        if len(messaging_platform_messages["viber"]) == 1 or (
            side_panel_message_number == 0
            and len(messaging_platform_messages["viber"]) > 1
        ):
            self.viber_body = messaging_platform_messages["viber"][0]["msg"]

        self.next_prompt = self._get_next_prompt(messaging_platform_messages)
        self.doc_link = self._get_doc_link(messaging_platform_messages)
        self.image_link = self._get_image_link(messaging_platform_messages)
        self.media_link = self._get_media_link(messaging_platform_messages)

        temp_rows = []
        if side_panel_message_number == 0 and most_messages > 1:
            # Set tuple_of_extra_rows rows to account for multiple messages
            for message_index in range(1, most_messages):
                new_row = ContentSheetRow.from_page(page, "", message_index)
                if message_index < len(messaging_platform_messages["whatsapp"]):
                    new_row.whatsapp_body = messaging_platform_messages["whatsapp"][
                        message_index
                    ]["msg"]
                if message_index < len(messaging_platform_messages["messenger"]):
                    new_row.messenger_body = messaging_platform_messages["messenger"][
                        message_index
                    ]["msg"]
                if message_index < len(messaging_platform_messages["viber"]):
                    new_row.viber_body = messaging_platform_messages["viber"][
                        message_index
                    ]["msg"]
                new_row.next_prompt = self._get_next_prompt(
                    messaging_platform_messages
                )
                new_row.doc_link = self._get_doc_link(messaging_platform_messages)
                new_row.image_link = self._get_image_link(messaging_platform_messages)
                new_row.media_link = self._get_media_link(messaging_platform_messages)
                temp_rows.append(new_row)
            self.tuple_of_extra_rows = tuple(temp_rows)

    @staticmethod
    def _get_related_pages(page: ContentPage) -> List[str]:
        """Returns a list of strings of the related page titles"""
        related_pages = []
        for related_page in page.related_pages:
            related_pages.append(related_page.value.title)
        return related_pages

    @staticmethod
    def _find_first_match(
        messaging_platform_messages: dict,
        index: int,
        attachment_type: str,
    ) -> str:
        """Returns the first found link for the attachment type.
        Valid attachment types are img, doc, med, next_prompt"""
        for platform_messages in messaging_platform_messages.values():
            if (
                platform_messages
                and len(platform_messages) < index - 1
                and platform_messages[index][attachment_type]
            ):
                return platform_messages[index][attachment_type]
        return ""

    def _get_image_link(
        self, messaging_platform_messages: dict, index: int = 0
    ) -> str:
        """Iterate over a dict of whatsapp, messenger and viber messages to find a valid image for that message level,
        if an image is found in any of the platforms, the url will be saved to the sheet.
        This will take the first one found, can be extended to a list of urls
        """
        image_name = self._find_first_match(messaging_platform_messages, index, "img")
        image = Image.objects.filter(title=image_name).first()
        if image:
            return image.usage_url
        return ""

    def _get_doc_link(self, messaging_platform_messages: dict, index: int = 0) -> str:
        """Iterate over a dict of all whatsapp, messenger and viber messages to find a valid document,
        if a document is found in any of the platforms, the url will be saved to the sheet
        This will take the first one found, can be extended to a list of urls
        """
        document_name = self._find_first_match(
            messaging_platform_messages, index, "doc"
        )
        document = Document.objects.filter(title=document_name).first()
        if document:
            return document.usage_url
        return ""

    def _get_media_link(
        self, messaging_platform_messages: dict, index: int = 0
    ) -> str:
        """Iterate over a dict of all whatsapp, messenger and viber messages to find a valid media,
        if a media is found in any of the platforms, the url will be saved to the sheet
        This will take the first one found, can be extended to a list of urls
        """
        media_name = self._find_first_match(messaging_platform_messages, index, "med")
        media = Media.objects.filter(title=media_name).first()
        if media:
            return media.usage_url
        return ""

    def _get_next_prompt(
        self, messaging_platform_messages: dict, index: int = 0
    ) -> str:
        """Iterate over a dict of all whatsapp, messenger and viber messages to find next prompts,
        if a next prompt is found in any of the platforms, the url will be saved to the sheet
        This will take the one found, can be extended to a list of urls
        """
        next_prompt = self._find_first_match(
            messaging_platform_messages, index, "next_prompt"
        )
        if next_prompt:
            return next_prompt
        return ""
