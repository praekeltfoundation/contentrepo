import csv
from dataclasses import dataclass, fields
from datetime import datetime
from io import BytesIO, StringIO
from queue import Queue

from openpyxl import load_workbook
from wagtail.coreutils import get_content_languages  # type: ignore
from wagtail.models import Locale  # type: ignore
from wagtail.models.sites import Site  # type: ignore

from home.models import WhatsAppTemplate  # type: ignore

PageId = tuple[str, Locale]


class ImportWhatsAppTemplateException(Exception):
    """
    Base exception for all import related issues.
    """

    def __init__(self, message: str, row_num: int | None = None):
        self.row_num = row_num
        self.message = message
        super().__init__()


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

    def locale_from_language_code(self, lang_code_entry: str) -> Locale:
        if lang_code_entry not in self.locale_map:
            codes = []
            lang_name = ""
            for lang_code, lang_dn in get_content_languages().items():
                if lang_code == lang_code_entry:
                    lang_name = lang_dn
                    codes.append(lang_code)
            if not codes:
                raise ImportWhatsAppTemplateException(
                    f"Language code not found: {lang_code_entry}"
                )
            if len(codes) > 1:
                raise ImportWhatsAppTemplateException(
                    f"Multiple codes for language: {lang_name} -> {codes}"
                )
            self.locale_map[lang_code_entry] = Locale.objects.get(
                language_code=codes[0]
            )
        return self.locale_map[lang_code_entry]

    def perform_import(self) -> None:
        rows = self.parse_file()
        self.set_progress("Loaded file", 5)

        if self.purge:
            self.delete_existing_content()
        self.set_progress("Deleted existing WhatsApp Template", 10)

        self.process_rows(rows)
        # self.save_pages_assessment()

    def process_rows(self, rows: list["ContentRow"]) -> None:
        for i, row in enumerate(rows, start=2):
            try:
                print(row)
                # self.create_shadow_assessment_page_from_row(row, i)
            except ImportWhatsAppTemplateException as e:
                e.row_num = i
                raise e

    # def save_pages_assessment(self) -> None:
    #     for i, page in enumerate(reversed(self.shadow_pages.values())):
    #         parent = self.home_page(page.locale)
    #         page.save(parent)
    #         self.set_progress("Importing pages", 10 + 70 * i // len(self.shadow_pages))

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
        # page_id_rows = group_rows_by_page_id(rows)
        return rows

    def parse_csv(self) -> list["ContentRow"]:
        reader = csv.DictReader(StringIO(self.file_content.decode()))
        rows = [ContentRow.from_flat(row) for row in reader]
        # page_id_rows = group_rows_by_page_id(rows)
        return rows

    def set_progress(self, message: str, progress: int) -> None:
        self.progress_queue.put_nowait(progress)

    def delete_existing_content(self) -> None:
        WhatsAppTemplate.objects.all().delete()

    def default_locale(self) -> Locale:
        site = Site.objects.get(is_default_site=True)
        return site.root_page.locale


@dataclass(slots=True, frozen=True)
class ContentRow:
    template_id: int | None = None
    name: str = ""
    category: str = ""
    # locale: str = ""
    # quick_replies: list[str] = field(default_factory=list)
    # image_link: str = ""
    # message: str = ""
    # example_values: list[str] = field(default_factory=list)
    # submission_name: str = ""
    # submission_status: str = ""
    # submission_result: str = ""

    @classmethod
    def from_flat(cls, row: dict[str, str]) -> "ContentRow":
        class_fields = {field.name for field in fields(cls)}
        row = {
            key.strip(): value.strip()
            for key, value in row.items()
            if value and key in class_fields
        }
        return cls(
            template_id=int(row.pop("template_id")) if row.get("template_id") else None,
            name=str(row.pop("name", "")),
            category=str(row.pop("category", "")),
            # quick_replies=deserialise_list(row.pop("quick_replies", "")),
            # triggers=deserialise_list(row.pop("triggers", "")),
            # related_pages=deserialise_list(row.pop("related_pages", "")),
            # example_values=deserialise_list(row.pop("example_values", "")),
            # buttons=json.loads(row.pop("buttons", "")) if row.get("buttons") else [],
            # list_items=deserialise_list(row.pop("list_items", "")),
            # footer=row.pop("footer") if row.get("footer") else "",
            **row,
        )


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
