import csv
from dataclasses import asdict, dataclass, fields
from itertools import zip_longest
from json import dumps

from django.http import HttpResponse  # type: ignore
from wagtail import blocks  # type: ignore
from wagtail.models import Locale, Page  # type: ignore
from wagtail.query import PageQuerySet  # type: ignore

from home.models import (
    ContentPage,
    ContentPageIndex,
    HomePage,
    MessengerBlock,
    VariationBlock,
    ViberBlock,
    WhatsappBlock,
)

HP_CTYPE = HomePage._meta.verbose_name
CP_CTYPE = ContentPage._meta.verbose_name
CPI_CTYPE = ContentPageIndex._meta.verbose_name


MsgBlocks = tuple[WhatsappBlock | None, MessengerBlock | None, ViberBlock | None]


@dataclass
class ExportRow:
    structure: str = ""
    message: int = 0
    page_id: int = 0
    slug: str = ""
    parent: str = ""
    web_title: str = ""
    web_subtitle: str = ""
    web_body: str = ""
    whatsapp_title: str = ""
    whatsapp_body: str = ""
    whatsapp_template_name: str = ""
    whatsapp_template_category: str = ""
    variation_title: str = ""
    variation_body: str = ""
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

    @classmethod
    def headings(cls) -> list[str]:
        return [f.name for f in fields(cls)]

    def to_dict(self) -> dict[str, str | int]:
        return asdict(self)

    def new_message_row(self, **fields: dict[str, str]) -> "ExportRow":
        return ExportRow(message=self.message + 1, page_id=self.page_id, slug=self.slug)

    def new_variation_row(self, variation: VariationBlock) -> "ExportRow":
        return ExportRow(
            message=self.message,
            page_id=self.page_id,
            slug=self.slug,
            variation_title=", ".join(
                f"{pf['type']}: {pf['value']}"
                for pf in variation.get("variation_restrictions").raw_data
            ),
            variation_body=variation.get("message"),
        )

    def add_message_fields(self, msg_blocks: MsgBlocks) -> None:
        whatsapp, messenger, viber = msg_blocks
        # We do these in reverse order to pick the same image as the old
        # exporter if there's more than one.
        if viber:
            self.viber_body = viber.value["message"].strip()
            if "image" in viber.value:
                self.image_link = viber.value["image"]
        if messenger:
            self.messenger_body = messenger.value["message"].strip()
            if "image" in messenger.value:
                self.image_link = messenger.value["image"]
        if whatsapp:
            self.whatsapp_body = whatsapp.value["message"].strip()
            if "image" in whatsapp.value:
                self.image_link = whatsapp.value["image"]
            if "document" in whatsapp.value:
                self.doc_link = whatsapp.value["document"]
            if "media" in whatsapp.value:
                self.media_link = whatsapp.value["media"]
            if "next_prompt" in whatsapp.value:
                self.next_prompt = whatsapp.value["next_prompt"]
            if "buttons" in whatsapp.value:
                self.buttons = self.serialise_buttons(whatsapp.value["buttons"])

    @staticmethod
    def serialise_buttons(buttons: blocks.StreamValue.StreamChild) -> str:
        button_dicts = []
        for button in buttons:
            button_dict = {"type": button.block_type, "title": button.value["title"]}
            if button.block_type == "go_to_page":
                button_dict["slug"] = button.value["page"].slug
            button_dicts.append(button_dict)
        return dumps(button_dicts)


class ContentExporter:
    rows: list[ExportRow]

    def __init__(self, queryset: PageQuerySet):
        self.rows = []
        self.queryset = queryset

    def perform_export(self) -> list[ExportRow]:
        for locale in Locale.objects.all():
            home = HomePage.objects.get(locale_id=locale.id)
            self._export_locale(home)
        return self.rows

    def _export_locale(self, home: HomePage) -> None:
        main_menu_pages = home.get_children()
        for index, page in enumerate(main_menu_pages, 1):
            structure_string = f"Menu {index}"
            self._export_page(page, structure_string)

    def _export_page(self, page: Page, structure: str) -> None:
        if page.content_type.name == CPI_CTYPE:
            self._export_cpi(ContentPageIndex.objects.get(id=page.id), structure)
        elif page.content_type.name == CP_CTYPE:
            content_page = self.queryset.filter(id=page.id).first()
            if content_page:
                self._export_content_page(content_page, structure)
        else:
            raise ValueError(f"Unexpected page type: {page.content_type.name}")
        # Now handle any child pages.
        if page.get_children_count() > 0:
            for index, child in enumerate(page.get_children(), 1):
                child_structure = f"{structure.replace('Menu', 'Sub')}.{index}"
                self._export_page(child, child_structure)

    def _export_content_page(self, page: ContentPage, structure: str) -> None:
        """
        Export a ContentPage.

        FIXME:
         * The locale should be a language code rather than a language name to
           make importing less messy.
         * We should use the parent slug (which is expected to be unique per
           locale (probably?)) instead of the parent title.
        """
        row = ExportRow(
            structure=structure,
            message=1,
            page_id=page.id,
            slug=page.slug,
            parent=self._parent_title(page),
            web_title=page.title,
            web_subtitle=page.subtitle,
            web_body=str(page.body),
            whatsapp_title=page.whatsapp_title,
            whatsapp_template_name=page.whatsapp_template_name,
            whatsapp_template_category=page.whatsapp_template_category,
            messenger_title=page.messenger_title,
            viber_title=page.viber_title,
            translation_tag=str(page.translation_key),
            tags=self._comma_sep_qs(page.tags.all()),
            quick_replies=self._comma_sep_qs(page.quick_replies.all()),
            triggers=self._comma_sep_qs(page.triggers.all()),
            locale=str(page.locale),
            related_pages=self._comma_sep_qs(self._related_pages(page)),
        )
        self.rows.append(row)
        message_bodies = list(
            zip_longest(page.whatsapp_body, page.messenger_body, page.viber_body)
        )
        for msg_blocks in message_bodies:
            self._export_row_message(row, msg_blocks)
            row = row.new_message_row()

    def _export_row_message(self, row: ExportRow, msg_blocks: MsgBlocks) -> None:
        row.add_message_fields(msg_blocks)
        if self.rows[-1] is not row:
            self.rows.append(row)
        # Only WhatsappBlock has variations at present.
        if msg_blocks[0] is None:
            return
        for variation in msg_blocks[0].value["variation_messages"]:
            self.rows.append(row.new_variation_row(variation))

    def _export_cpi(self, page: ContentPageIndex, structure: str) -> None:
        """
        Export a ContentPageIndex.

        FIXME:
         * The locale should be a language code rather than a language name to
           make importing less messy.
         * We use use the parent slug (which is expected to be unique per
           locale (probably?)) instead of the parent title.
        """
        row = ExportRow(
            structure=structure,
            page_id=page.id,
            slug=page.slug,
            parent=self._parent_title(page),
            web_title=page.title,
            translation_tag=str(page.translation_key),
            locale=str(page.locale),
        )
        self.rows.append(row)

    @staticmethod
    def _parent_title(page: Page) -> str:
        parent = page.get_parent()
        # If the parent is a HomePage, we treat the page as parentless.
        if parent.content_type.name == HP_CTYPE:
            return ""
        return parent.title

    @staticmethod
    def _related_pages(page: Page) -> list[str]:
        return [rp.value.slug for rp in page.related_pages]

    @staticmethod
    def _comma_sep_qs(unformatted_query: PageQuerySet) -> str:
        return ", ".join(str(x) for x in unformatted_query if str(x) != "")


@dataclass
class ExportWriter:
    rows: list[ExportRow]

    def write_csv(self, response: HttpResponse) -> None:
        writer = csv.DictWriter(response, ExportRow.headings())
        writer.writeheader()
        for row in self.rows:
            writer.writerow(row.to_dict())

    def write_xlsx(self, response: HttpResponse) -> None:
        raise NotImplementedError("TODO")
