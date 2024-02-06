import copy
import csv
import io
from dataclasses import dataclass
from io import BytesIO
from json import dumps
from logging import getLogger
from math import ceil
from typing import List, Tuple, Union

from django.db import transaction
from django.http import HttpResponse
from openpyxl import load_workbook
from openpyxl.styles import Border, Color, Font, NamedStyle, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet
from wagtail import blocks
from wagtail.documents.models import Document
from wagtail.images.models import Image
from wagtail.models import Locale
from wagtail.query import PageQuerySet
from wagtailmedia.models import Media

from home.models import (  # isort:skip
    ContentPage,
    ContentPageIndex,
    HomePage,
    OrderedContentSet,
)


EXPORT_FIELDNAMES = [
    "page_id",
    "slug",
    "parent",
    "web_title",
    "web_subtitle",
    "web_body",
    "whatsapp_title",
    "whatsapp_body",
    "whatsapp_template_name",
    "whatsapp_template_category",
    "example_values",
    "variation_title",
    "variation_body",
    "list_items",
    "sms_title",
    "sms_body",
    "ussd_title",
    "ussd_body",
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
    "buttons",
    "image_link",
    "doc_link",
    "media_link",
    "related_pages",
]

logger = getLogger(__name__)


@transaction.atomic
def import_content(file, filetype, progress_queue, purge=True, locale=None) -> None:
    from .import_content_pages import ContentImporter

    importer = ContentImporter(file.read(), filetype, progress_queue, purge, locale)
    importer.perform_import()


def export_xlsx_content(queryset: PageQuerySet, response: HttpResponse) -> None:
    from .export_content_pages import ContentExporter, ExportWriter

    exporter = ContentExporter(queryset)
    export_rows = exporter.perform_export()
    ExportWriter(export_rows).write_xlsx(response)


def export_csv_content(queryset: PageQuerySet, response: HttpResponse) -> None:
    from .export_content_pages import ContentExporter, ExportWriter

    exporter = ContentExporter(queryset)
    export_rows = exporter.perform_export()
    ExportWriter(export_rows).write_csv(response)


def style_sheet(wb: Workbook, sheet: Worksheet) -> Tuple[Workbook, Worksheet]:
    """Sets the style for the workbook adding any formatting that will make the sheet more aesthetically pleasing"""
    # Adjustment is because the size in openxlsx and google sheets are not equivalent
    adjustment = 7
    # Padding
    sheet.insert_cols(1)

    # Set columns based on best size

    column_widths_in_pts = {
        "structure": 110,
        "message": 70,
        "page_id": 110,
        "slug": 110,
        "parent": 110,
        "web_title": 110,
        "web_subtitle": 110,
        "web_body": 370,
        "whatsapp_title": 118,
        "whatsapp_body": 370,
        "whatsapp_template_name": 118,
        "whatsapp_template_category": 118,
        "example_values": 118,
        "variation_title": 118,
        "variation_body": 370,
        "list_items": 118,
        "sms_title": 118,
        "sms_body": 370,
        "ussd_title": 118,
        "ussd_body": 370,
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
        "buttons": 118,
        "image_link": 118,
        "doc_link": 118,
        "media_link": 118,
        "related": 118,
    }

    for index, column_width in enumerate(column_widths_in_pts.values(), 2):
        sheet.column_dimensions[get_column_letter(index)].width = ceil(
            column_width / adjustment
        )

    # Freeze heading row and side panel, 1 added because it freezes before the column
    panel_column = get_column_letter(5)
    sheet.freeze_panes = sheet[f"{panel_column}2"]

    # Colours
    blue = Color(rgb="0099CCFF")

    # Boarders
    left_border = Border(left=Side(border_style="thin", color="FF000000"))

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
    for cell in sheet[f"{panel_column}:{panel_column}"]:
        cell.border = left_border

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


def get_rows(
    page: Union[ContentPage, ContentPageIndex],
    structure_string: str,
) -> List[list]:
    """Sets up row for each page including the side panel.
    Each page is returned as a list of rows, this accounts for pages with multiple messages
    """
    rows = []
    base_row = ContentSheetRow.from_page(page=page, structure_string=structure_string)
    if base_row:
        rows.append(base_row.get_row())
        if base_row.variation_messages_rows:
            for variation_row in base_row.variation_messages_rows:
                rows.append(variation_row.get_row())
        if base_row.tuple_of_extra_rows:
            for extra_row in base_row.tuple_of_extra_rows:
                rows.append(extra_row.get_row())
                if extra_row.variation_messages_rows:
                    for variation_row in extra_row.variation_messages_rows:
                        rows.append(variation_row.get_row())
    return rows


def add_children(
    temp_sheet: List[list],
    children: PageQuerySet,
    queryset: PageQuerySet,
    parent_structure: str,
) -> List[list]:
    """Recursive function that traverses the children of a page with a depth first search algorithm"""
    for index, child in enumerate(children, 1):
        content_page = get_page(child, queryset)
        structure_string = f"{parent_structure.replace('Menu','Sub')}.{index}"
        row = get_rows(content_page, structure_string)
        if row:
            temp_sheet.extend(row)
        if content_page and content_page.has_children:
            add_children(
                temp_sheet,
                content_page.get_children(),
                queryset,
                structure_string,
            )
    return temp_sheet


def get_page(page: Union[ContentPage, ContentPageIndex], queryset: PageQuerySet = None):
    if page.content_type.name == "content page index":
        return ContentPageIndex.objects.filter(id=page.id).first()
    elif page.content_type.name == "content page" and queryset:
        return queryset.filter(id=page.id).first()
    else:
        return ContentPage.objects.filter(id=page.id).first()


def get_content_sheet(queryset: PageQuerySet) -> List[list]:
    content_sheet = []
    headings = ["structure", "message"] + EXPORT_FIELDNAMES
    content_sheet.append(headings)
    for locale in Locale.objects.all():
        home = HomePage.objects.filter(locale_id=locale.id).first()
        if home:
            main_menu_pages = home.get_children()
            for index, page in enumerate(main_menu_pages, 1):
                structure_string = f"Menu {index}"
                content_page = get_page(page, queryset)
                if content_page:
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


def import_ordered_sets(file, filetype, progress_queue, purge=False):
    def create_ordered_set_from_row(row):
        set_name = row["Name"]

        ordered_set = OrderedContentSet.objects.filter(name=set_name).first()
        if not ordered_set:
            ordered_set = OrderedContentSet(name=set_name)

        ordered_set.profile_fields = []
        for field in [f.strip() for f in row["Profile Fields"].split(",")]:
            if not field or field == "-":
                continue
            [field_name, field_value] = field.split(":")
            ordered_set.profile_fields.append((field_name, field_value))

        ordered_set.pages = []
        for page_slug in [p.strip() for p in row["Page Slugs"].split(",")]:
            if not page_slug or page_slug == "-":
                continue
            page = ContentPage.objects.filter(slug=page_slug).first()
            if page:
                ordered_set.pages.append(("pages", {"contentpage": page}))
            else:
                logger.warning(f"Content page not found for slug '{page_slug}'")

        ordered_set.save()
        return ordered_set

    file = file.read()
    lines = []
    if filetype == "XLSX":
        wb = load_workbook(filename=BytesIO(file))
        ws = wb.worksheets[0]
        ws.delete_rows(1)
        for row in ws.iter_rows(values_only=True):
            row_dict = {"Name": row[0], "Profile Fields": row[1], "Page Slugs": row[2]}
            lines.append(row_dict)
    else:
        if isinstance(file, bytes):
            try:
                file = file.decode("utf-8")
            except UnicodeDecodeError:
                file = file.decode("latin-1")

        reader = csv.DictReader(io.StringIO(file))
        for dictionary in reader:
            lines.append(dictionary)

    # 10% progress for loading file
    progress_queue.put_nowait(10)

    for index, row in enumerate(lines):
        os = create_ordered_set_from_row(row)
        if not os:
            print(f"Ordered Content Set not created for row {index + 1}")
        # 10-100% for loading ordered content sets
        progress_queue.put_nowait(10 + index * 90 / len(lines))


@dataclass
class Message:
    body: str = ""
    image_name: str = None
    media_name: str = None
    document_name: str = None
    next_prompt: str = None
    example_values: str = None
    buttons: str = None
    list_items: str = None

    @classmethod
    def from_platform_body_element(
        cls, platform_body_element: blocks.StreamValue.StreamChild
    ):
        message = cls()
        message.body = (
            platform_body_element.value["message"].strip()
            if "message" in platform_body_element.value
            else None
        )
        message.image_name = (
            platform_body_element.value["image"]
            if "image" in platform_body_element.value
            else None
        )
        message.document_name = (
            platform_body_element.value["document"]
            if "document" in platform_body_element.value
            else None
        )
        message.media_name = (
            platform_body_element.value["media"]
            if "media" in platform_body_element.value
            else None
        )
        message.next_prompt = (
            platform_body_element.value["next_prompt"]
            if "next_prompt" in platform_body_element.value
            else None
        )
        message.buttons = (
            cls.serialise_buttons(platform_body_element.value["buttons"])
            if "buttons" in platform_body_element.value
            else ""
        )
        message.example_values = (
            cls.serialise_example_values(platform_body_element.value["example_values"])
            if "example_values" in platform_body_element.value
            else ""
        )
        message.list_items = (
            cls.serialise_list_items(platform_body_element.value["list_items"])
            if "list_items" in platform_body_element.value
            else ""
        )
        return message

    @classmethod
    def serialise_buttons(cls, buttons: blocks.StreamValue.StreamChild) -> str:
        result = []
        for button in buttons:
            if button.block_type == "next_message":
                result.append(cls.serialise_next_message_button(button))
            elif button.block_type == "go_to_page":
                result.append(cls.serialise_go_to_page_button(button))
        return dumps(result)

    @classmethod
    def serialise_example_values(
        cls, example_values: blocks.StreamValue.StreamChild
    ) -> str:
        return ", ".join(example_values)

    @classmethod
    def serialise_next_message_button(
        cls, button: blocks.StreamValue.StreamChild
    ) -> dict:
        return {"type": button.block_type, "title": button.value["title"]}

    @classmethod
    def serialise_go_to_page_button(
        cls, button: blocks.StreamValue.StreamChild
    ) -> dict:
        return {
            "type": button.block_type,
            "title": button.value["title"],
            "slug": button.value["page"].slug,
        }

    @classmethod
    def serialise_list_items(cls, list_items: blocks.StreamValue.StreamChild) -> str:
        return ", ".join(list_items)


@dataclass
class VariationMessage:
    body: str = ""
    title: str = ""

    @classmethod
    def from_variation(cls, variation: blocks.StreamValue.StreamChild):
        message = cls()
        message.body = variation.get("message")
        profile_fields = []
        for profile_field in variation.get("variation_restrictions").raw_data:
            profile_fields.append(f"{profile_field['type']}: {profile_field['value']}")
        message.title = ", ".join(profile_fields)
        return message


@dataclass
class VariationMessageList:
    variations: List[VariationMessage]

    @classmethod
    def from_platform_body_element(cls, whatsapp_msg: blocks.StreamValue.StreamChild):
        variations = []
        for variation in whatsapp_msg.value["variation_messages"]:
            variations.append(VariationMessage.from_variation(variation=variation))
        return cls(variations)


@dataclass
class MessageContainer:
    whatsapp: Tuple[Message]
    sms: Tuple[Message]
    ussd: Tuple[Message]
    messenger: Tuple[Message]
    viber: Tuple[Message]
    variation_messages: Tuple[VariationMessage]

    @classmethod
    def from_platform_body(
        cls, whatsapp_body, sms_body, ussd_body, messenger_body, viber_body
    ):
        whatsapp = []
        whatsapp_variation_messages = []
        sms = []
        ussd = []
        messenger = []
        viber = []
        for whatsapp_msg in whatsapp_body:
            whatsapp.append(Message.from_platform_body_element(whatsapp_msg))
            whatsapp_variation_messages.append(
                VariationMessageList.from_platform_body_element(whatsapp_msg)
            )
        for sms_msg in sms_body:
            sms.append(Message.from_platform_body_element(sms_msg))

        for ussd_msg in ussd_body:
            ussd.append(Message.from_platform_body_element(ussd_msg))

        for messenger_msg in messenger_body:
            messenger.append(Message.from_platform_body_element(messenger_msg))

        for viber_msg in viber_body:
            viber.append(Message.from_platform_body_element(viber_msg))
        return cls(whatsapp, messenger, viber, whatsapp_variation_messages)

    def find_first_attachment(self, index: int, attachment_type: str) -> str:
        for message_list in [self.whatsapp, self.messenger, self.viber]:
            try:
                value = getattr(message_list[index], attachment_type)
                if value:
                    return value
            except IndexError:
                continue
        return ""

    @staticmethod
    def message_from_platform_body_element(
        platform_body_element: blocks.StreamValue.StreamChild,
    ):
        message = {}
        message["message"] = (
            platform_body_element.value["message"].strip()
            if "message" in platform_body_element.value
            else None
        )
        message["image_name"] = (
            platform_body_element.value["image_name"].strip()
            if "image_name" in platform_body_element.value
            else None
        )
        message["document_name"] = (
            platform_body_element.value["document_name"].strip()
            if "document_name" in platform_body_element.value
            else None
        )
        message["media_name"] = (
            platform_body_element.value["media_name"].strip()
            if "media_name" in platform_body_element.value
            else None
        )
        message["next_prompt"] = (
            platform_body_element.value["next_prompt"].strip()
            if "next_prompt" in platform_body_element.value
            else None
        )
        message["buttons"] = (
            platform_body_element.value["buttons"]
            if "buttons" in platform_body_element.value
            else None
        )

        return message


@dataclass
class ContentSheetRow:
    structure: str = ""
    side_panel_message_number: int = 0
    parent: str = ""
    slug: str = ""
    web_title: str = ""
    web_subtitle: str = ""
    web_body: str = ""
    whatsapp_title: str = ""
    whatsapp_body: str = ""
    whatsapp_template_name: str = ""
    whatsapp_template_category: str = ""
    list_items: str = ""
    sms_title: str = ""
    sms_body: str = ""
    ussd_title: str = ""
    ussd_body: str = ""
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
    buttons: str = ""
    image_link: str = ""
    doc_link: str = ""
    media_link: str = ""
    related_pages: str = ""
    example_values: str = ""
    variation_body: str = ""
    variation_title: str = ""
    tuple_of_extra_rows: tuple = ()
    variation_messages_rows: tuple = ()
    page_id: int = 0

    @classmethod
    def from_page(
        cls,
        page: ContentPage,
        structure_string: str,
        side_panel_message_number: int = 0,
    ):
        if isinstance(page, ContentPage):
            return cls.from_content_page(
                page, structure_string, side_panel_message_number
            )
        if isinstance(page, ContentPageIndex):
            return cls.from_index_page(page, structure_string)

    @classmethod
    def from_content_page(
        cls,
        page: ContentPage,
        structure_string: str,
        side_panel_message_number: int = 0,
    ):
        content_sheet_row = cls()
        message_container = MessageContainer.from_platform_body(
            page.whatsapp_body,
            page.sms_body,
            page.ussd_body,
            page.messenger_body,
            page.viber_body,
        )
        content_sheet_row._set_messages(
            page, side_panel_message_number, message_container
        )

        content_sheet_row.structure = structure_string
        content_sheet_row.page_id = page.id
        content_sheet_row.slug = page.slug

        if side_panel_message_number == 0:
            content_sheet_row.parent = content_sheet_row._get_parent_page(page)
            content_sheet_row.web_title = page.title
            content_sheet_row.web_subtitle = page.subtitle
            content_sheet_row.web_body = str(page.body)
            content_sheet_row.whatsapp_template_name = page.whatsapp_template_name
            content_sheet_row.whatsapp_template_category = (
                page.whatsapp_template_category
            )
            content_sheet_row.whatsapp_title = page.whatsapp_title
            content_sheet_row.sms_title = page.sms_title
            content_sheet_row.ussd_title = page.ussd_title
            content_sheet_row.messenger_title = page.messenger_title
            content_sheet_row.viber_title = page.viber_title
            content_sheet_row.translation_tag = str(page.translation_key)
            content_sheet_row.tags = content_sheet_row._format_list_from_query_set(
                page.tags.all()
            )
            content_sheet_row.quick_replies = (
                content_sheet_row._format_list_from_query_set(page.quick_replies.all())
            )
            content_sheet_row.triggers = content_sheet_row._format_list_from_query_set(
                page.triggers.all()
            )
            content_sheet_row.locale = str(page.locale)
            content_sheet_row.related_pages = (
                content_sheet_row._format_list_from_query_set(
                    content_sheet_row._get_related_pages(page)
                )
            )
        return content_sheet_row

    @classmethod
    def from_index_page(
        cls,
        page: ContentPageIndex,
        structure_string: str,
    ):
        content_sheet_row = cls()
        content_sheet_row.page_id = page.id
        content_sheet_row.slug = page.slug
        content_sheet_row.structure = structure_string
        content_sheet_row.parent = content_sheet_row._get_parent_page(page)
        content_sheet_row.web_title = page.title
        content_sheet_row.translation_tag = str(page.translation_key)
        content_sheet_row.locale = str(page.locale)
        return content_sheet_row

    @classmethod
    def from_variation_message(
        cls,
        page,
        variation_title,
        side_panel_message_number,
        variation_body,
    ):
        content_sheet_row = cls()
        content_sheet_row.page_id = page.id
        content_sheet_row.slug = page.slug
        content_sheet_row.side_panel_message_number = side_panel_message_number + 1
        content_sheet_row.variation_title = variation_title
        content_sheet_row.variation_body = variation_body
        return content_sheet_row

    def get_row(self):
        """Returns object as an exportable row"""
        return [
            self.structure,
            self.side_panel_message_number,
            self.page_id,
            self.slug,
            self.parent,
            self.web_title,
            self.web_subtitle,
            self.web_body,
            self.whatsapp_title,
            self.whatsapp_body,
            self.whatsapp_template_name,
            self.whatsapp_template_category,
            self.example_values,
            self.variation_title,
            self.variation_body,
            self.list_items,
            self.sms_title,
            self.sms_body,
            self.ussd_title,
            self.ussd_body,
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
            self.buttons,
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

    def _set_messages(
        self,
        page: ContentPage,
        side_panel_message_number: int,
        message_container: MessageContainer,
    ):
        """Sets all message level content, including any message level content such as documents, images, next prompts and media.
        Takes the possibility of different numbers of messages on different platforms.
        Adds multiple messages as blank rows with only the extra messages and the message number to the row to match the template
        """
        self.side_panel_message_number = side_panel_message_number + 1
        most_messages = max(
            [
                len(message_container.whatsapp),
                len(message_container.sms),
                len(message_container.ussd),
                len(message_container.messenger),
                len(message_container.viber),
                len(page.body),
            ]
        )
        variation_messages = []

        if len(message_container.whatsapp) == 1 or (
            side_panel_message_number == 0 and len(message_container.whatsapp) > 1
        ):
            self.whatsapp_body = message_container.whatsapp[0].body
            if message_container.variation_messages:
                variation_messages.extend(
                    self._make_variation_rows(page, message_container, 0)
                )
        if len(message_container.sms) == 1 or (
            side_panel_message_number == 0 and len(message_container.sms) > 1
        ):
            self.sms_body = message_container.sms[0].body

        if len(message_container.ussd) == 1 or (
            side_panel_message_number == 0 and len(message_container.ussd) > 1
        ):
            self.ussd_body = message_container.ussd[0].body

        if len(message_container.messenger) == 1 or (
            side_panel_message_number == 0 and len(message_container.messenger) > 1
        ):
            self.messenger_body = message_container.messenger[0].body

        if len(message_container.viber) == 1 or (
            side_panel_message_number == 0 and len(message_container.viber) > 1
        ):
            self.viber_body = message_container.viber[0].body

        self.next_prompt = self._get_next_prompt(message_container)
        self.example_values = self._get_example_values(message_container)
        self.buttons = self._get_buttons(message_container)
        self.doc_link = self._get_doc_link(message_container)
        self.image_link = self._get_image_link(message_container)
        self.media_link = self._get_media_link(message_container)
        self.list_items = self._get_list_items(message_container)

        temp_rows = []
        if side_panel_message_number == 0 and most_messages > 1:
            # Set tuple_of_extra_rows rows to account for multiple messages
            for message_index in range(1, most_messages):
                new_content_sheet_row = ContentSheetRow.from_page(
                    page=page,
                    structure_string="",
                    side_panel_message_number=message_index,
                )
                if message_index < len(message_container.whatsapp):
                    new_content_sheet_row.whatsapp_body = message_container.whatsapp[
                        message_index
                    ].body
                    if message_container.variation_messages:
                        new_content_sheet_row.variation_messages_rows = (
                            self._make_variation_rows(
                                page, message_container, message_index
                            )
                        )

                if message_index < len(message_container.messenger):
                    new_content_sheet_row.messenger_body = message_container.messenger[
                        message_index
                    ].body
                if message_index < len(message_container.sms):
                    new_content_sheet_row.sms_body = message_container.sms[
                        message_index
                    ].body
                if message_index < len(message_container.ussd):
                    new_content_sheet_row.ussd_body = message_container.ussd[
                        message_index
                    ].body
                if message_index < len(message_container.viber):
                    new_content_sheet_row.viber_body = message_container.viber[
                        message_index
                    ].body
                new_content_sheet_row.next_prompt = self._get_next_prompt(
                    message_container, message_index
                )
                new_content_sheet_row.buttons = self._get_buttons(
                    message_container, message_index
                )
                new_content_sheet_row.doc_link = self._get_doc_link(
                    message_container, message_index
                )
                new_content_sheet_row.image_link = self._get_image_link(
                    message_container, message_index
                )
                new_content_sheet_row.media_link = self._get_media_link(
                    message_container, message_index
                )
                temp_rows.append(new_content_sheet_row)
            self.tuple_of_extra_rows = tuple(temp_rows)
            self.variation_messages_rows = tuple(variation_messages)

    def _make_variation_rows(self, page, message_container, message_index):
        temp_rows = []
        for variation in message_container.variation_messages[message_index].variations:
            temp_rows.append(
                ContentSheetRow.from_variation_message(
                    page=page,
                    variation_title=variation.title,
                    side_panel_message_number=message_index,
                    variation_body=variation.body,
                )
            )
        return temp_rows

    @staticmethod
    def _get_related_pages(page: ContentPage) -> List[str]:
        """Returns a list of strings of the related page slugs"""
        related_pages = []
        for related_page in page.related_pages:
            related_pages.append(related_page.value.slug)
        return related_pages

    def _get_image_link(
        self, message_container: MessageContainer, index: int = 0
    ) -> str:
        """Iterate over a dict of whatsapp, messenger and viber messages to find a valid image for that message level,
        if an image is found in any of the platforms, the url will be saved to the sheet.
        This will take the first one found, can be extended to a list of urls
        """
        image_name = message_container.find_first_attachment(index, "image_name")
        image = Image.objects.filter(title=image_name).first()
        if image:
            return image.usage_url
        return ""

    def _get_doc_link(self, message_container: MessageContainer, index: int = 0) -> str:
        """Iterate over a dict of all whatsapp, messenger and viber messages to find a valid document,
        if a document is found in any of the platforms, the url will be saved to the sheet
        This will take the first one found, can be extended to a list of urls
        """
        document_name = message_container.find_first_attachment(index, "document_name")
        document = Document.objects.filter(title=document_name).first()
        if document:
            return document.usage_url
        return ""

    def _get_media_link(
        self, message_container: MessageContainer, index: int = 0
    ) -> str:
        """Iterate over a dict of all whatsapp, messenger and viber messages to find a valid media,
        if a media is found in any of the platforms, the url will be saved to the sheet
        This will take the first one found, can be extended to a list of urls
        """
        media_name = message_container.find_first_attachment(index, "media_name")
        media = Media.objects.filter(title=media_name).first()
        if media:
            return media.usage_url
        return ""

    def _get_next_prompt(
        self, message_container: MessageContainer, index: int = 0
    ) -> str:
        """Iterate over a dict of all whatsapp, messenger and viber messages to find next prompts,
        if a next prompt is found in any of the platforms, the url will be saved to the sheet
        This will take the one found, can be extended to a list of urls
        """
        next_prompt = message_container.find_first_attachment(index, "next_prompt")
        if next_prompt:
            return next_prompt
        return ""

    def _get_buttons(self, message_container: MessageContainer, index: int = 0) -> str:
        """Iterate over a dict of all whatsapp, messenger and viber messages to find buttons,
        if buttons are found in any of the platforms, the buttons will be saved to the sheet
        """
        buttons = message_container.find_first_attachment(index, "buttons")
        if buttons:
            return buttons
        return ""

    def _get_example_values(
        self, message_container: MessageContainer, index: int = 0
    ) -> str:
        """Iterate over a dict of all whatsapp, messenger and viber messages to find example_values,
        if example_values are found in any of the platforms, the values will be saved to the sheet
        """
        example_values = message_container.find_first_attachment(
            index, "example_values"
        )
        if example_values:
            return example_values
        return ""

    def _get_list_items(
        self, message_container: MessageContainer, index: int = 0
    ) -> str:
        """Iterate over a dict of all whatsapp, messenger and viber messages to find list_items,
        if list_items are found in any of the platforms, the values will be saved to the sheet
        """
        list_items = message_container.find_first_attachment(index, "list_items")
        if list_items:
            return list_items
        return ""
