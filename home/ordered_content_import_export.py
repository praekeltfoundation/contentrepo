from logging import getLogger

from django.http import HttpResponse  # type: ignore
from wagtail.query import PageQuerySet  # type: ignore

from .export_ordered_sets import OrderedSetExporter, OrderedSetsExportWriter
from .import_ordered_content_sets import OrderedContentSetImporter

logger = getLogger(__name__)


def export_xlsx_ordered_content(queryset: PageQuerySet, response: HttpResponse) -> None:
    exporter = OrderedSetExporter(queryset)
    export_rows = exporter.perform_export()
    OrderedSetsExportWriter(export_rows).write_xlsx(response)


def export_csv_ordered_content(queryset: PageQuerySet, response: HttpResponse) -> None:
    exporter = OrderedSetExporter(queryset)
    export_rows = exporter.perform_export()
    OrderedSetsExportWriter(export_rows).write_csv(response)


def import_ordered_sets(file, filetype, progress_queue) -> None:  # type: ignore
    """
    Import given ordered content file in the configured format with the configured importer.

    :param file: The file to be imported, as a django.core.files.base.File.
    :param filetype: The type of the file, e.g. 'CSV' or 'XLSX'.
    :param progress_queue: A queue.Queue to put progress information on.
    """
    importer = OrderedContentSetImporter(file, filetype, progress_queue)
    importer.perform_import()
