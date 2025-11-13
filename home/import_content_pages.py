import contextlib
import csv
from collections import defaultdict
from dataclasses import dataclass, field, fields
from queue import Queue
from typing import Any, Union
from uuid import uuid4

from django.core.exceptions import ObjectDoesNotExist, ValidationError  # type: ignore
from taggit.models import Tag  # type: ignore
from treebeard.exceptions import NodeAlreadySaved  # type: ignore
from wagtail.blocks import StructValue  # type: ignore
from wagtail.coreutils import get_content_languages  # type: ignore
from wagtail.models import Locale, Page  # type: ignore
from wagtail.models.sites import Site  # type: ignore
from wagtail.rich_text import RichText  # type: ignore

from home.import_helpers import (
    ImportException,
    ImportWarning,
    JSON_loader,
    parse_file,
    validate_using_form,
)

from .models import (
    Assessment,
    ContentPage,
    ContentPageIndex,
    ContentQuickReply,
    ContentTrigger,
    HomePage,
    MessengerBlock,
    SMSBlock,
    USSDBlock,
    ViberBlock,
    WhatsappBlock,
    WhatsAppTemplate,
)

PageId = tuple[str, Locale]


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
        self.locale_map: dict[str, Locale] = {}
        self.shadow_pages: dict[PageId, ShadowContentPage] = {}
        self.go_to_page_buttons: dict[PageId, dict[int, list[dict[str, Any]]]] = (
            defaultdict(lambda: defaultdict(list))
        )
        self.go_to_page_list_items: dict[PageId, dict[int, list[dict[str, Any]]]] = (
            defaultdict(lambda: defaultdict(list))
        )
        self.import_warnings: list[ImportWarning] = []

    def locale_from_display_name(self, langname: str) -> Locale:
        if langname not in self.locale_map:
            codes = []
            for lang_code, lang_dn in get_content_languages().items():
                if lang_dn == langname:
                    codes.append(lang_code)
            if not codes:
                raise ImportException(f"Language not found: {langname}")
            if len(codes) > 1:
                raise ImportException(
                    f"Multiple codes for language: {langname} -> {codes}"
                )
            self.locale_map[langname] = Locale.objects.get(language_code=codes[0])
        return self.locale_map[langname]

    def perform_import(self) -> None:
        rows = self.parse_file()
        self.set_progress("Loaded file", 5)

        if self.purge:
            self.delete_existing_content()
        self.set_progress("Deleted existing content", 10)

        self.process_rows(rows)
        self.save_pages()
        self.link_related_pages()

        self.add_go_to_page_items(self.go_to_page_buttons, "buttons")

        self.add_go_to_page_items(self.go_to_page_list_items, "list_items")

        self.add_media_link(rows)

    def add_media_link(self, rows: list["ContentRow"]) -> None:
        for row_num, row in enumerate(rows, start=2):
            if row.media_link:
                if row.media_link is not None or row.media_link != "":
                    self.import_warnings.append(
                        ImportWarning(
                            f"Media import not supported, {row.media_link} not added to {row.slug}",
                            row_num,
                        )
                    )

    def process_rows(self, rows: list["ContentRow"]) -> None:
        # Non-page rows don't have a locale, so we need to remember the last
        # row that does have a locale.

        prev_locale: Locale | None = None
        for i, row in enumerate(rows, start=2):
            try:
                if row.is_page_index:
                    prev_locale = self._get_locale_from_row(row)
                    if self.locale and self.locale != prev_locale:
                        # This page index isn't for the locale we're importing, so skip it.
                        continue
                    self.create_content_page_index_from_row(row)

                elif row.is_content_page:
                    self.create_shadow_content_page_from_row(row, i)
                    prev_locale = self._get_locale_from_row(row)
                elif row.is_variation_message:
                    self.add_variation_to_shadow_content_page_from_row(row, prev_locale)
                else:
                    self.add_message_to_shadow_content_page_from_row(row, prev_locale)

            except ImportException as e:
                e.row_num = i
                e.slug = row.slug
                e.locale = row.locale
                raise e

    def _get_locale_from_row(self, row: "ContentRow") -> Locale:
        if row.language_code:
            try:
                return Locale.objects.get(language_code=row.language_code)
            except Locale.DoesNotExist:
                raise ImportException(f"Language not found: {row.language_code}")
        else:
            return self.locale_from_display_name(row.locale)

    def save_pages(self) -> None:
        for i, page in enumerate(self.shadow_pages.values()):
            if self.locale and page.locale != self.locale:
                # This page isn't for the locale we're importing, so skip it.
                continue
            if page.parent:
                # TODO: We should need to use something unique for `parent`
                try:
                    parent = Page.objects.get(title=page.parent, locale=page.locale)

                except Page.DoesNotExist:
                    raise ImportException(
                        f"Cannot find parent page with title '{page.parent}' and "
                        f"locale '{page.locale}'",
                        page.row_num,
                    )
                except Page.MultipleObjectsReturned:
                    parents = Page.objects.filter(
                        title=page.parent, locale=page.locale
                    ).values("slug")

                    # Check which parents are in import vs database only
                    import_slugs = {slug for slug, loc in self.shadow_pages.keys() if loc == page.locale}

                    parent_slugs = [p["slug"] for p in parents]
                    in_import = [s for s in parent_slugs if s in import_slugs]
                    in_db = [s for s in parent_slugs if s not in import_slugs]

                    lines = [
                        f"Cannot determine parent for page '{page.slug}'. "
                        f"Multiple pages found with title '{page.parent}' and locale '{page.locale}':"
                    ]
                    if in_import:
                        lines.append(f"  - Import: {in_import}")
                    if in_db:
                        lines.append(f"  - Database: {in_db}")
                    lines.append("")
                    lines.append(
                        "Parent pages must have unique title+locale+slug combinations across Database and Import."
                    )
                    lines.append("")
                    lines.append('See <a href="/kb/1/" target="_blank">KB1</a> for detailed resolution steps.')

                    raise ImportException("\n".join(lines), page.row_num)

                try:
                    child = Page.objects.get(slug=page.slug, locale=page.locale)

                except Page.DoesNotExist:
                    # Nothing to check if the child doesn't exist yet.
                    pass
                else:
                    if child.get_parent().title != page.parent:
                        raise ImportException(
                            f"Changing the parent from '{child.get_parent()}' to '{page.parent}' "
                            f"for the page with title '{page.title}' during import is not allowed. Please use the UI",
                            page.row_num,
                        )

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

    def add_go_to_page_items(
        self, items_dict: dict[PageId, dict[int, list[dict[str, Any]]]], item_type: str
    ) -> None:
        for (slug, locale), messages in items_dict.items():
            try:
                page = ContentPage.objects.get(slug=slug, locale=locale)
            except ContentPage.DoesNotExist:
                raise ImportException(
                    f"No content pages found with slug '{slug}' and locale '{locale}' for go_to_page {item_type[:-1]} on page '{slug}'"
                )
            for message_index, items in messages.items():
                for item in items:
                    title = item["title"]
                    try:
                        related_page = Page.objects.get(
                            slug=item["slug"], locale=locale
                        )
                    except Page.DoesNotExist:
                        row = self.shadow_pages[(slug, locale)]
                        raise ImportException(
                            f"No pages found with slug '{item['slug']}' and locale "
                            f"'{locale}' for go_to_page {item_type[:-1]} '{item['title']}' on "
                            f"page '{slug}'",
                            row.row_num,
                        )
                    page.whatsapp_body[message_index].value[item_type].insert(
                        item["index"],
                        ("go_to_page", {"page": related_page, "title": title}),
                    )
            page.save()

    def parse_file(self) -> list["ContentRow"]:
        return [
            ContentRow.from_flat(row, i)
            for i, row in parse_file(self.file_content, self.file_type)
        ]

    def set_progress(self, message: str, progress: int) -> None:
        self.progress_queue.put_nowait(progress)

    def delete_existing_content(self) -> None:
        ContentPage.objects.all().delete()
        ContentPageIndex.objects.all().delete()

    def home_page(self, locale: Locale) -> HomePage:
        try:
            return HomePage.objects.get(locale=locale)
        except ObjectDoesNotExist:
            raise ImportException(
                f"You are trying to add a child page to a '{locale}' HomePage that does not exist. Please create the '{locale}' HomePage first"
            )

    def default_locale(self) -> Locale:
        site = Site.objects.get(is_default_site=True)
        return site.root_page.locale

    def create_content_page_index_from_row(self, row: "ContentRow") -> None:
        locale = self._get_locale_from_row(row)
        try:
            index = ContentPageIndex.objects.get(slug=row.slug, locale=locale)
        except ContentPageIndex.DoesNotExist:
            index = ContentPageIndex(slug=row.slug, locale=locale)
        index.title = row.web_title
        # Translation keys are required for pages with a non-default locale,
        # but optional for the default locale.
        if row.translation_tag or locale != self.default_locale():
            index.translation_key = row.translation_tag
        try:
            with contextlib.suppress(NodeAlreadySaved):
                self.home_page(locale).add_child(instance=index)
            index.save_revision().publish()
        except ValidationError as errors:
            err = []
            for error in errors:
                field_name = error[0]
                for msg in error[1]:
                    err.append(f"{field_name} - {msg}")
            raise ImportException([f"Validation error: {msg}" for msg in err])

    def create_shadow_content_page_from_row(
        self, row: "ContentRow", row_num: int
    ) -> None:
        locale = self._get_locale_from_row(row)
        page = ShadowContentPage(
            row_num=row_num,
            slug=row.slug,
            title=row.web_title,
            locale=locale,
            subtitle=row.web_subtitle,
            body=row.web_body,
            enable_web=bool(row.web_body),
            tags=row.tags,
            quick_replies=row.quick_replies,
            triggers=row.triggers,
            parent=row.parent,
            related_pages=row.related_pages,
        )
        self.shadow_pages[(row.slug, locale)] = page

        if row.is_whatsapp_message:
            page.whatsapp_title = row.whatsapp_title

        if row.is_whatsapp_template_message:
            try:
                wa_template = WhatsAppTemplate.objects.get(
                    slug=row.whatsapp_template_slug, locale=locale
                )
            except WhatsAppTemplate.DoesNotExist:
                raise ImportException(
                    f"The template '{row.whatsapp_template_slug}' does not exist for locale '{locale}'"
                )
            page.whatsapp_body.append(
                ShadowWhatsAppTemplate(slug=wa_template.slug, locale=wa_template.locale)
            )

            if row.is_whatsapp_message:
                # TODO: log a warning
                pass

        else:
            self.add_message_to_shadow_content_page_from_row(row, locale)
            # TODO: Media
            # Currently media is exported as a URL, which just has an ID. This doesn't
            # actually help us much, as IDs can differ between instances, so we need
            # a better way of exporting and importing media here

        if row.is_sms_message:
            page.sms_title = row.sms_title

        if row.is_ussd_message:
            page.ussd_title = row.ussd_title

        if row.is_messenger_message:
            page.messenger_title = row.messenger_title

        if row.is_viber_message:
            page.viber_title = row.viber_title

        # Translation keys are required for pages with a non-default locale,
        # but optional for the default locale.
        if row.translation_tag or locale != self.default_locale():
            page.translation_key = row.translation_tag

    def add_variation_to_shadow_content_page_from_row(
        self, row: "ContentRow", locale: Locale
    ) -> None:
        try:
            page = self.shadow_pages[(row.slug, locale)]
        except KeyError:
            raise ImportException(
                f"This is a variation for the content page with slug '{row.slug}' and locale '{locale}', but no such page exists"
            )
        whatsapp_block = page.whatsapp_body[-1]

        if isinstance(whatsapp_block, ShadowWhatsappBlock):
            whatsapp_block.variation_messages.append(
                ShadowVariationBlock(
                    message=row.variation_body,
                    variation_restrictions=row.variation_title,
                )
            )

    def _get_shadow_page(self, slug: str, locale: Locale) -> Page:
        try:
            return self.shadow_pages[(slug, locale)]
        except KeyError:
            raise ImportException(
                f"This is a message for page with slug '{slug}' and locale '{locale}', but no such page exists"
            )

    def _get_form(
        self, slug: str, locale: Locale, title: str, page_slug: str, item_type: str
    ) -> Assessment:
        try:
            return Assessment.objects.get(slug=slug, locale=locale)
        except Assessment.DoesNotExist:
            raise ImportException(
                f"No form found with slug '{slug}' and locale '{locale}' for go_to_form {item_type} '{title}' on page '{page_slug}'"
            )

    def _create_interactive_items(
        self,
        row_field: list[dict[str, Any]],
        page: Page,
        slug: str,
        locale: Locale,
        item_type: str,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for index, item in enumerate(row_field):
            try:
                if item["type"] == "next_message":
                    items.append(
                        {
                            "id": str(uuid4()),
                            "type": item["type"],
                            "value": {"title": item["title"]},
                        }
                    )
                elif item["type"] == "go_to_page":
                    item["index"] = index
                    if item_type == "button":
                        go_to_page = self.go_to_page_buttons
                    else:
                        go_to_page = self.go_to_page_list_items
                    page_gtp = go_to_page[(slug, locale)]
                    page_gtp[len(page.whatsapp_body)].append(item)
                elif item["type"] == "go_to_form":
                    form = self._get_form(
                        item["slug"],
                        locale,
                        item["title"],
                        slug,
                        item_type,
                    )
                    items.append(
                        {
                            "id": str(uuid4()),
                            "type": item["type"],
                            "value": {
                                "title": item["title"],
                                "form": form.id,
                            },
                        }
                    )
                elif not item["type"]:
                    pass
                else:
                    raise ImportException(
                        f"{item_type} with invalid type '{item['type']}'"
                    )
            except KeyError as e:
                raise ImportException(f"{item_type} is missing key {e}")
        return items

    def add_message_to_shadow_content_page_from_row(
        self, row: "ContentRow", locale: Locale
    ) -> None:
        try:
            page = self.shadow_pages[(row.slug, locale)]
        except KeyError:
            raise ImportException(
                f"This is a message for page with slug '{row.slug}' and locale '{locale}', but no such page exists"
            )
        if row.is_whatsapp_message:
            page.enable_whatsapp = True
            page = self._get_shadow_page(row.slug, locale)
            buttons = self._create_interactive_items(
                row.buttons, page, row.slug, locale, "button"
            )
            list_items = self._create_interactive_items(
                row.list_items, page, row.slug, locale, "list item"
            )

            page.whatsapp_body.append(
                ShadowWhatsappBlock(
                    message=row.whatsapp_body,
                    example_values=row.example_values,
                    buttons=buttons,
                    footer=row.footer,
                    list_title=row.list_title,
                    list_items=list_items,
                )
            )
        if row.is_sms_message:
            page.enable_sms = True
            page.sms_body.append(ShadowSMSBlock(message=row.sms_body))

        if row.is_ussd_message:
            page.enable_ussd = True
            page.ussd_body.append(ShadowUSSDBlock(message=row.ussd_body))

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
    locale: Locale
    row_num: int
    enable_web: bool = False
    title: str = ""
    subtitle: str = ""
    body: str = ""
    enable_whatsapp: bool = False
    whatsapp_title: str = ""
    whatsapp_body: list[Union["ShadowWhatsappBlock", "ShadowWhatsAppTemplate"]] = field(
        default_factory=list
    )
    enable_sms: bool = False
    sms_title: str = ""
    sms_body: list["ShadowSMSBlock"] = field(default_factory=list)
    enable_ussd: bool = False
    ussd_title: str = ""
    ussd_body: list["ShadowUSSDBlock"] = field(default_factory=list)
    enable_messenger: bool = False
    messenger_title: str = ""
    messenger_body: list["ShadowMessengerBlock"] = field(default_factory=list)
    enable_viber: bool = False
    viber_title: str = ""
    viber_body: list["ShadowViberBlock"] = field(default_factory=list)
    translation_key: str | None = None
    tags: list[str] = field(default_factory=list)
    quick_replies: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    related_pages: list[str] = field(default_factory=list)

    # FIXME: collect errors across all fields
    def validate_page_using_form(self, page: Page) -> None:
        edit_handler = page.edit_handler.bind_to_model(ContentPage)
        validate_using_form(edit_handler, page, self.row_num)

    def save(self, parent: Page) -> None:
        try:
            page = ContentPage.objects.get(slug=self.slug, locale=self.locale)
        except ContentPage.DoesNotExist:
            page = ContentPage(slug=self.slug, locale=self.locale)

        self.add_web_to_page(page)
        self.add_whatsapp_to_page(page)
        self.add_sms_to_page(page)
        self.add_ussd_to_page(page)
        self.add_messenger_to_page(page)
        self.add_viber_to_page(page)
        self.add_tags_to_page(page)
        self.add_quick_replies_to_page(page)
        self.add_triggers_to_page(page)
        self.validate_page_using_form(page)

        try:
            with contextlib.suppress(NodeAlreadySaved):
                parent.add_child(instance=page)
            page.save_revision().publish()

        except ValidationError as errors:
            err = []
            for error in errors:
                field_name = error[0]
                for msg in error[1]:
                    err.append(f"{field_name} - {msg}")
            raise ImportException(
                [f"Validation error: {msg}" for msg in err], self.row_num
            )

    def add_web_to_page(self, page: ContentPage) -> None:
        page.enable_web = self.enable_web
        page.title = self.title
        page.subtitle = self.subtitle
        page.body = self.formatted_body
        if self.translation_key is not None:
            page.translation_key = self.translation_key

    def add_whatsapp_to_page(self, page: ContentPage) -> None:
        page.enable_whatsapp = self.enable_whatsapp
        page.whatsapp_title = self.whatsapp_title
        page.whatsapp_body.clear()
        for message in self.formatted_whatsapp_body:
            body_type = (
                "Whatsapp_Template"
                if isinstance(message, WhatsAppTemplate)
                else "Whatsapp_Message"
            )
            page.whatsapp_body.append((body_type, message))

    def add_sms_to_page(self, page: ContentPage) -> None:
        page.enable_sms = self.enable_sms
        page.sms_title = self.sms_title
        page.sms_body.clear()
        for message in self.formatted_sms_body:
            page.sms_body.append(("SMS_Message", message))

    def add_ussd_to_page(self, page: ContentPage) -> None:
        page.enable_ussd = self.enable_ussd
        page.ussd_title = self.ussd_title
        page.ussd_body.clear()
        for message in self.formatted_ussd_body:
            page.ussd_body.append(("USSD_Message", message))

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
        page = ContentPage.objects.get(slug=self.slug, locale=self.locale)
        related_pages = []
        for related_page_slug in self.related_pages:
            try:
                related_page = Page.objects.get(
                    slug=related_page_slug, locale=self.locale
                )
            except Page.DoesNotExist:
                raise ImportException(
                    f"Cannot find related page with slug '{related_page_slug}' and "
                    f"locale '{self.locale}'",
                    self.row_num,
                )
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
        formatted = []
        for m in self.whatsapp_body:
            if isinstance(m, ShadowWhatsAppTemplate):
                template = WhatsAppTemplate.objects.get(slug=m.slug, locale=m.locale)
                formatted.append(template)
            else:
                formatted.append(WhatsappBlock().to_python(m.wagtail_format))

        return formatted

    @property
    def formatted_sms_body(self) -> list[StructValue]:
        return [SMSBlock().to_python(m.wagtail_format) for m in self.sms_body]

    @property
    def formatted_ussd_body(self) -> list[StructValue]:
        return [USSDBlock().to_python(m.wagtail_format) for m in self.ussd_body]

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
    buttons: list[dict[str, Any]] = field(default_factory=list)
    example_values: list[str] = field(default_factory=list)
    variation_messages: list["ShadowVariationBlock"] = field(default_factory=list)
    list_title: str = ""
    list_items: list[dict[str, Any]] = field(default_factory=list)
    footer: str = ""

    @property
    def wagtail_format(
        self,
    ) -> dict[str, str | list[dict[str, str | list[dict[str, str]]]] | list[str]]:
        return {
            "message": self.message,
            "example_values": self.example_values,
            "buttons": self.buttons,
            "variation_messages": [m.wagtail_format for m in self.variation_messages],
            "list_title": self.list_title,
            "list_items": self.list_items,
            "footer": self.footer,
        }


@dataclass
class ShadowWhatsAppTemplate:
    slug: str = ""
    locale: Locale | str | None = None

    @property
    def wagtail_format(self) -> dict[str, str | None]:
        return {
            "slug": self.slug,
            "locale": self.locale,
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
class ShadowSMSBlock:
    message: str = ""

    @property
    def wagtail_format(self) -> dict[str, str]:
        return {"message": self.message}


@dataclass(slots=True)
class ShadowUSSDBlock:
    message: str = ""

    @property
    def wagtail_format(self) -> dict[str, str]:
        return {"message": self.message}


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
    parent: str = ""
    web_title: str = ""
    web_subtitle: str = ""
    web_body: str = ""
    whatsapp_title: str = ""
    whatsapp_body: str = ""
    whatsapp_template_slug: str = ""
    example_values: list[str] = field(default_factory=list)
    variation_title: dict[str, str] = field(default_factory=dict)
    variation_body: str = ""
    list_title: str = ""
    list_items: list[dict[str, Any]] = field(default_factory=list)
    sms_title: str = ""
    sms_body: str = ""
    ussd_title: str = ""
    ussd_body: str = ""
    messenger_title: str = ""
    messenger_body: str = ""
    viber_title: str = ""
    viber_body: str = ""
    translation_tag: str = ""
    tags: list[str] = field(default_factory=list)
    quick_replies: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    locale: str = ""
    buttons: list[dict[str, Any]] = field(default_factory=list)
    image_link: str = ""
    doc_link: str = ""
    media_link: str = ""
    related_pages: list[str] = field(default_factory=list)
    footer: str = ""
    language_code: str = ""
    import_warnings: list[ImportWarning] = field(default_factory=list)

    @classmethod
    def from_flat(cls, row: dict[str, str], row_num: int) -> "ContentRow":
        class_fields = {field.name for field in fields(cls)}
        # NOTES:
        # * We strip leading and trailing whitespace off the field values
        #   because that lets us be a little more permissive with inputs, but
        #   we leave the field keys as-is because otherwise we may end up with
        #   duplicates for keys with whitespace differences.
        # * It's also important to strip whitespace in both the output dict and
        #   the emptiness check, otherwise whitespace-only fields will be
        #   non-empty here but empty below.
        # * We need to check `value` before `value.strip()` because we may get
        #   `None` values for missing fields.
        row = {
            key: value.strip()
            for key, value in row.items()
            if key in class_fields and value and value.strip()
        }
        if "slug" not in row:
            raise ImportException("Missing slug value", row_num)

        list_items = []
        try:
            row_list_items = row.pop("list_items", "")
            list_items = JSON_loader(row_num, row_list_items)
        except ImportException:
            list_items = [
                {"type": "next_message", "title": item}
                for item in deserialise_list(row_list_items)
            ]
        return cls(
            variation_title=deserialise_dict(row.pop("variation_title", "")),
            tags=deserialise_list(row.pop("tags", "")),
            quick_replies=deserialise_list(row.pop("quick_replies", "")),
            triggers=deserialise_list(row.pop("triggers", "")),
            related_pages=deserialise_list(row.pop("related_pages", "")),
            example_values=deserialise_list(row.pop("example_values", "")),
            buttons=(
                JSON_loader(row_num, row.pop("buttons", ""))
                if row.get("buttons")
                else []
            ),
            list_title=row.pop("list_title", ""),
            list_items=list_items,
            footer=row.pop("footer", ""),
            **row,
            import_warnings=[],
        )

    @property
    def is_page_index(self) -> bool:
        return bool(self.web_title) and not any(
            [
                self.parent,
                self.web_body,
                self.whatsapp_body,
                self.sms_body,
                self.ussd_body,
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
        return bool(self.whatsapp_template_slug)

    @property
    def is_sms_message(self) -> bool:
        return bool(self.sms_body)

    @property
    def is_ussd_message(self) -> bool:
        return bool(self.ussd_body)

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

    items = list(csv.reader([value]))[0]
    return [item.strip() for item in items]


def to_int_or_none(val: str | None) -> int | None:
    if val is None:
        return None
    try:
        return int(val)
    except ValueError:
        # If it's an excel document with number formatting, we get a float
        # If it's not a valid number, then we let the exception bubble up
        return int(float(val))
