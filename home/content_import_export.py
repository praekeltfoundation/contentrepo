from logging import getLogger
from queue import Queue

from django.core.files.base import File  # type: ignore
from django.db import transaction
from django.http import HttpResponse
from wagtail.query import PageQuerySet

logger = getLogger(__name__)


@transaction.atomic
def import_content(file, filetype, progress_queue, purge=True, locale=None):
    from .import_content_pages import ContentImporter

    importer = ContentImporter(file.read(), filetype, progress_queue, purge, locale)
    importer.perform_import()
    return importer


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


"""Ordered Content Sets Imports/Export"""


def export_xlsx_ordered_content(queryset: PageQuerySet, response: HttpResponse) -> None:
    from .export_ordered_sets import OrderedSetExporter, OrderedSetsExportWriter

    exporter = OrderedSetExporter(queryset)
    export_rows = exporter.perform_export()
    OrderedSetsExportWriter(export_rows).write_xlsx(response)


def export_csv_ordered_content(queryset: PageQuerySet, response: HttpResponse) -> None:
    from .export_ordered_sets import OrderedSetExporter, OrderedSetsExportWriter

    exporter = OrderedSetExporter(queryset)
    export_rows = exporter.perform_export()
    OrderedSetsExportWriter(export_rows).write_csv(response)


def import_ordered_sets(file: File, filetype: str, progress_queue: Queue) -> None:
    """
    Import given ordered content file in the configured format with the configured importer.

    :param file: The file to be imported, as a django.core.files.base.File.
    :param filetype: The type of the file, e.g. 'CSV' or 'XLSX'.
    :param progress_queue: A queue.Queue to put progress information on.
    """

    from .import_ordered_content_sets import OrderedContentSetImporter

    importer = OrderedContentSetImporter(file, filetype, progress_queue)
    importer.perform_import()
