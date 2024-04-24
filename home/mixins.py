from datetime import datetime

from django.http import HttpResponse

from .content_import_export import export_csv_content, export_xlsx_content
from .whatsapp_template_import_export import (
    export_csv_whatsapp_template,
    export_xlsx_whatsapp_template,
)


class SpreadsheetExportMixin:
    """A mixin for views, providing spreadsheet export functionality in csv and xlsx formats"""

    FORMAT_XLSX = "xlsx"
    FORMAT_CSV = "csv"
    FORMATS = (FORMAT_XLSX, FORMAT_CSV)

    def get_filename(self):
        """Gets the base filename for the exported spreadsheet, without extensions"""
        return f'exported_content_{datetime.now().strftime("%Y%m%d")}'

    def write_xlsx_response(self, queryset):
        ctype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        response = HttpResponse(content_type=ctype)
        filename = f"{self.get_filename()}.xlsx"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        export_xlsx_content(queryset, response)
        return response

    def write_csv_response(self, queryset):
        response = HttpResponse(content_type="application/CSV")
        filename = f"{self.get_filename()}.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        export_csv_content(queryset, response)
        return response

    def as_spreadsheet(self, queryset, spreadsheet_format):
        """Return a response with a spreadsheet representing the exported data from queryset, in the format specified"""
        if spreadsheet_format == self.FORMAT_CSV:
            return self.write_csv_response(queryset)
        elif spreadsheet_format == self.FORMAT_XLSX:
            return self.write_xlsx_response(queryset)

    def get_export_url(self, format):
        params = self.request.GET.copy()
        params["export"] = format
        return self.request.path + "?" + params.urlencode()

    @property
    def xlsx_export_url(self):
        return self.get_export_url("xlsx")

    @property
    def csv_export_url(self):
        return self.get_export_url("csv")


class SpreadsheetExportMixinWhatsAppTemplate:
    """A mixin for views, providing spreadsheet export functionality in csv and xlsx formats for WhatsAppTemplates"""

    FORMAT_XLSX = "xlsx"
    FORMAT_CSV = "csv"
    FORMATS = (FORMAT_XLSX, FORMAT_CSV)

    def get_filename(self):
        """Gets the base filename for the exported spreadsheet, without extensions"""
        return f'exported_content_{datetime.now().strftime("%Y%m%d")}'

    def write_xlsx_response(self, queryset):
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = (
            f'attachment; filename="{self.get_filename()}.xlsx"'
        )
        export_xlsx_whatsapp_template(queryset, response)
        return response

    def write_csv_response(self, queryset):
        response = HttpResponse(content_type="application/CSV")
        response["Content-Disposition"] = (
            f'attachment; filename="{self.get_filename()}.csv"'
        )
        export_csv_whatsapp_template(queryset, response)

        return response

    def as_spreadsheet(self, queryset, spreadsheet_format):
        """Return a response with a spreadsheet representing the exported data from queryset, in the format specified"""
        if spreadsheet_format == self.FORMAT_CSV:
            return self.write_csv_response(queryset)
        elif spreadsheet_format == self.FORMAT_XLSX:
            return self.write_xlsx_response(queryset)

    def get_export_url(self, format):
        params = self.request.GET.copy()
        params["export"] = format
        return self.request.path + "?" + params.urlencode()

    @property
    def xlsx_export_url(self):
        return self.get_export_url("xlsx")

    @property
    def csv_export_url(self):
        return self.get_export_url("csv")
