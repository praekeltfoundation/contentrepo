import csv
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from functools import wraps
from io import BytesIO, StringIO
from pathlib import Path
from queue import Queue
from typing import Any

import pytest
from openpyxl import load_workbook
from pytest_django.fixtures import SettingsWrapper
from wagtail.models import Locale  # type: ignore

from home.whatsapp_template_import_export import import_whatsapptemplate
from home.import_whatsapp_templates import ImportWhatsAppTemplateException
from home.models import (
    HomePage,
    WhatsAppTemplate,
)

from .page_builder import (
    MBlk,
    MBody,
    PageBuilder,
    WABlk,
    WABody,
)

IMP_EXP_DATA_BASE = Path("home/tests/import-export-data")

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
def strip_leading_whitespace(entry: ExpDict) -> ExpDict:
    # FIXME: Do we expect imported content to have leading spaces removed?
    bodies = {k: v.lstrip(" ") for k, v in entry.items() if k.endswith("_body")}
    return {**entry, **bodies}


EXPORT_FILTER_FUNCS = [
    # add_new_fields,
    # ignore_certain_fields,
    strip_leading_whitespace,
]


def filter_exports(srcs: ExpDicts, dsts: ExpDicts) -> ExpDictsPair:
    fsrcs, fdsts = [], []
    for src, dst in zip(srcs, dsts, strict=True):
        for ff in EXPORT_FILTER_FUNCS:
            src, dst = ff(src, dst)
        fsrcs.append(src)
        fdsts.append(dst)
    return fsrcs, fdsts


def csv2dicts(csv_bytes: bytes) -> ExpDicts:
    return list(csv.DictReader(StringIO(csv_bytes.decode())))


WEB_PARA_RE = re.compile(r'^<div class="block-paragraph">(.*)</div>$')


@dataclass
class ImportExport:
    admin_client: Any
    format: str

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

    def export_whatsapp_template(self, locale: str | None = None) -> bytes:
        """
        Export all (or filtered) content in the configured format.

        FIXME:
         * If we filter the export by locale, we only get ContentPage entries
           for the given language, but we still get ContentPageIndex rows for
           all languages.
        """
        url = f"/admin/snippets/home/whatsapptemplate/?export={self.format}"
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

    def import_whatsapp_template(self, content_bytes: bytes, **kw: Any) -> None:
        """
        Import given content in the configured format with the configured importer.
        """
        import_whatsapptemplate(BytesIO(content_bytes), self.format.upper(), Queue(), **kw)

    def read_bytes(self, path_str: str, path_base: Path = IMP_EXP_DATA_BASE) -> bytes:
        return (path_base / path_str).read_bytes()

    def import_file(
        self, path_str: str, path_base: Path = IMP_EXP_DATA_BASE, **kw: Any
    ) -> bytes:
        """
        Import given content file in the configured format with the configured importer.
        """
        content = self.read_bytes(path_str, path_base)
        self.import_whatsapp_template(content, **kw)
        return content

    def export_reimport(self) -> None:
        """
        Export all content, then immediately reimport it.
        """
        self.import_whatsapp_template(self.export_whatsapp_template())

    def csvs2dicts(self, src_bytes: bytes, dst_bytes: bytes) -> ExpDictsPair:
        src = csv2dicts(src_bytes)
        dst = csv2dicts(dst_bytes)
        return filter_exports(src, dst)


@pytest.fixture(params=["csv", "xlsx"])
def impexp(request: Any, admin_client: Any) -> ImportExport:
    return ImportExport(admin_client, request.param)


@pytest.fixture()
def tmp_media_path(tmp_path: Path, settings: SettingsWrapper) -> None:
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture()
def csv_impexp(request: Any, admin_client: Any) -> ImportExport:
    return ImportExport(admin_client, "csv")


@pytest.fixture()
def xlsx_impexp(request: Any, admin_client: Any) -> ImportExport:
    return ImportExport(admin_client, "xlsx")


@pytest.mark.django_db()
class TestImportExportRoundtrip:
    """
    Test importing and reexporting content produces an export that is
    equilavent to the original imported content.

    NOTE: This is not a Django (or even unittest) TestCase. It's just a
        container for related tests.
    """

    def test_simple(self, csv_impexp: ImportExport) -> None:
        """
        Importing a simple CSV file with one whatsapp template and
        one question and export it

        (This uses whatsapp_template_simple.csv.)

        """

        home_page = HomePage.objects.first()
        main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        PageBuilder.build_cp(
            parent=main_menu,
            slug="high-inflection",
            title="High Inflection",
            bodies=[
                WABody("High Inflection", [WABlk("*High Inflection Page")]),
                MBody("High inflection", [MBlk("High Inflection Page")]),
            ],
        )
        PageBuilder.build_cp(
            parent=main_menu,
            slug="medium-score",
            title="Medium Score",
            bodies=[
                WABody("Medium Score", [WABlk("*Medium Inflection Page")]),
                MBody("Medium Score", [MBlk("Medium Inflection Page")]),
            ],
        )

        PageBuilder.build_cp(
            parent=main_menu,
            slug="low-score",
            title="Low Score",
            bodies=[
                WABody("Low Score", [WABlk("*Low Inflection Page")]),
                MBody("Low Score", [MBlk("Low Inflection Page")]),
            ],
        )

        csv_bytes = csv_impexp.import_file("whatsapp_template_simple.csv")
        content = csv_impexp.export_whatsapp_template()
        src, dst = csv_impexp.csvs2dicts(csv_bytes, content)
        assert dst == src

    def test_less_simple_multiple_questions(self, csv_impexp: ImportExport) -> None:
        """
        Importing a simple CSV file with two whatsapp templates and
        multiple questions and export it

        (This uses whatsapp_template_less_simple.csv.)

        """

        home_page = HomePage.objects.first()
        main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        PageBuilder.build_cp(
            parent=main_menu,
            slug="high-inflection",
            title="High Inflection",
            bodies=[
                WABody("High Inflection", [WABlk("*High Inflection Page")]),
                MBody("High inflection", [MBlk("High Inflection Page")]),
            ],
        )
        PageBuilder.build_cp(
            parent=main_menu,
            slug="medium-score",
            title="Medium Score",
            bodies=[
                WABody("Medium Score", [WABlk("*Medium Inflection Page")]),
                MBody("Medium Score", [MBlk("Medium Inflection Page")]),
            ],
        )

        PageBuilder.build_cp(
            parent=main_menu,
            slug="low-score",
            title="Low Score",
            bodies=[
                WABody("Low Score", [WABlk("*Low Inflection Page")]),
                MBody("Low Score", [MBlk("Low Inflection Page")]),
            ],
        )

        csv_bytes = csv_impexp.import_file("whatsapp_template_less_simple.csv")
        content = csv_impexp.export_whatsapp_template()
        src, dst = csv_impexp.csvs2dicts(csv_bytes, content)
        assert dst == src

    def test_multiple_whatsapp_templates(self, csv_impexp: ImportExport) -> None:
        """
        Importing a simple CSV file with more than one whatsapp template and
        multiple questions and export it

        (This uses multiple_whatsapp_templates.csv.)

        """

        home_page = HomePage.objects.first()
        main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        PageBuilder.build_cp(
            parent=main_menu,
            slug="high-inflection",
            title="High Inflection",
            bodies=[
                WABody("High Inflection", [WABlk("*High Inflection Page")]),
                MBody("High inflection", [MBlk("High Inflection Page")]),
            ],
        )
        PageBuilder.build_cp(
            parent=main_menu,
            slug="medium-score",
            title="Medium Score",
            bodies=[
                WABody("Medium Score", [WABlk("*Medium Inflection Page")]),
                MBody("Medium Score", [MBlk("Medium Inflection Page")]),
            ],
        )

        PageBuilder.build_cp(
            parent=main_menu,
            slug="low-score",
            title="Low Score",
            bodies=[
                WABody("Low Score", [WABlk("*Low Inflection Page")]),
                MBody("Low Score", [MBlk("Low Inflection Page")]),
            ],
        )

        csv_bytes = csv_impexp.import_file("multiple_whatsapp_templates.csv")
        content = csv_impexp.export_whatsapp_template()
        src, dst = csv_impexp.csvs2dicts(csv_bytes, content)
        assert dst == src

    def test_bulk_whatsapp_templates(self, csv_impexp: ImportExport) -> None:
        """
        Importing a simple CSV file with more than five whatsapp templates and
        multiple questions and export it

        (This uses bulk_whatsapp_templates.csv.)

        """

        home_page = HomePage.objects.first()
        main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        PageBuilder.build_cp(
            parent=main_menu,
            slug="high-inflection",
            title="High Inflection",
            bodies=[
                WABody("High Inflection", [WABlk("*High Inflection Page")]),
                MBody("High inflection", [MBlk("High Inflection Page")]),
            ],
        )
        PageBuilder.build_cp(
            parent=main_menu,
            slug="medium-score",
            title="Medium Score",
            bodies=[
                WABody("Medium Score", [WABlk("*Medium Inflection Page")]),
                MBody("Medium Score", [MBlk("Medium Inflection Page")]),
            ],
        )

        PageBuilder.build_cp(
            parent=main_menu,
            slug="low-score",
            title="Low Score",
            bodies=[
                WABody("Low Score", [WABlk("*Low Inflection Page")]),
                MBody("Low Score", [MBlk("Low Inflection Page")]),
            ],
        )

        csv_bytes = csv_impexp.import_file("bulk_whatsapp_templates.csv")
        content = csv_impexp.export_whatsapp_template()
        src, dst = csv_impexp.csvs2dicts(csv_bytes, content)
        assert dst == src

    def test_comma_separated_answers(self, csv_impexp: ImportExport) -> None:
        """
        Importing a CSV file with multiple whatsapp templates. Some with comma
        separated answers and some without commas.

        (This uses comma_sep_whatsapp_templates.csv.)

        """

        home_page = HomePage.objects.first()
        main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        PageBuilder.build_cp(
            parent=main_menu,
            slug="high-inflection",
            title="High Inflection",
            bodies=[
                WABody("High Inflection", [WABlk("*High Inflection Page")]),
                MBody("High inflection", [MBlk("High Inflection Page")]),
            ],
        )
        PageBuilder.build_cp(
            parent=main_menu,
            slug="medium-score",
            title="Medium Score",
            bodies=[
                WABody("Medium Score", [WABlk("*Medium Inflection Page")]),
                MBody("Medium Score", [MBlk("Medium Inflection Page")]),
            ],
        )

        PageBuilder.build_cp(
            parent=main_menu,
            slug="low-score",
            title="Low Score",
            bodies=[
                WABody("Low Score", [WABlk("*Low Inflection Page")]),
                MBody("Low Score", [MBlk("Low Inflection Page")]),
            ],
        )

        csv_bytes = csv_impexp.import_file("comma_separated_answers.csv")
        content = csv_impexp.export_whatsapp_template()
        src, dst = csv_impexp.csvs2dicts(csv_bytes, content)
        assert dst == src


@pytest.mark.django_db()
class TestImportExport:
    """
    Test import and export scenarios that aren't specifically round
    trips.
    """



    def test_import_error(elf, csv_impexp: ImportExport) -> None:
        """
        Importing an invalid CSV file leaves the db as-is.
        """

        home_page = HomePage.objects.first()
        main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        PageBuilder.build_cp(
            parent=main_menu,
            slug="high-inflection",
            title="High Inflection",
            bodies=[
                WABody("High Inflection", [WABlk("*High Inflection Page")]),
                MBody("High inflection", [MBlk("High Inflection Page")]),
            ],
        )
        PageBuilder.build_cp(
            parent=main_menu,
            slug="medium-score",
            title="Medium Score",
            bodies=[
                WABody("Medium Score", [WABlk("*Medium Inflection Page")]),
                MBody("Medium Score", [MBlk("Medium Inflection Page")]),
            ],
        )

        PageBuilder.build_cp(
            parent=main_menu,
            slug="low-score",
            title="Low Score",
            bodies=[
                WABody("Low Score", [WABlk("*Low Inflection Page")]),
                MBody("Low Score", [MBlk("Low Inflection Page")]),
            ],
        )
        csv_bytes = csv_impexp.import_file("whatsapp_template_simple.csv")
        with pytest.raises(ImportWhatsAppTemplateException) as e:
            csv_impexp.import_file("broken_whatsapp_template.csv")
        assert e.value.message == "The import file is missing some required fields."
        content = csv_impexp.export_whatsapp_template()
        src, dst = csv_impexp.csvs2dicts(csv_bytes, content)
        assert dst == src

    def test_invalid_locale_code(self, csv_impexp: ImportExport) -> None:
        """
        Importing whatsapp templates with invalid locale code should raise an error that results
        in an error message that gets sent back to the user
        """
        with pytest.raises(ImportWhatsAppTemplateException) as e:
            csv_impexp.import_file("invalid-whatsapp_template-locale-name.csv")

        assert e.value.row_num == 2
        assert e.value.message == "Language code not found: fakecode"



class TemplateBuilder():
    """
    Builder for various Template objects.

    """
    template: WhatsAppTemplate

    @classmethod
    def cp(cls, slug: str, title: str) -> "TemplateBuilder[WhatsAppTemplate]":
        return cls(title, page_type=WhatsAppTemplate)



    # @classmethod
    # def build_whatsapp_template(
    #     cls,
    #     name: str,
    #     category: str,
    #     quick_replies: str,
    #     locale: str,
    #     message: str,
    #     example_values: str,
    #     submission_status: str,
    #     submission_result: str,
    #     submission_name: str,git
       
    #     publish: bool = True,
    # ) -> WhatsAppTemplate:
    #     builder = cls.cp(parent, slug, title).add_bodies(*bodies)
    #     if web_body:
    #         builder = builder.add_web_body(*web_body)
    #     if tags:
    #         builder = builder.add_tags(*tags)
    #     if triggers:
    #         builder = builder.add_triggers(*triggers)
    #     if quick_replies:
    #         builder = builder.add_quick_replies(*quick_replies)
    #     if whatsapp_template_name:
    #         builder = builder.set_whatsapp_template_name(whatsapp_template_name)
    #     if whatsapp_template_category:
    #         builder = builder.set_whatsapp_template_category(whatsapp_template_category)
    #     if translated_from:
    #         builder = builder.translated_from(translated_from)
    #     return builder.build(publish=publish)

    # def build(self, publish: bool = True) -> TPage:
    #     self.parent.add_child(instance=self.page)
    #     rev = self.page.save_revision()
    #     if publish:
    #         rev.publish()
    #     else:
    #         self.page.unpublish()
    #     # The page instance is out of date after revision operations, so reload.
    #     self.page.refresh_from_db()
    #     return self.page

    # def add_web_body(self, *paragraphs: str) -> "PageBuilder[TPage]":
    #     # TODO: Support images?
    #     self.page.enable_web = True
    #     for paragraph in paragraphs:
    #         self.page.body.append(("paragraph", RichTextBlock().to_python(paragraph)))
    #     return self

    # def add_bodies(self, *bodies: ContentBody[TCBlk]) -> "PageBuilder[TPage]":
    #     for body in bodies:
    #         body.set_on(self.page)
    #     return self

    # def add_tags(self, *tag_strs: str) -> "PageBuilder[TPage]":
    #     for tag_str in tag_strs:
    #         tag, _ = Tag.objects.get_or_create(name=tag_str)
    #         self.page.tags.add(tag)
    #     return self

    # def add_triggers(self, *trigger_strs: str) -> "PageBuilder[TPage]":
    #     for trigger_str in trigger_strs:
    #         trigger, _ = ContentTrigger.objects.get_or_create(name=trigger_str)
    #         self.page.triggers.add(trigger)
    #     return self

    # def add_quick_replies(self, *qr_strs: str) -> "PageBuilder[TPage]":
    #     for qr_str in qr_strs:
    #         qr, _ = ContentQuickReply.objects.get_or_create(name=qr_str)
    #         self.page.quick_replies.add(qr)
    #     return self

    # def set_whatsapp_template_name(self, name: str) -> "PageBuilder[TPage]":
    #     self.page.is_whatsapp_template = True
    #     self.page.whatsapp_template_name = name
    #     return self

    # def set_category(self, category: str) -> "PageBuilder[TPage]":
        
    #     self.page.whatsapp_template_category = category
    #     return self


