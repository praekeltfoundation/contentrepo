from datetime import datetime

from django.http import HttpResponse

from .assessment_import_export import export_csv_assessment, export_xlsx_assessment
from .content_import_export import export_csv_content, export_xlsx_content


class SpreadsheetExportMixin:
    """A mixin for views, providing spreadsheet export functionality in csv and xlsx formats for assessments"""

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
        response["Content-Disposition"] = 'attachment; filename="{}.xlsx"'.format(
            self.get_filename()
        )
        export_xlsx_content(queryset, response)
        return response

    def write_csv_response(self, queryset):
        response = HttpResponse(content_type="application/CSV")
        response["Content-Disposition"] = 'attachment; filename="{}.csv"'.format(
            self.get_filename()
        )
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


class SpreadsheetExportMixinAssessment:
    """A mixin for views, providing spreadsheet export functionality in csv and xlsx formats in Assessment"""

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
        response["Content-Disposition"] = 'attachment; filename="{}.xlsx"'.format(
            self.get_filename()
        )
        export_xlsx_assessment(queryset, response)
        return response

    def write_csv_response(self, queryset):
        response = HttpResponse(content_type="application/CSV")
        response["Content-Disposition"] = 'attachment; filename="{}.csv"'.format(
            self.get_filename()
        )
        export_csv_assessment(queryset, response)

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
