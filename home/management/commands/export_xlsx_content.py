from django.core.management.base import BaseCommand

from home import utils


class Command(BaseCommand):
    help = "Export content to XLSX"

    def handle(self, *args, **options):
        utils.export_xlsx_content()
