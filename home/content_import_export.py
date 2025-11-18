from logging import getLogger

from django.db import transaction
from django.http import HttpResponse
from wagtail.query import PageQuerySet

logger = getLogger(__name__)


@transaction.atomic
def import_content(file, filetype, progress_queue, purge=True, locale=None) -> None:
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
