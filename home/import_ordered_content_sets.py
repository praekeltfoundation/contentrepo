import itertools
import re
from dataclasses import dataclass
from logging import getLogger
from queue import Queue

from django.core.files.base import File  # type: ignore
from wagtail.admin.panels import get_edit_handler  # type: ignore
from wagtail.models import Locale  # type: ignore

from home.import_helpers import ImportException, parse_file, validate_using_form
from home.models import ContentPage, OrderedContentSet

logger = getLogger(__name__)


@dataclass
class OrderedContentSetPage:
    time: str
    unit: str
    before_or_after: str
    page_slug: str
    contact_field: str
    locale: str


class OrderedContentSetImporter:
    def __init__(
        self,
        file: File,  # type: ignore
        file_type: str,
        progress_queue: Queue[int],
    ):
        """
        Initialize an instance of OrderedContentSetImporter.

        :param file: The file to be imported, as a django.core.files.base.File.
        :param file_type: The type of the file, e.g. 'CSV' or 'XLSX'.
        :param progress_queue: A queue.Queue to put progress information on.
        """
        self.file = file
        self.filetype = file_type
        self.progress_queue = progress_queue

    @staticmethod
    def _normalize_row(row: dict[str, str]) -> dict[str, str]:
        """
        Normalize row keys to support both old Title Case and new lowercase formats.

        :param row: The row with potentially Title Case headers
        :return: The row with lowercase_with_underscores headers
        """
        normalized = {}
        for key, value in row.items():
            # Replace non-word characters with underscores, strip, and lowercase
            normalized_key = re.sub(r"\W+", "_", key.strip()).lower().strip("_")
            normalized[normalized_key] = value
        return normalized

    def _get_or_init_ordered_content_set(
        self, index: int, row: dict[str, str], set_slug: str, set_locale: str
    ) -> OrderedContentSet:
        """
        Get or initialize an instance of OrderedContentSet from a row of a CSV file.

        :param row: The row of the CSV file, as a dict.
        :param set_slug: The slug of the ordered content set.
        :param set_locale: The locale of the ordered content set.
        :return: An instance of OrderedContentSet.
        """
        try:
            locale = Locale.objects.get(language_code=set_locale)
            ordered_set = OrderedContentSet.objects.filter(
                slug=set_slug, locale=locale
            ).first()
            if not ordered_set:
                ordered_set = OrderedContentSet(slug=set_slug, locale=locale)

            return ordered_set
        except Locale.DoesNotExist:
            if set_locale:
                raise ImportException(f"Locale {set_locale} does not exist.", index)
            raise ImportException("No locale specified.", index)

    def _add_profile_fields(
        self, ordered_set: OrderedContentSet, row: dict[str, str]
    ) -> None:
        """
        Add profile fields to an instance of OrderedContentSet from a row of a CSV file.

        :param ordered_set: An instance of OrderedContentSet.
        :param row: The row of the CSV file, as a dict.
        """
        ordered_set.profile_fields = []
        for field in [f.strip() for f in (row["profile_fields"] or "").split(",")]:
            if field and field != "-":
                [field_name, field_value] = field.lower().split(":")
                ordered_set.profile_fields.append((field_name, field_value))

    def _extract_ordered_content_set_pages(
        self, row: dict[str, str], index: int
    ) -> list[OrderedContentSetPage]:
        times = self._csv_to_list(row["time"])
        units = self._csv_to_list(row["unit"])
        before_or_afters = self._csv_to_list(row["before_or_after"])
        page_slugs = self._csv_to_list(row["page_slugs"])
        contact_fields = self._csv_to_list(row["contact_field"])

        # Backwards compatibility: if there's only one value for optional fields
        # and it's empty, expand it to match page_slugs count
        num_pages = len(page_slugs)

        if len(times) == 1 and (not times[0] or times[0] == "-"):
            times = [times[0]] * num_pages
        if len(units) == 1 and (not units[0] or units[0] == "-"):
            units = [units[0]] * num_pages
        if len(before_or_afters) == 1 and (
            not before_or_afters[0] or before_or_afters[0] == "-"
        ):
            before_or_afters = [before_or_afters[0]] * num_pages
        if len(contact_fields) == 1:
            contact_fields = [contact_fields[0]] * num_pages

        fields = [times, units, before_or_afters, page_slugs, contact_fields]
        if len({len(item) for item in fields}) != 1:
            raise ImportException(
                f"Row {row['name']} has {len(times)} times, {len(units)} units, {len(before_or_afters)} before_or_afters, {len(page_slugs)} page_slugs and {len(contact_fields)} contact_fields and they should all be equal.",
                index,
            )

        return [
            OrderedContentSetPage(
                time=time,
                unit=unit.lower(),
                before_or_after=before_or_after.lower(),
                page_slug=page_slug,
                contact_field=contact_field,
                locale=row.get("language_code") or row["locale"],
            )
            for time, unit, before_or_after, page_slug, contact_field in zip(
                times, units, before_or_afters, page_slugs, contact_fields, strict=False
            )
        ]

    def _csv_to_list(self, column: str) -> list[str]:
        """
        Return a list of strings parsed from a column of a CSV row.

        :param column: The column to parse.
        :return: A list of strings, split from the value of row[column].
        """
        return [p.strip() for p in column.split(",")]

    def _add_pages(
        self,
        ordered_set: OrderedContentSet,
        pages: list[OrderedContentSetPage],
        index: int,
    ) -> None:
        """
        Given the extracted values from a row of the file, create the corresponding ordered content set pages.

        Note that this adds the pages to the OrderedContentSet object, hence there is no return value.

        :param ordered_set: The ordered content set to add the pages to.
        :param pages: A list of OrderedContentSetPage objects.
        """
        locale = ordered_set.locale
        ordered_set.pages = []
        for page in pages:
            if page.page_slug and page.page_slug != "-":
                content_page = ContentPage.objects.filter(
                    slug=page.page_slug, locale=locale
                ).first()
                if content_page:
                    os_page = {
                        "contentpage": content_page,
                        "time": page.time or "",
                        "unit": page.unit or "",
                        "before_or_after": page.before_or_after or "",
                        "contact_field": page.contact_field or "",
                    }
                    ordered_set.pages.append(("pages", os_page))
                else:
                    raise ImportException(
                        f"Content page not found for slug '{page.page_slug}' in locale '{locale}'",
                        index,
                    )
            if (not page.page_slug or page.page_slug == "-") and (
                page.time or page.unit or page.before_or_after or page.contact_field
            ):
                raise ImportException(
                    "You are attempting to import an ordered content set with page details, but no page slug.",
                    index,
                )

    # FIXME: collect errors across all fields
    def _validate_ordered_set_using_form(
        self, index: int, model: OrderedContentSet
    ) -> None:
        edit_handler = get_edit_handler(OrderedContentSet)
        validate_using_form(edit_handler, model, index)

    def _create_ordered_set_from_row(
        self, index: int, row: dict[str, str]
    ) -> OrderedContentSet:
        """
        Create an ordered content set from a single row of the file.

        :param index: The row number of the row being processed.
        :param row: The row of the file as a dictionary.
        :return: An instance of OrderedContentSet.
        :raises ImportException: If time, units, before_or_afters, page_slugs and contact_fields are not all equal length.
        """
        locale_val = row.get("language_code") or row["locale"]
        ordered_set = self._get_or_init_ordered_content_set(
            index, row, row["slug"].lower(), locale_val.lower()
        )
        ordered_set.name = row["name"]
        self._add_profile_fields(ordered_set, row)

        pages = self._extract_ordered_content_set_pages(row, index)

        self._add_pages(ordered_set, pages, index)

        self._validate_ordered_set_using_form(index, ordered_set)

        ordered_set.save()
        return ordered_set

    def _set_progress(self, progress: int) -> None:
        self.progress_queue.put_nowait(progress)

    def perform_import(self) -> None:
        """
        Import ordered content sets from a file.

        This method reads the file associated with the importer, processes its
        content based on the specified file type (XLSX or CSV), and creates
        ordered content sets by extracting relevant information from each row.
        The progress of the import operation is reported via a queue.

        Raises:
            ImportException: If any inconsistencies are found in the data
            row while creating ordered content sets.
        """
        file = self.file.read()

        rows = parse_file(file, self.filetype)
        rows, rows2 = itertools.tee(rows)
        num_rows = sum(1 for _ in rows2)

        # 10% progress for loading file
        self._set_progress(10)

        for index, row in rows:  # type: ignore
            # Normalize row to support both old Title Case and new lowercase headers
            normalized_row = self._normalize_row(row)  # type: ignore
            os = self._create_ordered_set_from_row(index, normalized_row)  # type: ignore
            if not os:
                raise ImportException("Ordered Content Set not created", index)
            # 10-100% for loading ordered content sets
            self._set_progress(10 + index * 90 // num_rows)
