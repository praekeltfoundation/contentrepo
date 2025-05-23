from logging import getLogger

from django.db import transaction  # type: ignore
from django.http import HttpResponse  # type: ignore
from wagtail.query import PageQuerySet  # type: ignore

from .export_whatsapp_templates import (
    WhatsAppTemplateExporter,
    WhatsAppTemplateExportWriter,
)
from .import_whatsapp_templates import WhatsAppTemplateImporter

logger = getLogger(__name__)


def export_xlsx_whatsapp_template(
    queryset: PageQuerySet, response: HttpResponse
) -> None:
    exporter = WhatsAppTemplateExporter(queryset)
    export_rows = exporter.perform_export()
    WhatsAppTemplateExportWriter(export_rows).write_xlsx(response)


def export_csv_whatsapp_template(
    queryset: PageQuerySet, response: HttpResponse
) -> None:
    exporter = WhatsAppTemplateExporter(queryset)
    export_rows = exporter.perform_export()
    WhatsAppTemplateExportWriter(export_rows).write_csv(response)


@transaction.atomic
def import_whatsapptemplate(  # type: ignore
    file,
    filetype,
    progress_queue,
    purge=True,
    locale=None,
) -> None:
    importer = WhatsAppTemplateImporter(
        file.read(), filetype, progress_queue, purge, locale
    )
    importer.perform_import()
