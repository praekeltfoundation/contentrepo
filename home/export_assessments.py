import copy
import csv
from dataclasses import asdict, astuple, dataclass, fields
from math import ceil

from django.http import HttpResponse  # type: ignore
from openpyxl.styles import Border, Color, Font, NamedStyle, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet
from wagtail.query import PageQuerySet  # type: ignore


@dataclass
class ExportRow:
    title: str = ""
    page_id: int = 0
    tags: str = ""
    slug: str = ""
    locale: str = ""
    high_result_page: str = ""
    high_inflection: str = ""
    medium_result_page: str = ""
    medium_inflection: str = ""
    low_result_page: str = ""
    low_inflection: str = ""
    generic_error: str = ""
    question_count: int = 0
    questions: str = ""
    error: str = ""
    answers: str = ""
    score: str = ""

    @classmethod
    def headings(cls) -> list[str]:
        return [f.name for f in fields(cls)]

    def to_dict(self) -> dict[str, str | int]:
        return asdict(self)

    def to_tuple(self) -> tuple[str | int, ...]:
        return astuple(self)


# Define your AssessmentExporter class
class AssessmentExporter:
    rows: list[dict]

    def __init__(self, queryset: PageQuerySet):
        self.rows = []
        self.queryset = queryset

    def perform_export(self) -> list[dict]:
        self.queryset[0].locale
        for item in self.queryset:
            questions_data = self.get_questions(item.questions)
            for i, question_data in enumerate(questions_data):

                self.rows.append(
                    {
                        "title": item.title,
                        "page_id": item.id,
                        "tags": self._comma_sep_qs(item.tags.all()),
                        "slug": item.slug,
                        "locale": str(item.locale),
                        "high_result_page": str(item.high_result_page.slug),
                        "high_inflection": item.high_inflection,
                        "medium_result_page": str(item.medium_result_page.slug),
                        "medium_inflection": item.medium_inflection,
                        "low_result_page": str(item.low_result_page.slug),
                        "low_inflection": 0,
                        "generic_error": item.generic_error,
                        "question_count": i + 1,
                        **question_data,
                    }
                )
        return self.rows

    def get_questions(self, questions):
        question_data = []
        for question in questions:
            answers = []
            scores = []
            for answer in question.value["answers"]:
                answers.append(answer["answer"])
                scores.append(str(answer["score"]))
            question_data.append(
                {
                    "questions": (question.value["question"]).replace("\n", ","),
                    "error": (question.value["error"]),
                    "answers": ", ".join(answers),
                    "score": ", ".join(scores),
                }
            )
        return question_data

    @staticmethod
    def _comma_sep_qs(unformatted_query: PageQuerySet) -> str:
        return ", ".join(str(x) for x in unformatted_query if str(x) != "")


"""
Definining ExportWriter class for assessments
"""


class AssessmentExportWriter:
    rows: list[dict]

    def __init__(self, rows: list[dict]):
        self.rows = rows

    def write_xlsx(self, response: HttpResponse) -> None:
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(ExportRow.headings())
        for row in self.rows:
            row_values = [
                row["title"],
                row["page_id"],
                row["tags"],
                row["slug"],
                row["locale"],
                row["high_result_page"],
                row["high_inflection"],
                row["medium_result_page"],
                row["medium_inflection"],
                row["low_result_page"],
                row["low_inflection"],
                row["generic_error"],
                row["question_count"],
                row["questions"],
                row["error"],
                row["answers"],
                row["score"],
            ]
            worksheet.append(row_values)

        # Save workbook to response
        _set_xlsx_styles(workbook, worksheet)
        workbook.save(response)

    def write_csv(self, response: HttpResponse) -> None:
        csv_response = csv.writer(response)

        # Write header row

        csv_response.writerow(ExportRow.headings())

        # Write data rows
        for row in self.rows:
            row_values = [
                row["title"],
                row["page_id"],
                row["tags"],
                row["slug"],
                row["locale"],
                row["high_result_page"],
                row["high_inflection"],
                row["medium_result_page"],
                row["medium_inflection"],
                row["low_result_page"],
                row["low_inflection"],
                row["generic_error"],
                row["question_count"],
                row["questions"],
                row["error"],
                row["answers"],
                row["score"],
            ]
            csv_response.writerow(row_values)


def _set_xlsx_styles(wb: Workbook, sheet: Worksheet) -> None:
    """Sets the style for the workbook adding any formatting that will make the sheet more aesthetically pleasing"""
    # Adjustment is because the size in openxlsx and google sheets are not equivalent
    adjustment = 7
    # Padding
    sheet.insert_cols(1)

    # Set columns based on best size

    column_widths_in_pts = {
        "title": 110,
        "page_id": 110,
        "tags": 110,
        "slug": 110,
        "locale": 118,
        "high_result_page": 110,
        "high_inflection": 110,
        "medium_result_page": 110,
        "medium_inflection": 110,
        "low_result_page": 118,
        "low_inflection": 110,
        "generic_error": 300,
        "question_count": 110,
        "questions": 370,
        "error": 400,
        "answer": 110,
        "score": 110,
    }

    for index, column_width in enumerate(column_widths_in_pts.values(), 2):
        sheet.column_dimensions[get_column_letter(index)].width = ceil(
            column_width / adjustment
        )

    # Freeze heading row and side panel, 1 added because it freezes before the column
    panel_column = get_column_letter(5)
    sheet.freeze_panes = sheet[f"{panel_column}2"]

    # Colours
    blue = Color(rgb="0099CCFF")

    # Boarders
    left_border = Border(left=Side(border_style="thin", color="FF000000"))

    # Fills
    blue_fill = PatternFill(patternType="solid", fgColor=blue)

    # Named Styles
    header_style = NamedStyle(name="header_style")
    menu_style = NamedStyle(name="menu_style")

    # Set attributes to styles
    header_style.font = Font(bold=True, size=10)
    menu_style.fill = blue_fill
    menu_style.font = Font(bold=True, size=10)

    # Add named styles to wb
    wb.add_named_style(header_style)
    wb.add_named_style(menu_style)

    # column widths

    # Set menu style for any "Menu" row
    for row in sheet.iter_rows():
        if isinstance(row[1].value, str) and "Menu" in row[1].value:
            for cell in row:
                cell.style = menu_style

    # Set header style for row 1 and 2
    for row in sheet["1:2"]:
        for cell in row:
            cell.style = header_style

    # Set dividing border for side panel
    for cell in sheet[f"{panel_column}:{panel_column}"]:
        cell.border = left_border

    # set font on all cells initially to 10pt and row height
    general_font = Font(size=10)
    for index, row in enumerate(sheet.iter_rows()):
        if index > 2:
            sheet.row_dimensions[index].height = 60  # type: ignore # Bad annotation.
        for cell in row:
            cell.font = general_font
            alignment = copy.copy(cell.alignment)
            alignment.wrapText = True
            cell.alignment = alignment  # type: ignore # Broken typeshed update, maybe?
