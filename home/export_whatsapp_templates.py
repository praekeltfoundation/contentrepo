import copy
import csv
from dataclasses import asdict, astuple, dataclass, fields
from math import ceil

from django.http import HttpResponse  # type: ignore
from openpyxl.styles import Border, Color, Font, NamedStyle, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet
from wagtail.blocks import (  # type: ignore
    StreamValue,
    StructValue,  # type: ignore
)
from wagtail.query import PageQuerySet  # type: ignore


@dataclass
class ExportRow:
    title: str = ""
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
    question: str = ""
    error: str = ""
    answers: str = ""
    scores: str = ""

    @classmethod
    def headings(cls) -> list[str]:
        return [f.name for f in fields(cls)]

    def to_dict(self) -> dict[str, str | int]:
        return asdict(self)

    def to_tuple(self) -> tuple[str | int, ...]:
        return astuple(self)


# Define your AssessmentExporter class
class WhatsAppTemplateExporter:
    rows: list[dict[str | int, str | int]]

    def __init__(self, queryset: PageQuerySet):
        self.rows = []
        self.queryset = queryset

    def perform_export(self) -> list[dict[str | int, str | int]]:
        for item in self.queryset:
            questions_data = self.get_questions(item.questions)
            for i, question_data in enumerate(questions_data):

                self.rows.append(
                    {
                        "title": item.title,
                        # "page_id": item.id,
                        "tags": self._comma_sep_qs(item.tags.all()),
                        "slug": item.slug,
                        "locale": str(item.locale.language_code),
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

    def format_answers(self, answers: list[str]) -> str:
        escaped_answer = [answer.replace(",", "</>") for answer in answers]
        joined_string = ",".join(escaped_answer).split(",")
        return_value = [answer.replace("</>", ",") for answer in joined_string]
        return str(return_value)[1:-1]

    def get_questions(self, questions: StreamValue) -> list[StructValue]:
        question_data = []
        for question in questions:
            answers = []
            scores = []
            for answer in question.value["answers"]:
                answers.append(answer["answer"])
                scores.append(str(answer["score"]))
            question_data.append(
                {
                    "question": (question.value["question"]).replace("\n", ","),
                    "error": (question.value["error"]),
                    "answers": self.format_answers(answers),
                    "scores": ", ".join(scores),
                }
            )
        return question_data

    @staticmethod
    def _comma_sep_qs(unformatted_query: PageQuerySet) -> str:
        return ", ".join(str(x) for x in unformatted_query if str(x) != "")


"""
Definining ExportWriter class for assessments
"""


class WhatsAppTemplateExportWriter:
    rows: list[dict[str | int, str | int]]

    def __init__(self, rows: list[dict[str | int, str | int]]):
        self.rows = rows

    def write_xlsx(self, response: HttpResponse) -> None:
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(ExportRow.headings())  # type: ignore
        for row in self.rows:
            row_values = [
                row["title"],
                # row["page_id"],
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
                row["question"],
                row["error"],
                row["answers"],
                row["scores"],
            ]
            worksheet.append(row_values)  # type: ignore
        _set_xlsx_styles(workbook, worksheet)  # type: ignore
        workbook.save(response)

    def write_csv(self, response: HttpResponse) -> None:
        csv_response = csv.writer(response)
        csv_response.writerow(ExportRow.headings())

        # Write data rows
        for row in self.rows:
            row_values = [
                row["title"],
                # row["page_id"],
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
                row["question"],
                row["error"],
                row["answers"],
                row["scores"],
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
        # "page_id": 110,
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
        "question": 370,
        "error": 400,
        "answer": 110,
        "scores": 110,
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
