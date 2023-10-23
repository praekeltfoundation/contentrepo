import contextlib
import csv
import json
from collections import defaultdict
from dataclasses import dataclass, field, fields
from datetime import datetime
from io import BytesIO, StringIO
from queue import Queue
from typing import Any
from uuid import uuid4

from openpyxl import load_workbook
from taggit.models import Tag  # type: ignore
from treebeard.exceptions import NodeAlreadySaved  # type: ignore
from wagtail.blocks import StructValue  # type: ignore
from wagtail.coreutils import get_content_languages  # type: ignore
from wagtail.models import Locale, Page  # type: ignore
from wagtail.rich_text import RichText  # type: ignore

from home.models import (
    ContentPage,
    ContentPageIndex,
    ContentQuickReply,
    ContentTrigger,
    HomePage,
    MessengerBlock,
    ViberBlock,
    WhatsappBlock,
)


def language_code_from_display_name(display_name: str) -> str:
    codes = []
    for lang_code, lang_dn in get_content_languages().items():
        if lang_dn == display_name:
            codes.append(lang_code)
    if not codes:
        raise ValueError(f"Language not found: {display_name}")
    if len(codes) > 1:
        raise ValueError(f"Multiple codes for language: {display_name} -> {codes}")
    return codes[0]


class ContentImporter:
    def __init__(
        self,
        file_content: bytes,
        file_type: str,
        progress_queue: Queue[int],
        purge: bool | str = True,
        locale: Locale | str | None = None,
    ):
        if isinstance(locale, str):
            locale = Locale.objects.get(language_code=locale)
        self.file_content = file_content
        self.file_type = file_type
        self.progress_queue = progress_queue
        self.purge = purge in ["True", "yes", True]
        self.locale = locale
        self.shadow_pages: dict[str, ShadowContentPage] = {}
        self.go_to_page_buttons: dict[
            str, dict[int, list[dict[str, Any]]]
        ] = defaultdict(lambda: defaultdict(list))

    def perform_import(self) -> None:
        rows = self.parse_file()
        self.set_progress("Loaded file", 5)

        if self.purge:
            self.delete_existing_content()
        self.set_progress("Deleted existing content", 10)

        self.process_rows(rows)
        self.save_pages()
        self.link_related_pages()
        self.add_go_to_page_buttons()

    def process_rows(self, rows: list["ContentRow"]) -> None:
        for row in rows:
            if row.is_page_index:
                if self.locale and row.locale != self.locale.get_display_name():
                    # This page index isn't for the locale we're importing, so skip it.
                    continue
                self.create_content_page_index_from_row(row)
            elif row.is_content_page:
                self.create_shadow_content_page_from_row(row)
            elif row.is_variation_message:
                self.add_variation_to_shadow_content_page_from_row(row)
            else:
                self.add_message_to_shadow_content_page_from_row(row)

    def save_pages(self) -> None:
        for i, page in enumerate(self.shadow_pages.values()):
            if self.locale and page.locale != self.locale:
                # This page isn't for the locale we're importing, so skip it.
                continue
            if page.parent:
                # TODO: We should need to use something unique for `parent`
                parent = Page.objects.get(title=page.parent, locale=page.locale)
            else:
                parent = self.home_page(page.locale)
            page.save(parent)
            self.set_progress("Importing pages", 10 + 70 * i // len(self.shadow_pages))

    def link_related_pages(self) -> None:
        for i, page in enumerate(self.shadow_pages.values()):
            if page.related_pages:
                page.link_related_pages()
            self.set_progress(
                "Linking related pages", 80 + 10 * i // len(self.shadow_pages)
            )

    def add_go_to_page_buttons(self) -> None:
        for slug, messages in self.go_to_page_buttons.items():
            page = ContentPage.objects.get(slug=slug)
            for message_index, buttons in messages.items():
                for button in buttons:
                    title = button["title"]
                    related_page = ContentPage.objects.get(slug=button["slug"])
                    page.whatsapp_body[message_index].value["buttons"].append(
                        ("go_to_page", {"page": related_page, "title": title})
                    )
            page.save_revision().publish()

    def parse_file(self) -> list["ContentRow"]:
        if self.file_type == "XLSX":
            return self.parse_excel()
        return self.parse_csv()

    def parse_excel(self) -> list["ContentRow"]:
        workbook = load_workbook(BytesIO(self.file_content), read_only=True)
        worksheet = workbook.worksheets[0]

        def clean_excel_cell(cell_value: str | float | datetime | None) -> str:
            return str(cell_value).replace("_x000D", "")

        first_row = next(worksheet.iter_rows(max_row=1, values_only=True))
        header = [clean_excel_cell(cell) if cell else None for cell in first_row]
        rows: list[ContentRow] = []
        for row in worksheet.iter_rows(min_row=2, values_only=True):
            r = {}
            for name, cell in zip(header, row):  # noqa: B905 (TODO: strict?)
                if name and cell:
                    r[name] = clean_excel_cell(cell)
            rows.append(ContentRow.from_flat(r))
        return rows

    def parse_csv(self) -> list["ContentRow"]:
        reader = csv.DictReader(StringIO(self.file_content.decode()))
        return [ContentRow.from_flat(row) for row in reader]

    def set_progress(self, message: str, progress: int) -> None:
        self.progress_queue.put_nowait(progress)

    def delete_existing_content(self) -> None:
        ContentPage.objects.all().delete()
        ContentPageIndex.objects.all().delete()

    def home_page(self, locale: Locale) -> HomePage:
        return HomePage.objects.get(locale=locale)

    def create_content_page_index_from_row(self, row: "ContentRow") -> None:
        try:
            index = ContentPageIndex.objects.get(slug=row.slug)
        except ContentPageIndex.DoesNotExist:
            index = ContentPageIndex(slug=row.slug)
        index.title = row.web_title
        if row.translation_tag:
            index.translation_key = row.translation_tag
        language_code = language_code_from_display_name(row.locale)
        locale = Locale.objects.get(language_code=language_code)
        with contextlib.suppress(NodeAlreadySaved):
            self.home_page(locale).add_child(instance=index)

        index.save_revision().publish()

    def create_shadow_content_page_from_row(self, row: "ContentRow") -> None:
        language_code = language_code_from_display_name(row.locale)
        page = ShadowContentPage(
            slug=row.slug,
            title=row.web_title,
            locale=Locale.objects.get(language_code=language_code),
            subtitle=row.web_subtitle,
            body=row.web_body,
            enable_web=bool(row.web_body),
            tags=row.tags,
            quick_replies=row.quick_replies,
            triggers=row.triggers,
            parent=row.parent,
            related_pages=row.related_pages,
        )
        self.shadow_pages[row.slug] = page

        self.add_message_to_shadow_content_page_from_row(row)

        if row.is_whatsapp_message:
            page.whatsapp_title = row.whatsapp_title
            if row.is_whatsapp_template_message:
                page.is_whatsapp_template = True
                page.whatsapp_template_name = row.whatsapp_template_name
                page.whatsapp_template_category = row.whatsapp_template_category
            # TODO: Media
            # Currently media is exported as a URL, which just has an ID. This doesn't
            # actually help us much, as IDs can differ between instances, so we need
            # a better way of exporting and importing media here

        if row.is_messenger_message:
            page.messenger_title = row.messenger_title

        if row.is_viber_message:
            page.viber_title = row.viber_title

        if row.translation_tag:
            page.translation_key = row.translation_tag

    def add_variation_to_shadow_content_page_from_row(self, row: "ContentRow") -> None:
        page = self.shadow_pages[row.slug]
        whatsapp_block = page.whatsapp_body[-1]
        whatsapp_block.variation_messages.append(
            ShadowVariationBlock(
                message=row.variation_body, variation_restrictions=row.variation_title
            )
        )

    def add_message_to_shadow_content_page_from_row(self, row: "ContentRow") -> None:
        page = self.shadow_pages[row.slug]
        if row.is_whatsapp_message:
            page.enable_whatsapp = True
            buttons = []
            for button in row.buttons:
                if button["type"] == "next_message":
                    buttons.append(
                        {
                            "id": str(uuid4()),
                            "type": button["type"],
                            "value": {"title": button["title"]},
                        }
                    )
                elif button["type"] == "go_to_page":
                    self.go_to_page_buttons[row.slug][len(page.whatsapp_body)].append(
                        button
                    )
            page.whatsapp_body.append(
                ShadowWhatsappBlock(
                    message=row.whatsapp_body,
                    next_prompt=row.next_prompt,
                    example_values=row.example_values,
                    buttons=buttons,
                )
            )

        if row.is_messenger_message:
            page.enable_messenger = True
            page.messenger_body.append(ShadowMessengerBlock(message=row.messenger_body))

        if row.is_viber_message:
            page.enable_viber = True
            page.viber_body.append(ShadowViberBlock(message=row.viber_body))


# Since wagtail page models are so difficult to create and modify programatically,
# we instead store all the pages as these shadow objects, which we can then at the end
# do a single write to the database from, and encapsulate all that complexity
@dataclass(slots=True)
class ShadowContentPage:
    slug: str
    parent: str
    locale: Locale | None = None
    enable_web: bool = False
    title: str = ""
    subtitle: str = ""
    body: str = ""
    enable_whatsapp: bool = False
    is_whatsapp_template: bool = False
    whatsapp_title: str = ""
    whatsapp_body: list["ShadowWhatsappBlock"] = field(default_factory=list)
    whatsapp_template_name: str = ""
    whatsapp_template_category: str = "UTILITY"
    enable_messenger: bool = False
    messenger_title: str = ""
    messenger_body: list["ShadowMessengerBlock"] = field(default_factory=list)
    enable_viber: bool = False
    viber_title: str = ""
    viber_body: list["ShadowViberBlock"] = field(default_factory=list)
    translation_key: str = ""
    tags: list[str] = field(default_factory=list)
    quick_replies: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    related_pages: list[str] = field(default_factory=list)

    def save(self, parent: Page) -> None:
        try:
            page = ContentPage.objects.get(slug=self.slug)
        except ContentPage.DoesNotExist:
            page = ContentPage(slug=self.slug)

        self.add_web_to_page(page)
        self.add_whatsapp_to_page(page)
        self.add_messenger_to_page(page)
        self.add_viber_to_page(page)
        self.add_tags_to_page(page)
        self.add_quick_replies_to_page(page)
        self.add_triggers_to_page(page)

        with contextlib.suppress(NodeAlreadySaved):
            parent.add_child(instance=page)

        page.save_revision().publish()

    def add_web_to_page(self, page: ContentPage) -> None:
        page.enable_web = self.enable_web
        page.title = self.title
        page.subtitle = self.subtitle
        page.body = self.formatted_body
        page.translation_key = self.translation_key

    def add_whatsapp_to_page(self, page: ContentPage) -> None:
        page.enable_whatsapp = self.enable_whatsapp
        page.is_whatsapp_template = self.is_whatsapp_template
        page.whatsapp_title = self.whatsapp_title
        page.whatsapp_template_name = self.whatsapp_template_name
        page.whatsapp_template_category = self.whatsapp_template_category
        page.whatsapp_body.clear()
        for message in self.formatted_whatsapp_body:
            page.whatsapp_body.append(("Whatsapp_Message", message))

    def add_messenger_to_page(self, page: ContentPage) -> None:
        page.enable_messenger = self.enable_messenger
        page.messenger_title = self.messenger_title
        page.messenger_body.clear()
        for message in self.formatted_messenger_body:
            page.messenger_body.append(("messenger_block", message))

    def add_viber_to_page(self, page: ContentPage) -> None:
        page.enable_viber = self.enable_viber
        page.viber_title = self.viber_title
        page.viber_body.clear()
        for message in self.formatted_viber_body:
            page.viber_body.append(("viber_message", message))

    def add_tags_to_page(self, page: ContentPage) -> None:
        page.tags.clear()
        for tag_name in self.tags:
            tag, _ = Tag.objects.get_or_create(name=tag_name)
            page.tags.add(tag)

    def add_quick_replies_to_page(self, page: ContentPage) -> None:
        for quick_reply_name in self.quick_replies:
            quick_reply, _ = ContentQuickReply.objects.get_or_create(
                name=quick_reply_name
            )
            page.quick_replies.add(quick_reply)

    def add_triggers_to_page(self, page: ContentPage) -> None:
        for trigger_name in self.triggers:
            trigger, _ = ContentTrigger.objects.get_or_create(name=trigger_name)
            page.triggers.add(trigger)

    def link_related_pages(self) -> None:
        page = ContentPage.objects.get(slug=self.slug)
        related_pages = []
        for related_page_slug in self.related_pages:
            related_page = ContentPage.objects.get(slug=related_page_slug)
            related_pages.append(("related_page", related_page))
        page.related_pages = related_pages
        page.save_revision().publish()

    @property
    def formatted_body(self) -> list[tuple[str, RichText]]:
        if not self.body:
            return []
        formatted = []
        for line in self.body.splitlines():
            if line:
                formatted.append(("paragraph", RichText(line)))
        return formatted

    @property
    def formatted_whatsapp_body(self) -> list[StructValue]:
        return [WhatsappBlock().to_python(m.wagtail_format) for m in self.whatsapp_body]

    @property
    def formatted_messenger_body(self) -> list[StructValue]:
        return [
            MessengerBlock().to_python(m.wagtail_format) for m in self.messenger_body
        ]

    @property
    def formatted_viber_body(self) -> list[StructValue]:
        return [ViberBlock().to_python(m.wagtail_format) for m in self.viber_body]


@dataclass(slots=True)
class ShadowWhatsappBlock:
    message: str = ""
    next_prompt: str = ""
    buttons: list[dict[str, Any]] = field(default_factory=list)
    example_values: list[str] = field(default_factory=list)
    variation_messages: list["ShadowVariationBlock"] = field(default_factory=list)

    @property
    def wagtail_format(
        self,
    ) -> dict[str, str | list[dict[str, str | list[dict[str, str]]]]]:
        return {
            "message": self.message,
            "next_prompt": self.next_prompt,
            "example_values": self.example_values,
            "buttons": self.buttons,
            "variation_messages": [m.wagtail_format for m in self.variation_messages],
        }


@dataclass(slots=True)
class ShadowVariationBlock:
    message: str = ""
    variation_restrictions: dict[str, str] = field(default_factory=dict)

    @property
    def wagtail_format(self) -> dict[str, str | list[dict[str, str]]]:
        return {
            "message": self.message,
            "variation_restrictions": [
                {"type": t, "value": v} for t, v in self.variation_restrictions.items()
            ],
        }


@dataclass(slots=True)
class ShadowMessengerBlock:
    message: str = ""

    @property
    def wagtail_format(self) -> dict[str, str]:
        return {"message": self.message}


@dataclass(slots=True)
class ShadowViberBlock:
    message: str = ""

    @property
    def wagtail_format(self) -> dict[str, str]:
        return {"message": self.message}


@dataclass(slots=True, frozen=True)
class ContentRow:
    slug: str
    page_id: int | None = None
    parent: str = ""
    web_title: str = ""
    web_subtitle: str = ""
    web_body: str = ""
    whatsapp_title: str = ""
    whatsapp_body: str = ""
    whatsapp_template_name: str = ""
    whatsapp_template_category: str = ""
    example_values: list[str] = field(default_factory=list)
    variation_title: dict[str, str] = field(default_factory=dict)
    variation_body: str = ""
    messenger_title: str = ""
    messenger_body: str = ""
    viber_title: str = ""
    viber_body: str = ""
    translation_tag: str = ""
    tags: list[str] = field(default_factory=list)
    quick_replies: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    locale: str = ""
    next_prompt: str = ""
    buttons: list[dict[str, Any]] = field(default_factory=list)
    image_link: str = ""
    doc_link: str = ""
    media_link: str = ""
    related_pages: list[str] = field(default_factory=list)

    @classmethod
    def from_flat(cls, row: dict[str, str]) -> "ContentRow":
        class_fields = {field.name for field in fields(cls)}
        row = {
            key.strip(): value.strip()
            for key, value in row.items()
            if value and key in class_fields
        }
        return cls(
            page_id=int(row.pop("page_id")) if row.get("page_id") else None,
            variation_title=deserialise_dict(row.pop("variation_title", "")),
            tags=deserialise_list(row.pop("tags", "")),
            quick_replies=deserialise_list(row.pop("quick_replies", "")),
            triggers=deserialise_list(row.pop("triggers", "")),
            related_pages=deserialise_list(row.pop("related_pages", "")),
            example_values=json.loads(row.pop("example_values", ""))
            if row.get("example_values")
            else [],
            buttons=json.loads(row.pop("buttons", "")) if row.get("buttons") else [],
            **row,
        )

    @property
    def is_page_index(self) -> bool:
        return bool(self.web_title) and not any(
            [
                self.parent,
                self.web_body,
                self.whatsapp_body,
                self.messenger_body,
                self.viber_body,
            ]
        )

    @property
    def is_content_page(self) -> bool:
        return bool(self.web_title)

    @property
    def is_whatsapp_message(self) -> bool:
        return bool(self.whatsapp_body)

    @property
    def is_whatsapp_template_message(self) -> bool:
        return bool(self.whatsapp_template_name)

    @property
    def is_messenger_message(self) -> bool:
        return bool(self.messenger_body)

    @property
    def is_viber_message(self) -> bool:
        return bool(self.viber_body)

    @property
    def is_variation_message(self) -> bool:
        return bool(self.variation_body)


def deserialise_dict(value: str) -> dict[str, str]:
    if not value:
        return {}
    result = {}
    for item in value.strip().split(","):
        key, value = item.split(":")
        result[key.strip()] = value.strip()
    return result


def deserialise_list(value: str) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.strip().split(",")]
