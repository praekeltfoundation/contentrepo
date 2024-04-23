from logging import getLogger

from django.db import transaction
from django.http import HttpResponse
from wagtail.query import PageQuerySet

from .export_assessments import AssessmentExporter, AssessmentExportWriter
from .import_assessment_pages import ContentImporter

logger = getLogger(__name__)


def export_xlsx_assessment(queryset: PageQuerySet, response: HttpResponse) -> None:

    exporter = AssessmentExporter(queryset)
    export_rows = exporter.perform_export()
    AssessmentExportWriter(export_rows).write_xlsx(response)


def export_csv_assessment(queryset: PageQuerySet, response: HttpResponse) -> None:

    exporter = AssessmentExporter(queryset)
    export_rows = exporter.perform_export()
    AssessmentExportWriter(export_rows).write_csv(response)


@transaction.atomic
def import_assessment(file, filetype, progress_queue, purge=True, locale=None) -> None:
    importer = ContentImporter(file.read(), filetype, progress_queue, purge, locale)
    importer.perform_import()
