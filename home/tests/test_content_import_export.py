import csv
import json
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from functools import wraps
from io import BytesIO, StringIO
from pathlib import Path
from queue import Queue
from typing import Any

import pytest
from django.core import serializers  # type: ignore
from django.core.files.images import ImageFile  # type: ignore
from openpyxl import load_workbook
from pytest_django.fixtures import SettingsWrapper
from wagtail.images.models import Image  # type: ignore
from wagtail.models import Locale, Page  # type: ignore

from home.content_import_export import import_content, old_import_content
from home.import_content_pages import ImportException
from home.models import ContentPage, ContentPageIndex, HomePage

from .helpers import set_profile_field_options
from .page_builder import (
    MBlk,
    MBody,
    NextBtn,
    PageBtn,
    PageBuilder,
    SBlk,
    SBody,
    UBlk,
    UBody,
    VarMsg,
    VBlk,
    VBody,
    WABlk,
    WABody,
)

ExpDict = dict[str, Any]
ExpPair = tuple[ExpDict, ExpDict]
ExpDicts = Iterable[ExpDict]
ExpDictsPair = tuple[ExpDicts, ExpDicts]


def filter_both(
    filter_func: Callable[[ExpDict], ExpDict]
) -> Callable[[ExpDict, ExpDict], ExpPair]:
    @wraps(filter_func)
    def ff(src: ExpDict, dst: ExpDict) -> ExpPair:
        return filter_func(src), filter_func(dst)

    return ff


@filter_both
def add_new_fields(entry: ExpDict) -> ExpDict:
    # FIXME: This should probably be in a separate test for importing old exports.
    return {
        "whatsapp_template_name": "",
        **entry,
        "whatsapp_template_category": entry.get("whatsapp_template_category")
        or "UTILITY",
        "example_values": entry.get("example_values") or "[]",
        "sms_body": entry.get("sms_body") or "",
        "ussd_body": entry.get("ussd_body") or "",
    }


def remove_translation_tag_from_tags(src: ExpDict, dst: ExpDict) -> ExpPair:
    # FIXME: Do we actually need translation_tag to be added to tags?
    if not src["translation_tag"]:
        return src, dst
    dtags = [tag for tag in dst["tags"].split(", ") if tag != src["translation_tag"]]
    return src, dst | {"tags": ", ".join(dtags)}


@filter_both
def ignore_certain_fields(entry: ExpDict) -> ExpDict:
    # FIXME: Do we need page.id to be imported? At the moment nothing in the
    #        import reads that.
    # FIXME: Implement import/export for doc_link, image_link, media_link.
    ignored_fields = {
        "page_id",
        "doc_link",
        "image_link",
        "media_link",
    }
    return {k: v for k, v in entry.items() if k not in ignored_fields}


@filter_both
def ignore_old_fields(entry: ExpDict) -> ExpDict:
    ignored_fields = {"next_prompt", "translation_tag", "buttons"}
    return {k: v for k, v in entry.items() if k not in ignored_fields}


@filter_both
def strip_leading_whitespace(entry: ExpDict) -> ExpDict:
    # FIXME: Do we expect imported content to have leading spaces removed?
    bodies = {k: v.lstrip(" ") for k, v in entry.items() if k.endswith("_body")}
    return {**entry, **bodies}


EXPORT_FILTER_FUNCS = [
    add_new_fields,
    ignore_certain_fields,
    strip_leading_whitespace,
]

OLD_EXPORT_FILTER_FUNCS = [
    remove_translation_tag_from_tags,
    ignore_old_fields,
]


def filter_exports(srcs: ExpDicts, dsts: ExpDicts, importer: str) -> ExpDictsPair:
    fsrcs, fdsts = [], []
    for src, dst in zip(srcs, dsts, strict=True):
        for ff in EXPORT_FILTER_FUNCS:
            src, dst = ff(src, dst)
        if importer == "old":
            for ff in OLD_EXPORT_FILTER_FUNCS:
                src, dst = ff(src, dst)
        fsrcs.append(src)
        fdsts.append(dst)
    return fsrcs, fdsts


def csv2dicts(csv_bytes: bytes) -> ExpDicts:
    return list(csv.DictReader(StringIO(csv_bytes.decode())))


DbDict = dict[str, Any]
DbDicts = Iterable[DbDict]


def _models2dicts(model_instances: Any) -> DbDicts:
    return json.loads(serializers.serialize("json", model_instances))


def get_page_json() -> DbDicts:
    page_objs = Page.objects.type(ContentPage, ContentPageIndex).all()
    pages = {p["pk"]: p["fields"] for p in _models2dicts(page_objs)}
    content_pages = [
        *_models2dicts(ContentPage.objects.all()),
        *_models2dicts(ContentPageIndex.objects.all()),
    ]
    return [p | {"fields": {**pages[p["pk"]], **p["fields"]}} for p in content_pages]


def per_page(filter_func: Callable[[DbDict], DbDict]) -> Callable[[DbDicts], DbDicts]:
    @wraps(filter_func)
    def fp(pages: DbDicts) -> DbDicts:
        return [filter_func(page) for page in pages]

    return fp


def _is_json_field(field_name: str) -> bool:
    return field_name.endswith("body") or field_name in {"related_pages"}


@per_page
def decode_json_fields(page: DbDict) -> DbDict:
    fields = {
        k: json.loads(v) if _is_json_field(k) else v for k, v in page["fields"].items()
    }
    return page | {"fields": fields}


def _normalise_button_pks(body: DbDict, min_pk: int) -> DbDict:
    value = body["value"]
    if "buttons" in value:
        buttons = []
        for button in value["buttons"]:
            if button["type"] == "go_to_page":
                v = button["value"]
                button = button | {"value": v | {"page": v["page"] - min_pk}}
            buttons.append(button)
        value = value | {"buttons": buttons}
    return body | {"value": value}


def _normalise_pks(page: DbDict, min_pk: int) -> DbDict:
    fields = page["fields"]
    if "related_pages" in fields:
        related_pages = [
            rp | {"value": rp["value"] - min_pk} for rp in fields["related_pages"]
        ]
        fields = fields | {"related_pages": related_pages}
    if "whatsapp_body" in fields:
        body = [_normalise_button_pks(b, min_pk) for b in fields["whatsapp_body"]]
        fields = fields | {"whatsapp_body": body}
    return page | {"fields": fields, "pk": page["pk"] - min_pk}


def normalise_pks(pages: DbDicts) -> DbDicts:
    min_pk = min(p["pk"] for p in pages)
    return [_normalise_pks(p, min_pk) for p in pages]


def _update_field(
    pages: DbDicts, field_name: str, update_fn: Callable[[Any], Any]
) -> DbDicts:
    for p in pages:
        fields = p["fields"]
        yield p | {"fields": {**fields, field_name: update_fn(fields[field_name])}}


def normalise_revisions(pages: DbDicts) -> DbDicts:
    if "latest_revision" not in list(pages)[0]["fields"]:
        return pages
    min_latest = min(p["fields"]["latest_revision"] for p in pages)
    min_live = min(p["fields"]["live_revision"] for p in pages)
    pages = _update_field(pages, "latest_revision", lambda v: v - min_latest)
    pages = _update_field(pages, "live_revision", lambda v: v - min_live)
    return pages


def _remove_fields(pages: DbDicts, field_names: set[str]) -> DbDicts:
    for p in pages:
        fields = {k: v for k, v in p["fields"].items() if k not in field_names}
        yield p | {"fields": fields}


PAGE_TIMESTAMP_FIELDS = {
    "first_published_at",
    "last_published_at",
    "latest_revision_created_at",
}


def remove_timestamps(pages: DbDicts) -> DbDicts:
    return _remove_fields(pages, PAGE_TIMESTAMP_FIELDS)


def _normalise_varmsg_ids(page_id: str, var_list: list[dict[str, Any]]) -> None:
    for i, varmsg in enumerate(var_list):
        assert "id" in varmsg
        varmsg["id"] = f"{page_id}:var:{i}"
        for ir, rest in enumerate(varmsg["value"]["variation_restrictions"]):
            rest["id"] = f"{page_id}:var:{i}:var:{ir}"


def _normalise_body_field_ids(
    page: DbDict, body_name: str, body_list: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    for i, body in enumerate(body_list):
        assert "id" in body
        body["id"] = f"fake:{page['pk']}:{body_name}:{i}"
        if "variation_messages" in body["value"]:
            _normalise_varmsg_ids(body["id"], body["value"]["variation_messages"])
    return body_list


@per_page
def normalise_body_ids(page: DbDict) -> DbDict:
    # FIXME: Does it matter if these change?
    fields = {
        k: _normalise_body_field_ids(page, k, v) if k.endswith("body") else v
        for k, v in page["fields"].items()
    }
    return page | {"fields": fields}


def _normalise_related_page_ids(
    page: DbDict, rp_list: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    for i, rp in enumerate(rp_list):
        assert "id" in rp
        rp["id"] = f"fake:{page['pk']}:related_page:{i}"
    return rp_list


@per_page
def normalise_related_page_ids(page: DbDict) -> DbDict:
    # FIXME: Does it matter if these change?
    fields = {
        k: _normalise_related_page_ids(page, v) if k == "related_pages" else v
        for k, v in page["fields"].items()
    }
    return page | {"fields": fields}


def remove_translation_key(pages: DbDicts) -> DbDicts:
    # For old importer.
    return _remove_fields(pages, {"translation_key"})


def remove_revisions(pages: DbDicts) -> DbDicts:
    # For old importer. Sometimes (maybe for the ContentPages imported after
    # the first language?) we get higher revision numbers. Let's just strip
    # them all and be done with it.
    return _remove_fields(pages, {"latest_revision", "live_revision"})


@per_page
def null_to_emptystr(page: DbDict) -> DbDict:
    # FIXME: Confirm that there's no meaningful difference here, potentially
    #        make these fields non-nullable.
    fields = {**page["fields"]}
    for k in [
        "subtitle",
        "whatsapp_title",
        "messenger_title",
        "viber_title",
    ]:
        if k in fields and fields[k] is None:
            fields[k] = ""
    if "whatsapp_body" in fields:
        for body in fields["whatsapp_body"]:
            if "next_prompt" in body["value"] and not body["value"]["next_prompt"]:
                body["value"]["next_prompt"] = ""
    return page | {"fields": fields}


def _add_fields(body: dict[str, Any], extra_fields: dict[str, Any]) -> None:
    body["value"] = extra_fields | body["value"]


@per_page
def add_body_fields(page: DbDict) -> DbDict:
    if "whatsapp_body" in page["fields"]:
        for body in page["fields"]["whatsapp_body"]:
            _add_fields(
                body,
                {
                    "document": None,
                    "image": None,
                    "media": None,
                    "next_prompt": "",
                    "example_values": [],
                    "variation_messages": [],
                },
            )
    if "sms_body" in page["fields"]:
        for body in page["fields"]["sms_body"]:
            _add_fields(body, {"image": None})
    if "ussd_body" in page["fields"]:
        for body in page["fields"]["ussd_body"]:
            _add_fields(body, {"image": None})
    if "messenger_body" in page["fields"]:
        for body in page["fields"]["messenger_body"]:
            _add_fields(body, {"image": None})
    if "viber_body" in page["fields"]:
        for body in page["fields"]["viber_body"]:
            _add_fields(body, {"image": None})
    return page


WEB_PARA_RE = re.compile(r'^<div class="block-paragraph">(.*)</div>$')


@per_page
def clean_web_paragraphs(page: DbDict) -> DbDict:
    # FIXME: Handle this at export time, I guess.
    if "body" in page["fields"]:
        body = [
            b | {"value": WEB_PARA_RE.sub(r"\1", b["value"])}
            for b in page["fields"]["body"]
        ]
        page = page | {"fields": page["fields"] | {"body": body}}
    return page


@per_page
def remove_next_prompt(page: DbDict) -> DbDict:
    if "whatsapp_body" in page["fields"]:
        for body in page["fields"]["whatsapp_body"]:
            body["value"].pop("next_prompt", None)
    return page


@per_page
def remove_buttons(page: DbDict) -> DbDict:
    if "whatsapp_body" in page["fields"]:
        for body in page["fields"]["whatsapp_body"]:
            body["value"].pop("buttons", None)
    return page


@per_page
def remove_example_values(page: DbDict) -> DbDict:
    if "whatsapp_body" in page["fields"]:
        for body in page["fields"]["whatsapp_body"]:
            body["value"].pop("example_values", None)
    return page


@per_page
def remove_sms_fields(page: DbDict) -> DbDict:
    if "sms_body" in page["fields"]:
        for body in page["fields"]["sms_body"]:
            body["value"].pop("sms_body", None)
    return page


@per_page
def remove_ussd_fields(page: DbDict) -> DbDict:
    if "ussd_body" in page["fields"]:
        for body in page["fields"]["ussd_body"]:
            body["value"].pop("ussd_body", None)
    return page


@per_page
def remove_button_ids(page: DbDict) -> DbDict:
    if "whatsapp_body" in page["fields"]:
        for body in page["fields"]["whatsapp_body"]:
            buttons = body["value"].get("buttons", [])
            for button in buttons:
                button.pop("id", None)
    return page


@per_page
def remove_example_value_ids(page: DbDict) -> DbDict:
    if "whatsapp_body" in page["fields"]:
        for body in page["fields"]["whatsapp_body"]:
            example_values = body["value"].get("example_values", [])
            for example_value in example_values:
                example_value.pop("id", None)
    return page


@per_page
def enable_web(page: DbDict) -> DbDict:
    page["fields"]["enable_web"] = True
    return page


PAGE_FILTER_FUNCS = [
    normalise_pks,
    normalise_revisions,
    remove_timestamps,
    normalise_body_ids,
    normalise_related_page_ids,
    clean_web_paragraphs,
    null_to_emptystr,
    remove_button_ids,
    remove_example_value_ids,
]

OLD_PAGE_FILTER_FUNCS = [
    remove_translation_key,
    remove_revisions,
    add_body_fields,
    remove_next_prompt,
    remove_buttons,
    remove_example_values,
    enable_web,
    remove_sms_fields,
    remove_ussd_fields,
]


@dataclass
class ImportExport:
    admin_client: Any
    importer: str
    format: str

    @property
    def _import_content(self) -> Callable[..., None]:
        return {
            "new": import_content,
            "old": old_import_content,
        }[self.importer]

    @property
    def _filter_export(self) -> Callable[..., bytes]:
        return {
            "csv": self._filter_export_CSV,
            "xlsx": self._filter_export_XLSX,
        }[self.format]

    def _filter_export_row(self, row: ExpDict, locale: str | None) -> bool:
        """
        Determine whether to keep a given export row.
        """
        if locale:
            if row["locale"] not in [None, "", locale]:
                return False
        return True

    def _filter_export_CSV(self, content: bytes, locale: str | None) -> bytes:
        reader = csv.DictReader(StringIO(content.decode()))
        assert reader.fieldnames is not None
        out_content = StringIO()
        writer = csv.DictWriter(out_content, fieldnames=reader.fieldnames)
        writer.writeheader()
        for row in reader:
            if self._filter_export_row(row, locale=locale):
                writer.writerow(row)
        return out_content.getvalue().encode()

    def _filter_export_XLSX(self, content: bytes, locale: str | None) -> bytes:
        workbook = load_workbook(BytesIO(content))
        worksheet = workbook.worksheets[0]
        header = next(worksheet.iter_rows(max_row=1, values_only=True))

        rows_to_remove: list[int] = []
        for i, row in enumerate(worksheet.iter_rows(min_row=2, values_only=True)):
            r = {k: v for k, v in zip(header, row, strict=True) if isinstance(k, str)}
            if not self._filter_export_row(r, locale=locale):
                rows_to_remove.append(i + 2)
        for row_num in reversed(rows_to_remove):
            worksheet.delete_rows(row_num)

        out_content = BytesIO()
        workbook.save(out_content)
        return out_content.getvalue()

    def export_content(self, locale: str | None = None) -> bytes:
        """
        Export all (or filtered) content in the configured format.

        FIXME:
         * If we filter the export by locale, we only get ContentPage entries
           for the given language, but we still get ContentPageIndex rows for
           all languages.
        """
        url = f"/admin/home/contentpage/?export={self.format}"
        if locale:
            loc = Locale.objects.get(language_code=locale)
            locale = str(loc)
            url = f"{url}&locale__id__exact={loc.id}"
        content = self.admin_client.get(url).content
        # Hopefully we can get rid of this at some point.
        if locale:
            content = self._filter_export(content, locale=locale)
        if self.format == "csv":
            print("-v-CONTENT-v-")
            print(content.decode())
            print("-^-CONTENT-^-")
        return content

    def import_content(self, content_bytes: bytes, **kw: Any) -> None:
        """
        Import given content in the configured format with the configured importer.
        """
        self._import_content(BytesIO(content_bytes), self.format.upper(), Queue(), **kw)

    def read_bytes(self, path_str: str, path_base: str = "home/tests") -> bytes:
        return (Path(path_base) / path_str).read_bytes()

    def import_file(
        self, path_str: str, path_base: str = "home/tests", **kw: Any
    ) -> bytes:
        """
        Import given content file in the configured format with the configured importer.
        """
        content = self.read_bytes(path_str, path_base)
        self.import_content(content, **kw)
        return content

    def export_reimport(self) -> None:
        """
        Export all content, then immediately reimport it.
        """
        self.import_content(self.export_content())

    def get_page_json(self, locale: str | None = None) -> DbDicts:
        """
        Serialize all ContentPage and ContentPageIndex instances and normalize
        things that vary across import/export.
        """
        pages = decode_json_fields(get_page_json())
        if self.importer == "old":
            for ff in OLD_PAGE_FILTER_FUNCS:
                pages = ff(pages)
        for ff in PAGE_FILTER_FUNCS:
            pages = ff(pages)
        if locale is not None:
            loc = Locale.objects.get(language_code=locale)
            pages = [p for p in pages if p["fields"]["locale"] == loc.id]
        return sorted(pages, key=lambda p: p["pk"])

    def csvs2dicts(self, src_bytes: bytes, dst_bytes: bytes) -> ExpDictsPair:
        src = csv2dicts(src_bytes)
        dst = csv2dicts(dst_bytes)
        return filter_exports(src, dst, self.importer)


@pytest.fixture(params=["old", "new"])
def csv_impexp(request: Any, admin_client: Any) -> ImportExport:
    return ImportExport(admin_client, request.param, "csv")


@pytest.fixture()
def newcsv_impexp(request: Any, admin_client: Any) -> ImportExport:
    return ImportExport(admin_client, "new", "csv")


@pytest.mark.django_db
class TestImportExportRoundtrip:
    """
    Test importing and reexporting content produces an export that is
    equilavent to the original imported content.

    NOTE: This is not a Django (or even unittest) TestCase. It's just a
        container for related tests.
    """

    def test_simple(self, csv_impexp: ImportExport) -> None:
        """
        Importing a simple CSV file and then exporting it produces a duplicate
        of the original file.

        (This uses content2.csv from test_api.py.)

        FIXME:
         * This should probably be in a separate test for importing old exports.
         * Do we need page.id to be exported? At the moment nothing in the
           import reads that.
         * Do we expect imported content to have leading spaces removed?
         * Should we set enable_web and friends based on body, title, or an
           enable field that we'll need to add to the export?
        """
        csv_bytes = csv_impexp.import_file("content2.csv")
        content = csv_impexp.export_content()
        src, dst = csv_impexp.csvs2dicts(csv_bytes, content)
        assert dst == src

    def test_less_simple(self, csv_impexp: ImportExport) -> None:
        """
        Importing a less simple CSV file and then exporting it produces a
        duplicate of the original file.

        (This uses exported_content_20230911-variations-linked-page.csv.)

        FIXME:
         * Implement import/export for doc_link, image_link, media_link.
        """
        set_profile_field_options()
        csv_bytes = csv_impexp.import_file(
            "exported_content_20230911-variations-linked-page.csv"
        )
        content = csv_impexp.export_content()
        src, dst = csv_impexp.csvs2dicts(csv_bytes, content)
        assert dst == src

    def test_multiple_messages(self, csv_impexp: ImportExport) -> None:
        """
        Importing a CSV file containing multiple messages of each type for a
        page and then exporting it produces a duplicate of the original file.

        (This uses multiple_messages.csv.)
        """
        set_profile_field_options()
        csv_bytes = csv_impexp.import_file("multiple_messages.csv")
        content = csv_impexp.export_content()
        src, dst = csv_impexp.csvs2dicts(csv_bytes, content)
        assert dst == src

    def test_translations_sep(self, csv_impexp: ImportExport) -> None:
        """
        Importing a CSV file split into separate parts per locale and then
        exporting it produces a duplicate of the original file.

        (This uses translations-sp.csv and the two language-specific subsets thereof.)

        FIXME:
         * Remove this test when the old importer goes away completely.
        """
        # Create a new homepage for Portuguese.
        pt, _created = Locale.objects.get_or_create(language_code="pt")
        HomePage.add_root(locale=pt, title="Home (pt)", slug="home-pt")

        set_profile_field_options()
        csv_impexp.import_file("translations-sep-en.csv")
        csv_impexp.import_file("translations-sep-pt.csv", locale="pt", purge=False)
        csv_bytes = csv_impexp.read_bytes("translations-sep.csv")
        content = csv_impexp.export_content()
        src, dst = csv_impexp.csvs2dicts(csv_bytes, content)
        assert dst == src

    def test_default_locale(self, newcsv_impexp: ImportExport) -> None:
        """
        Importing a CSV file with multiple languages and specifying a locale
        and then exporting it produces a duplicate of the original file but
        with only pages from the specifyied specified locale included.

        NOTE: Old importer can't handle multiple languages at once.

        (This uses translations.csv and the en language-specific subset thereof.)
        """
        # Create a new homepage for Portuguese.
        pt, _created = Locale.objects.get_or_create(language_code="pt")
        HomePage.add_root(locale=pt, title="Home (pt)", slug="home-pt")

        set_profile_field_options()
        newcsv_impexp.import_file("translations.csv", locale="en")
        csv_bytes = newcsv_impexp.read_bytes("translations-en.csv")
        content = newcsv_impexp.export_content()
        src, dst = newcsv_impexp.csvs2dicts(csv_bytes, content)
        assert dst == src

    def test_translated_locale(self, newcsv_impexp: ImportExport) -> None:
        """
        Importing a CSV file with multiple languages and specifying a locale
        and then exporting it produces a duplicate of the original file but
        with only pages from the specifyied specified locale included.

        NOTE: Old importer can't handle multiple languages at once.

        (This uses translations.csv and the pt language-specific subset thereof.)
        """
        # Create a new homepage for Portuguese.
        pt, _created = Locale.objects.get_or_create(language_code="pt")
        HomePage.add_root(locale=pt, title="Home (pt)", slug="home-pt")

        set_profile_field_options()
        newcsv_impexp.import_file("translations.csv", locale="pt")
        csv_bytes = newcsv_impexp.read_bytes("translations-pt.csv")
        content = newcsv_impexp.export_content()
        src, dst = newcsv_impexp.csvs2dicts(csv_bytes, content)
        assert dst == src

    def test_all_locales(self, newcsv_impexp: ImportExport) -> None:
        """
        Importing a CSV file containing translations and then exporting it
        produces a duplicate of the original file.

        NOTE: Old importer can't handle multiple languages at once.

        (This uses translations.csv.)
        """
        # Create a new homepage for Portuguese.
        pt, _created = Locale.objects.get_or_create(language_code="pt")
        HomePage.add_root(locale=pt, title="Home (pt)", slug="home-pt")

        set_profile_field_options()
        csv_bytes = newcsv_impexp.import_file("translations.csv")
        content = newcsv_impexp.export_content()
        src, dst = newcsv_impexp.csvs2dicts(csv_bytes, content)
        assert dst == src

    def test_all_locales_split(self, newcsv_impexp: ImportExport) -> None:
        """
        Importing a CSV file split into separate parts per locale and then
        exporting it produces a duplicate of the original file.

        NOTE: Old importer can't handle non-unique slugs.

        (This uses translations.csv and the two language-specific subsets thereof.)
        """
        # Create a new homepage for Portuguese.
        pt, _created = Locale.objects.get_or_create(language_code="pt")
        HomePage.add_root(locale=pt, title="Home (pt)", slug="home-pt")

        set_profile_field_options()
        csv_bytes = newcsv_impexp.read_bytes("translations.csv")
        newcsv_impexp.import_file("translations.csv", locale="en")
        newcsv_impexp.import_file("translations.csv", purge=False, locale="pt")

        content = newcsv_impexp.export_content()
        src, dst = newcsv_impexp.csvs2dicts(csv_bytes, content)
        assert dst == src


@pytest.mark.django_db
class TestImportExport:
    """
    Text various import and export scenarios that aren't specifically round
    trips.

    NOTE: This is not a Django (or even unittest) TestCase. It's just a
        container for related tests.
    """

    def test_import_error(self, csv_impexp: ImportExport) -> None:
        """
        Importing an invalid CSV file leaves the db as-is.

        (This uses content2.csv from test_api.py and broken.csv.)
        """
        # Start with some existing content.
        csv_bytes = csv_impexp.import_file("content2.csv")

        # This CSV doesn't have any of the fields we expect.
        with pytest.raises((KeyError, TypeError)):
            csv_impexp.import_file("broken.csv")

        # The export should match the existing content.
        content = csv_impexp.export_content()
        src, dst = csv_impexp.csvs2dicts(csv_bytes, content)
        assert dst == src

    def test_no_translation_key_default(self, newcsv_impexp: ImportExport) -> None:
        """
        Importing pages without translation keys in the default locale causes
        wagtail to generate new translation keys.

        (This uses no-translation-key-default.csv.)
        """
        csv_bytes = newcsv_impexp.import_file("no-translation-key-default.csv")

        content = newcsv_impexp.export_content()
        src, dst = newcsv_impexp.csvs2dicts(csv_bytes, content)
        # Check that the export has translation keys for all rows and clear
        # them to match the imported data
        for row in dst:
            assert len(row["translation_tag"]) == 36  # uuid with dashes
            row["translation_tag"] = ""
        assert dst == src

    def test_no_translation_key_nondefault(self, newcsv_impexp: ImportExport) -> None:
        """
        Importing pages without translation keys in the non-default locale
        causes a validation error.

        (This uses no-translation-key-cpi.csv and no-translation-key-cp.csv.)
        """
        # Create a new homepage for Portuguese.
        pt, _created = Locale.objects.get_or_create(language_code="pt")
        HomePage.add_root(locale=pt, title="Home (pt)", slug="home-pt")

        # A ContentPageIndex without a translation key fails
        with pytest.raises(ImportException) as e:
            newcsv_impexp.import_file("no-translation-key-cpi.csv")

        assert e.value.row_num == 4
        # FIXME: Find a better way to represent this.
        assert "translation_key" in e.value.message
        assert "“” is not a valid UUID." in e.value.message

        # A ContentPage without a translation key fails
        with pytest.raises(ImportException) as e:
            newcsv_impexp.import_file("no-translation-key-cp.csv")

        assert e.value.row_num == 5
        # FIXME: Find a better way to represent this.
        assert "translation_key" in e.value.message
        assert "“” is not a valid UUID." in e.value.message

    def test_invalid_locale_name(self, newcsv_impexp: ImportExport) -> None:
        """
        Importing pages with invalid locale names should raise an error that results
        in an error message that gets sent back to the user
        """
        with pytest.raises(ImportException) as e:
            newcsv_impexp.import_file("invalid-locale-name.csv")

        assert e.value.row_num == 2
        assert e.value.message == "Language not found: NotEnglish"

    def test_multiple_locales_for_name(
        self, newcsv_impexp: ImportExport, settings: SettingsWrapper
    ) -> None:
        """
        Importing pages with locale names that represent multiple locales should raise
        an error that results in an error message that gets sent back to the user
        """
        settings.WAGTAIL_CONTENT_LANGUAGES = settings.LANGUAGES = [
            ("en1", "NotEnglish"),
            ("en2", "NotEnglish"),
        ]
        with pytest.raises(ImportException) as e:
            newcsv_impexp.import_file("invalid-locale-name.csv")

        assert e.value.row_num == 2
        assert (
            e.value.message
            == "Multiple codes for language: NotEnglish -> ['en1', 'en2']"
        )

    def test_missing_parent(self, newcsv_impexp: ImportExport) -> None:
        """
        If the import file specifies a parent title, but there are no pages with that
        title, then an error message should get sent back to the user.
        """
        with pytest.raises(ImportException) as e:
            newcsv_impexp.import_file("missing-parent.csv")

        assert e.value.row_num == 2
        assert (
            e.value.message
            == "Cannot find parent page with title 'missing-parent' and locale "
            "'English'"
        )

    def test_multiple_parents(self, newcsv_impexp: ImportExport) -> None:
        """
        Because we use the title to find a parent page, and it's possible to have
        multiple pages with the same title, it's possible to have the situation where
        we don't know which parent this import points to. In that case we should show
        the user an error message, with information that will allow them to fix it.
        """
        home_page = HomePage.objects.first()
        PageBuilder.build_cpi(home_page, "missing-parent1", "missing-parent")
        PageBuilder.build_cpi(home_page, "missing-parent2", "missing-parent")

        with pytest.raises(ImportException) as e:
            newcsv_impexp.import_file("missing-parent.csv", purge=False)
        assert e.value.row_num == 2
        assert (
            e.value.message
            == "Multiple pages with title 'missing-parent' and locale 'English' for "
            "parent page: ['missing-parent1', 'missing-parent2']"
        )

    def test_go_to_page_button_missing_page(self, newcsv_impexp: ImportExport) -> None:
        """
        Go to page buttons in the import file link to other pages using the slug. But
        if no page with that slug exists, then we should give the user an error message
        that tells them where and how to fix it.
        """
        with pytest.raises(ImportException) as e:
            newcsv_impexp.import_file("missing-gotopage.csv")
        assert e.value.row_num == 2
        assert (
            e.value.message
            == "No pages found with slug 'missing' and locale 'English' for go_to_page "
            "button 'Missing' on page 'ma_import-export'"
        )

    def test_missing_related_pages(self, newcsv_impexp: ImportExport) -> None:
        """
        Related pages are listed as comma separated slugs in imported files. If there
        is a slug listed that we cannot find the page for, then we should show the
        user an error with information about the missing page.
        """
        with pytest.raises(ImportException) as e:
            newcsv_impexp.import_file("missing-related-page.csv")
        assert e.value.row_num == 2
        assert (
            e.value.message
            == "Cannot find related page with slug 'missing related' and locale "
            "'English'"
        )

    def test_invalid_wa_template_category(self, newcsv_impexp: ImportExport) -> None:
        """
        Importing a WhatsApp template with an invalid category should raise an
        error that results in an error message that gets sent back to the user
        """
        with pytest.raises(ImportException) as e:
            newcsv_impexp.import_file("bad-whatsapp-template-category.csv")

        assert e.value.row_num == 3
        # FIXME: Find a better way to represent this.
        assert (
            e.value.message
            == "Validation error: {'whatsapp_template_category': [\"Value 'Marketing' is not a valid choice.\"]}"
        )


    def test_import_required_fields(self, csv_impexp: ImportExport) -> None:
        """
        Importing an CSV file with only the required feids shoud not break

        """
        
        csv_bytes = csv_impexp.import_file("required_fields_sample.csv")
        content = csv_impexp.export_content()
        src, dst = csv_impexp.csvs2dicts(csv_bytes, content)
        assert dst == src


# "old-xlsx" has at least three bugs, so we don't bother testing it.
@pytest.fixture(params=["old-csv", "new-csv", "new-xlsx"])
def impexp(request: Any, admin_client: Any) -> ImportExport:
    importer, format = request.param.split("-")
    return ImportExport(admin_client, importer, format)


@pytest.fixture(params=["csv", "xlsx"])
def new_impexp(request: Any, admin_client: Any) -> ImportExport:
    return ImportExport(admin_client, "new", request.param)


@pytest.fixture()
def tmp_media_path(tmp_path: Path, settings: SettingsWrapper) -> None:
    settings.MEDIA_ROOT = tmp_path


def mk_img(img_path: Path, title: str) -> Image:
    img = Image(title=title, file=ImageFile(img_path.open("rb"), name=img_path.name))
    img.save()
    return img


@pytest.mark.usefixtures("tmp_media_path")
@pytest.mark.django_db
class TestExportImportRoundtrip:
    """
    Test that the db state after exporting and reimporting content is
    equilavent to what it was before.

    NOTE: This is not a Django (or even unittest) TestCase. It's just a
        container for related tests.
    """

    def test_simple(self, impexp: ImportExport) -> None:
        """
        Exporting and then importing leaves the db in the same state it was
        before, except for page_ids, timestamps, and body item ids.

        FIXME:
         * Determine whether we need to maintain StreamField block ids. (I
           think we don't.)
         * Confirm that there's no meaningful difference between null and ""
           for the nullable fields that the importer sets to "", potentially
           make these fields non-nullable.
        """
        home_page = HomePage.objects.first()
        main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        ha_menu = PageBuilder.build_cp(
            parent=main_menu,
            slug="ha-menu",
            title="HealthAlert menu",
            bodies=[
                WABody("HealthAlert menu", [WABlk("*Welcome to HealthAlert* WA")]),
                SBody("HealthAlert menu", [SBlk("Welcome to HealthAlert S")]),
                MBody("HealthAlert menu", [MBlk("Welcome to HealthAlert M")]),
            ],
        )
        _health_info = PageBuilder.build_cp(
            parent=ha_menu,
            slug="health-info",
            title="health info",
            bodies=[
                WABody("health info", [WABlk("*Health information* WA")]),
                SBody("health info", [SBlk("*Health information* S")]),
                MBody("health info", [MBlk("*Health information* M")]),
            ],
        )
        _self_help = PageBuilder.build_cp(
            parent=ha_menu,
            slug="self-help",
            title="self-help",
            bodies=[
                WABody("self-help", [WABlk("*Self-help programs* WA")]),
                SBody("self-help", [SBlk("*Self-help programs* S")]),
                MBody("self-help", [MBlk("*Self-help programs* M")]),
                VBody("self-help", [VBlk("*Self-help programs* V")]),
            ],
        )

        orig = impexp.get_page_json()
        impexp.export_reimport()
        imported = impexp.get_page_json()
        assert imported == orig

    def test_web_content(self, impexp: ImportExport) -> None:
        """
        ContentPages with web content are preserved across export/import.

        FIXME:
         * The exporter currently emits rendered web content instead of the source data.
        """
        home_page = HomePage.objects.first()
        main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        _ha_menu = PageBuilder.build_cp(
            parent=main_menu,
            slug="ha-menu",
            title="HealthAlert menu",
            bodies=[],
            web_body=["Paragraph 1.", "Paragraph 2."],
        )

        orig = impexp.get_page_json()
        impexp.export_reimport()
        imported = impexp.get_page_json()
        assert imported == orig

    def test_multiple_messages(self, impexp: ImportExport) -> None:
        """
        ContentPages with multiple message blocks are preserved across
        export/import.
        """
        home_page = HomePage.objects.first()
        main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        ha_menu = PageBuilder.build_cp(
            parent=main_menu,
            slug="ha-menu",
            title="HealthAlert menu",
            bodies=[
                WABody("HealthAlert menu", [WABlk("*Welcome to HealthAlert* WA")]),
                SBody("HealthAlert menu", [SBlk("Welcome to HealthAlert S")]),
                MBody("HealthAlert menu", [MBlk("Welcome to HealthAlert M")]),
                VBody("HealthAlert menu", [VBlk("Welcome to HealthAlert V")]),
            ],
        )
        _health_info = PageBuilder.build_cp(
            parent=ha_menu,
            slug="health-info",
            title="health info",
            bodies=[
                WABody("health info", [WABlk(f"wa{i}") for i in [1, 2, 3]]),
                SBody("health info", [SBlk(f"s{i}") for i in [1, 2, 3, 4]]),
                MBody("health info", [MBlk(f"m{i}") for i in [1, 2, 3, 4, 5]]),
                VBody("health info", [VBlk(f"v{i}") for i in [1, 2, 3, 4, 5, 6]]),
            ],
        )

        orig = impexp.get_page_json()
        impexp.export_reimport()
        imported = impexp.get_page_json()
        assert imported == orig

    @pytest.mark.xfail(reason="Image imports are currently broken.")
    def test_images(self, new_impexp: ImportExport) -> None:
        """
        ContentPages with images in multiple message types are preserved across
        export/import.

        NOTE: Old importer can't handle images.
        """
        img_path = Path("home/tests/test_static") / "test.jpeg"
        img_wa = mk_img(img_path, "wa_image")
        img_m = mk_img(img_path, "m_image")
        img_v = mk_img(img_path, "v_image")

        home_page = HomePage.objects.first()
        main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        _ha_menu = PageBuilder.build_cp(
            parent=main_menu,
            slug="ha-menu",
            title="HealthAlert menu",
            bodies=[
                WABody("HA menu", [WABlk("Welcome WA", image=img_wa.id)]),
                MBody("HA menu", [MBlk("Welcome M", image=img_m.id)]),
                VBody("HA menu", [VBlk("Welcome V", image=img_v.id)]),
            ],
        )

        orig = new_impexp.get_page_json()
        new_impexp.export_reimport()
        imported = new_impexp.get_page_json()
        assert imported == orig

    def test_variations(self, impexp: ImportExport) -> None:
        """
        ContentPages with variation messages (and buttons and next prompts) are
        preserved across export/import.

        NOTE: The old importer can't handle multiple restrictions on a
            variation, so it gets a slightly simpler dataset.
        """
        set_profile_field_options()

        home_page = HomePage.objects.first()
        imp_exp = PageBuilder.build_cpi(home_page, "import-export", "Import Export")

        m1vars = [
            VarMsg("Single male", gender="male", relationship="single"),
            VarMsg("Complicated male", gender="male", relationship="complicated"),
        ]
        if impexp.importer == "old":
            m1vars = [
                VarMsg("Single", relationship="single"),
                VarMsg("Complicated", relationship="complicated"),
            ]

        cp_imp_exp_wablks = [
            WABlk(
                "Message 1",
                next_prompt="Next message",
                buttons=[NextBtn("Next message")],
                variation_messages=m1vars,
            ),
            WABlk(
                "Message 2, variable placeholders as well {{0}}",
                buttons=[PageBtn("Import Export", page=imp_exp)],
                variation_messages=[VarMsg("Var'n for Rather not say", gender="empty")],
            ),
            WABlk("Message 3 with no variation", next_prompt="Next message"),
        ]
        cp_imp_exp = PageBuilder.build_cp(
            parent=imp_exp,
            slug="cp-import-export",
            title="CP-Import/export",
            bodies=[WABody("WA import export data", cp_imp_exp_wablks)],
        )
        # Save and publish cp_imp_exp again so the revision numbers match up after import.
        rev = cp_imp_exp.save_revision()
        rev.publish()

        orig = impexp.get_page_json()
        impexp.export_reimport()
        imported = impexp.get_page_json()
        assert imported == orig

    def test_tags_and_related(self, impexp: ImportExport) -> None:
        """
        ContentPages with tags and related pages are preserved across
        export/import.

        NOTE: The old importer can't handle non-ContentPage related pages, so
            it doesn't get one of those.
        """
        home_page = HomePage.objects.first()
        main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        ha_menu = PageBuilder.build_cp(
            parent=main_menu,
            slug="ha-menu",
            title="HealthAlert menu",
            bodies=[
                WABody("HealthAlert menu", [WABlk("*Welcome to HealthAlert* WA")]),
                MBody("HealthAlert menu", [MBlk("Welcome to HealthAlert M")]),
            ],
            tags=["tag1", "tag2"],
        )
        health_info = PageBuilder.build_cp(
            parent=ha_menu,
            slug="health-info",
            title="health info",
            bodies=[MBody("health info", [MBlk("*Health information* M")])],
            tags=["tag2", "tag3"],
        )
        self_help = PageBuilder.build_cp(
            parent=ha_menu,
            slug="self-help",
            title="self-help",
            bodies=[WABody("self-help", [WABlk("*Self-help programs* WA")])],
            tags=["tag4"],
        )
        PageBuilder.link_related(health_info, [self_help])
        if impexp.importer == "old":
            PageBuilder.link_related(self_help, [health_info])
        else:
            PageBuilder.link_related(self_help, [health_info, main_menu])

        orig = impexp.get_page_json()
        impexp.export_reimport()
        imported = impexp.get_page_json()
        assert imported == orig

    def test_triggers_and_quick_replies(self, impexp: ImportExport) -> None:
        """
        ContentPages with triggers and quick replies are preserved across
        export/import.
        """
        home_page = HomePage.objects.first()
        main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        ha_menu = PageBuilder.build_cp(
            parent=main_menu,
            slug="ha-menu",
            title="HealthAlert menu",
            bodies=[
                WABody("HealthAlert menu", [WABlk("*Welcome to HealthAlert* WA")]),
                MBody("HealthAlert menu", [MBlk("Welcome to HealthAlert M")]),
            ],
            triggers=["trigger1", "trigger2"],
        )
        _health_info = PageBuilder.build_cp(
            parent=ha_menu,
            slug="health-info",
            title="health info",
            bodies=[MBody("health info", [MBlk("*Health information* M")])],
            triggers=["trigger2", "trigger3"],
            quick_replies=["button1", "button2"],
        )
        _self_help = PageBuilder.build_cp(
            parent=ha_menu,
            slug="self-help",
            title="self-help",
            bodies=[WABody("self-help", [WABlk("*Self-help programs* WA")])],
            quick_replies=["button3", "button2"],
        )

        orig = impexp.get_page_json()
        impexp.export_reimport()
        imported = impexp.get_page_json()
        assert imported == orig

    def test_whatsapp_template(self, impexp: ImportExport) -> None:
        """
        ContentPages that are whatsapp templates are preserved across
        export/import.
        """
        home_page = HomePage.objects.first()
        main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        ha_menu = PageBuilder.build_cp(
            parent=main_menu,
            slug="ha-menu",
            title="HealthAlert menu",
            bodies=[WABody("HealthAlert menu", [WABlk("*Welcome to HealthAlert* WA")])],
        )
        _health_info = PageBuilder.build_cp(
            parent=ha_menu,
            slug="health-info",
            title="health info",
            bodies=[WABody("health info", [WABlk("*Health information* WA")])],
            whatsapp_template_name="template-health-info",
        )

        orig = impexp.get_page_json()
        impexp.export_reimport()
        imported = impexp.get_page_json()
        assert imported == orig

    def test_translations(self, new_impexp: ImportExport) -> None:
        """
        ContentPages in multiple languages (with unique-per-locale slugs and
        titles) are preserved across export/import.

        NOTE: Old importer can't handle non-unique slugs.
        """
        # Create a new homepage for Portuguese.
        pt, _created = Locale.objects.get_or_create(language_code="pt")
        HomePage.add_root(locale=pt, title="Home (pt)", slug="home-pt")

        # NOTE: For the results to match without a bunch of work reordering
        # pages and juggling ids, we need all CPIs to be created before all
        # CPs.

        # English CPIs
        home_en = HomePage.objects.get(locale__language_code="en")
        _app_rem = PageBuilder.build_cpi(
            parent=home_en, slug="appointment-reminders", title="Appointment reminders"
        )
        _sbm = PageBuilder.build_cpi(
            parent=home_en, slug="stage-based-messages", title="Stage-based messages"
        )
        _him = PageBuilder.build_cpi(
            parent=home_en, slug="health-info-messages", title="Health info messages"
        )
        _wtt = PageBuilder.build_cpi(
            parent=home_en,
            slug="whatsapp-template-testing",
            title="whatsapp template testing",
        )
        imp_exp = PageBuilder.build_cpi(
            parent=home_en, slug="import-export", title="Import Export"
        )

        # Portuguese CPIs
        home_pt = HomePage.objects.get(locale__language_code="pt")
        imp_exp_pt = PageBuilder.build_cpi(
            parent=home_pt,
            slug="import-export",
            title="Import Export (pt)",
            translated_from=imp_exp,
        )

        # English CPs
        non_templ_wablks = [
            WABlk("this is a non template message"),
            WABlk("this message has a doc"),
            WABlk("this message comes with audio"),
        ]
        non_tmpl = PageBuilder.build_cp(
            parent=imp_exp,
            slug="non-template",
            title="Non template messages",
            bodies=[WABody("non template OCS", non_templ_wablks)],
        )

        # Portuguese CPs
        non_templ_wablks_pt = [
            WABlk("this is a non template message (pt)"),
            WABlk("this message has a doc (pt)"),
            WABlk("this message comes with audio (pt)"),
        ]
        non_tmpl_pt = PageBuilder.build_cp(
            parent=imp_exp_pt,
            slug="non-template",
            title="Non template messages",
            bodies=[WABody("non template OCS", non_templ_wablks_pt)],
            translated_from=non_tmpl,
        )

        assert imp_exp.translation_key == imp_exp_pt.translation_key
        assert non_tmpl.translation_key == non_tmpl_pt.translation_key

        orig = new_impexp.get_page_json()
        new_impexp.export_reimport()
        imported = new_impexp.get_page_json()
        assert imported == orig

    def test_translations_sep(self, impexp: ImportExport) -> None:
        """
        ContentPages in multiple languages (with globally-unique slugs and titles) are
        preserved across export/import with each language imported separately.
        """
        # Create a new homepage for Portuguese.
        pt, _created = Locale.objects.get_or_create(language_code="pt")
        HomePage.add_root(locale=pt, title="Home (pt)", slug="home-pt")

        # English pages
        home_en = HomePage.objects.get(locale__language_code="en")
        _app_rem = PageBuilder.build_cpi(
            parent=home_en, slug="appointment-reminders", title="Appointment reminders"
        )
        _sbm = PageBuilder.build_cpi(
            parent=home_en, slug="stage-based-messages", title="Stage-based messages"
        )
        _him = PageBuilder.build_cpi(
            parent=home_en, slug="health-info-messages", title="Health info messages"
        )
        _wtt = PageBuilder.build_cpi(
            parent=home_en,
            slug="whatsapp-template-testing",
            title="whatsapp template testing",
        )
        imp_exp = PageBuilder.build_cpi(
            parent=home_en, slug="import-export", title="Import Export"
        )
        non_templ_wablks = [
            WABlk("this is a non template message"),
            WABlk("this message has a doc"),
            WABlk("this message comes with audio"),
        ]
        non_tmpl = PageBuilder.build_cp(
            parent=imp_exp,
            slug="non-template",
            title="Non template messages",
            bodies=[WABody("non template OCS", non_templ_wablks)],
        )

        # Portuguese pages
        home_pt = HomePage.objects.get(locale__language_code="pt")
        imp_exp_pt = PageBuilder.build_cpi(
            parent=home_pt,
            slug="import-export-pt",
            title="Import Export (pt)",
            translated_from=imp_exp,
        )
        non_templ_wablks_pt = [
            WABlk("this is a non template message (pt)"),
            WABlk("this message has a doc (pt)"),
            WABlk("this message comes with audio (pt)"),
        ]
        non_tmpl_pt = PageBuilder.build_cp(
            parent=imp_exp_pt,
            slug="non-template-pt",
            title="Non template messages",
            bodies=[WABody("non template OCS", non_templ_wablks_pt)],
            translated_from=non_tmpl,
        )

        assert imp_exp.translation_key == imp_exp_pt.translation_key
        assert non_tmpl.translation_key == non_tmpl_pt.translation_key

        orig = impexp.get_page_json()
        content_en = impexp.export_content(locale="en")
        content_pt = impexp.export_content(locale="pt")

        impexp.import_content(content_en, locale="en")
        impexp.import_content(content_pt, locale="pt", purge=False)
        imported = impexp.get_page_json()
        assert imported == orig

    def test_translations_split(self, new_impexp: ImportExport) -> None:
        """
        ContentPages in multiple languages (with unique-per-locale slugs and
        titles) are preserved across export/import with each language imported
        separately.

        NOTE: Old importer can't handle non-unique slugs.
        """
        # Create a new homepage for Portuguese.
        pt, _created = Locale.objects.get_or_create(language_code="pt")
        HomePage.add_root(locale=pt, title="Home (pt)", slug="home-pt")

        # English pages
        home_en = HomePage.objects.get(locale__language_code="en")
        _app_rem = PageBuilder.build_cpi(
            parent=home_en, slug="appointment-reminders", title="Appointment reminders"
        )
        _sbm = PageBuilder.build_cpi(
            parent=home_en, slug="stage-based-messages", title="Stage-based messages"
        )
        _him = PageBuilder.build_cpi(
            parent=home_en, slug="health-info-messages", title="Health info messages"
        )
        _wtt = PageBuilder.build_cpi(
            parent=home_en,
            slug="whatsapp-template-testing",
            title="whatsapp template testing",
        )
        imp_exp = PageBuilder.build_cpi(
            parent=home_en, slug="import-export", title="Import Export"
        )
        non_templ_wablks = [
            WABlk("this is a non template message"),
            WABlk("this message has a doc"),
            WABlk("this message comes with audio"),
        ]
        non_tmpl = PageBuilder.build_cp(
            parent=imp_exp,
            slug="non-template",
            title="Non template messages",
            bodies=[WABody("non template OCS", non_templ_wablks)],
        )

        # Portuguese pages
        home_pt = HomePage.objects.get(locale__language_code="pt")
        imp_exp_pt = PageBuilder.build_cpi(
            parent=home_pt,
            slug="import-export",
            title="Import Export (pt)",
            translated_from=imp_exp,
        )
        non_templ_wablks_pt = [
            WABlk("this is a non template message (pt)"),
            WABlk("this message has a doc (pt)"),
            WABlk("this message comes with audio (pt)"),
        ]
        non_tmpl_pt = PageBuilder.build_cp(
            parent=imp_exp_pt,
            slug="non-template",
            title="Non template messages",
            bodies=[WABody("non template OCS", non_templ_wablks_pt)],
            translated_from=non_tmpl,
        )

        assert imp_exp.translation_key == imp_exp_pt.translation_key
        assert non_tmpl.translation_key == non_tmpl_pt.translation_key

        orig = new_impexp.get_page_json()
        content_en = new_impexp.export_content(locale="en")
        content_pt = new_impexp.export_content(locale="pt")

        new_impexp.import_content(content_en, locale="en")
        new_impexp.import_content(content_pt, locale="pt", purge=False)
        imported = new_impexp.get_page_json()
        assert imported == orig

    def test_translations_en(self, new_impexp: ImportExport) -> None:
        """
        ContentPages in multiple languages are that are imported with a locale
        specified have pages in that locale preserved and all other locales are
        removed.

        NOTE: Old importer can't handle multiple languages at once.
        """
        # Create a new homepage for Portuguese.
        pt, _created = Locale.objects.get_or_create(language_code="pt")
        HomePage.add_root(locale=pt, title="Home (pt)", slug="home-pt")

        # English pages
        home_en = HomePage.objects.get(locale__language_code="en")
        _app_rem = PageBuilder.build_cpi(
            parent=home_en, slug="appointment-reminders", title="Appointment reminders"
        )
        _sbm = PageBuilder.build_cpi(
            parent=home_en, slug="stage-based-messages", title="Stage-based messages"
        )
        _him = PageBuilder.build_cpi(
            parent=home_en, slug="health-info-messages", title="Health info messages"
        )
        _wtt = PageBuilder.build_cpi(
            parent=home_en,
            slug="whatsapp-template-testing",
            title="whatsapp template testing",
        )
        imp_exp = PageBuilder.build_cpi(
            parent=home_en, slug="import-export", title="Import Export"
        )
        non_templ_wablks = [
            WABlk("this is a non template message"),
            WABlk("this message has a doc"),
            WABlk("this message comes with audio"),
        ]
        non_tmpl = PageBuilder.build_cp(
            parent=imp_exp,
            slug="non-template",
            title="Non template messages",
            bodies=[WABody("non template OCS", non_templ_wablks)],
        )

        # Portuguese pages
        home_pt = HomePage.objects.get(locale__language_code="pt")
        imp_exp_pt = PageBuilder.build_cpi(
            parent=home_pt,
            slug="import-export-pt",
            title="Import Export (pt)",
            translated_from=imp_exp,
        )
        non_templ_wablks_pt = [
            WABlk("this is a non template message (pt)"),
            WABlk("this message has a doc (pt)"),
            WABlk("this message comes with audio (pt)"),
        ]
        non_tmpl_pt = PageBuilder.build_cp(
            parent=imp_exp_pt,
            slug="non-template-pt",
            title="Non template messages",
            bodies=[WABody("non template OCS", non_templ_wablks_pt)],
            translated_from=non_tmpl,
        )

        assert imp_exp.translation_key == imp_exp_pt.translation_key
        assert non_tmpl.translation_key == non_tmpl_pt.translation_key

        orig_en = new_impexp.get_page_json(locale="en")
        content = new_impexp.export_content()

        new_impexp.import_content(content, locale="en")
        imported = new_impexp.get_page_json()
        assert imported == orig_en

    def test_example_values(self, new_impexp: ImportExport) -> None:
        """
        ContentPages with example values in whatsapp messages are preserved
        across export/import.

        NOTE: Old importer can't handle example values.
        """
        home_page = HomePage.objects.first()
        main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")

        ha_menu = PageBuilder.build_cp(
            parent=main_menu,
            slug="ha-menu",
            title="HealthAlert menu",
            bodies=[WABody("HealthAlert menu", [WABlk("*Welcome to HealthAlert* WA")])],
        )

        example_values = ["Example value 1", "Example value 2"]
        _health_info = PageBuilder.build_cp(
            parent=ha_menu,
            slug="health-info",
            title="health info",
            bodies=[
                WABody(
                    "health info",
                    [WABlk("*Health information* WA", example_values=example_values)],
                )
            ],
            whatsapp_template_name="template-health-info",
        )

        orig = new_impexp.get_page_json()
        new_impexp.export_reimport()
        imported = new_impexp.get_page_json()
        assert imported == orig

    def test_export_missing_related_page(self, impexp: ImportExport) -> None:
        """
        If a page has a related page that no longer exists, the missing related
        page is skipped during export.
        """
        home_page = HomePage.objects.first()
        main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        ha_menu = PageBuilder.build_cp(
            parent=main_menu,
            slug="ha-menu",
            title="HealthAlert menu",
            bodies=[WABody("HealthAlert menu", [WABlk("*Welcome to HealthAlert*")])],
        )
        health_info = PageBuilder.build_cp(
            parent=ha_menu,
            slug="health-info",
            title="health info",
            bodies=[WABody("health info", [WABlk("*Health information*")])],
        )
        self_help = PageBuilder.build_cp(
            parent=ha_menu,
            slug="self-help",
            title="self-help",
            bodies=[WABody("self-help", [WABlk("*Self-help programs*")])],
        )
        health_info = PageBuilder.link_related(health_info, [self_help])
        # This is what we expect to see after export/import, so we fetch the
        # JSON to compare with before adding the missing related page.
        orig_without_self_help = impexp.get_page_json()

        move_along = PageBuilder.build_cp(
            parent=ha_menu,
            slug="move-along",
            title="move-along",
            bodies=[WABody("move along", [WABlk("*Nothing to see here*")])],
        )
        PageBuilder.link_related(health_info, [move_along])
        move_along.delete()

        # Ideally, all related page links would be removed when the page they
        # link to is deleted. We don't currently do that, so for now we just
        # make sure that we skip such links during export.
        sh_page = Page.objects.get(pk=self_help.id)
        assert [rp.value for rp in health_info.related_pages] == [sh_page, None]

        impexp.export_reimport()
        imported = impexp.get_page_json()
        assert imported == orig_without_self_help

    def test_ussd_values(self, new_impexp: ImportExport) -> None:
        """
        ContentPages with USSD messages are preserved
        across export/import.

        NOTE: Old importer can't handle USSD values.
        """
        home_page = HomePage.objects.first()
        main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")

        PageBuilder.build_cp(
            parent=main_menu,
            slug="ha-menu",
            title="HealthAlert menu",
            bodies=[UBody("HealthAlert menu", [UBlk("*Welcome to HealthAlert* USSD")])],
        )

        orig = new_impexp.get_page_json()
        new_impexp.export_reimport()
        imported = new_impexp.get_page_json()
        assert imported == orig

    def test_sms_values(self, new_impexp: ImportExport) -> None:
        """
        ContentPages with SMS messages are preserved
        across export/import.

        NOTE: Old importer can't handle SMS values.
        """
        home_page = HomePage.objects.first()
        main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")

        PageBuilder.build_cp(
            parent=main_menu,
            slug="ha-menu",
            title="HealthAlert menu",
            bodies=[SBody("HealthAlert menu", [SBlk("*Welcome to HealthAlert* SMS")])],
        )

        orig = new_impexp.get_page_json()
        new_impexp.export_reimport()
        imported = new_impexp.get_page_json()
        assert imported == orig
