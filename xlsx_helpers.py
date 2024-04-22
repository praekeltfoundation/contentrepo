from typing import cast

from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet


def get_active_sheet(workbook: Workbook) -> Worksheet:
    """
    A wrapper around the type juggling we need to keep mypy happy, so we don't
    have to reimplement it in a bunch of different places.
    """
    return cast(Worksheet, workbook.active)
