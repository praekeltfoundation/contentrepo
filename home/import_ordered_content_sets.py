import csv
import io
from io import BytesIO
from logging import getLogger
from queue import Queue

from django.core.files.base import File  # type: ignore
from openpyxl import load_workbook

from home.import_helpers import ImportException
from home.models import ContentPage, OrderedContentSet

logger = getLogger(__name__)


class OrderedContentSetImporter:
    def __init__(
        self,
        file: File,
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

    def _get_or_init_ordered_content_set(
        self, row: dict, set_name: str
    ) -> OrderedContentSet:
        """
        Get or initialize an instance of OrderedContentSet from a row of a CSV file.

        :param row: The row of the CSV file, as a dict.
        :param set_name: The name of the ordered content set.
        :return: An instance of OrderedContentSet.
        """
        ordered_set = OrderedContentSet.objects.filter(name=set_name).first()
        if not ordered_set:
            ordered_set = OrderedContentSet(name=set_name)

        ordered_set.profile_fields = []
        for field in [f.strip() for f in (row["Profile Fields"] or "").split(",")]:
            if not field or field == "-":
                continue
            [field_name, field_value] = field.split(":")
            ordered_set.profile_fields.append((field_name, field_value))

        ordered_set.pages = []
        return ordered_set

    def _csv_to_list(self, column: str) -> list[str]:
        """
        Return a list of strings parsed from a column of a CSV row.

        :param column: The column to parse.
        :return: A list of strings, split from the value of row[column].
        """
        return [p.strip() for p in column.split(",")]

    def _validate_extracted_values(
        self,
        index: int,
        row: dict,
        times: list,
        units: list,
        before_or_afters: list,
        page_slugs: list,
        contact_fields: list,
    ) -> None:
        """
        Validate that the extracted values (times, units, before_or_afters, page_slugs, contact_fields) from a row of the file have the same length.
        If not, raise an ImportException.
        """

        if (
            len(times) != 0
            and len(times) != len(units)
            or len(times) != len(before_or_afters)
            or len(times) != len(page_slugs)
            or len(times) != len(contact_fields)
        ):
            raise ImportException(
                f"Row {row['Name']} has {len(times)} times, {len(units)} units, {len(before_or_afters)} before_or_afters, {len(page_slugs)} page_slugs and {len(contact_fields)} contact_fields and they should all be equal.",
                index,
            )

    def _create_pages(
        self,
        ordered_set: OrderedContentSet,
        times: list,
        units: list,
        before_or_afters: list,
        page_slugs: list,
        contact_fields: list,
    ) -> None:
        """
        Given the extracted values from a row of the file, create the corresponding ordered content set pages.

        Note that this adds the pages to the OrderedContentSet object, hence there is no return value.

        :param ordered_set: The ordered content set to add the pages to.
        :param times: The times extracted from the row.
        :param units: The units extracted from the row.
        :param before_or_afters: The before or afters extracted from the row.
        :param page_slugs: The page slugs extracted from the row.
        :param contact_fields: The contact fields extracted from the row.
        """
        for idx, page_slug in enumerate(page_slugs):
            if not page_slug or page_slug == "-":
                continue
            page = ContentPage.objects.filter(slug=page_slug).first()
            time = times[idx]
            unit = units[idx]
            before_or_after = before_or_afters[idx]
            contact_field = contact_fields[idx]
            if page:
                ordered_set.pages.append(
                    (
                        "pages",
                        {
                            "contentpage": page,
                            "time": time or "",
                            "unit": unit or "",
                            "before_or_after": before_or_after or "",
                            "contact_field": contact_field or "",
                        },
                    )
                )
            else:
                logger.warning(f"Content page not found for slug '{page_slug}'")

    def _create_ordered_set_from_row(self, index: int, row: dict) -> OrderedContentSet:
        """
        Create an ordered content set from a single row of the file.

        :param index: The row number of the row being processed.
        :param row: The row of the file as a dictionary.
        :return: An instance of OrderedContentSet.
        :raises ImportException: If time, units, before_or_afters, page_slugs and contact_fields are not all equal length.
        """
        ordered_set = self._get_or_init_ordered_content_set(row, row["Name"])

        times = self._csv_to_list(row["Time"])
        units = self._csv_to_list(row["Unit"])
        before_or_afters = self._csv_to_list(row["Before Or After"])
        page_slugs = self._csv_to_list(row["Page Slugs"])
        # backwards compatiblilty if there's only one contact field
        contact_fields = row["Contact Field"].split(",")
        contact_fields = (
            [p.strip() for p in contact_fields]
            if len(contact_fields) > 1
            else [contact_fields[0]] * len(times)
        )

        self._validate_extracted_values(
            index, row, times, units, before_or_afters, page_slugs, contact_fields
        )

        self._create_pages(
            ordered_set, times, units, before_or_afters, page_slugs, contact_fields
        )

        ordered_set.save()
        return ordered_set

    def perform_import(self):
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
        lines = []
        if self.filetype == "XLSX":
            wb = load_workbook(filename=BytesIO(file))
            ws = wb.worksheets[0]
            ws.delete_rows(1)
            for row in ws.iter_rows(values_only=True):
                row_dict = {
                    "Name": row[0],
                    "Profile Fields": row[1],
                    "Page Slugs": row[2],
                    "Time": row[3],
                    "Unit": row[4],
                    "Before Or After": row[5],
                    "Contact Field": row[6],
                }
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
        self.progress_queue.put_nowait(10)

        for index, row in enumerate(lines):
            os = self._create_ordered_set_from_row(index, row)
            if not os:
                print(f"Ordered Content Set not created for row {index + 1}")
            # 10-100% for loading ordered content sets
            self.progress_queue.put_nowait(10 + index * 90 / len(lines))
