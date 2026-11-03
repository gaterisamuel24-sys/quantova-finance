"""Response bodies for CSV transaction imports."""

from typing import Literal

from pydantic import BaseModel


class ImportRowError(BaseModel):
    """One problem in the file. `row` is the line number as a spreadsheet would show it."""

    row: int
    column: str | None
    message: str


class ImportReport(BaseModel):
    # rejected: errors found, nothing imported. validated: dry run passed, nothing imported.
    # imported: every row was imported, in a single database transaction.
    status: Literal["rejected", "validated", "imported"]
    filename: str | None
    row_count: int
    imported_count: int
    error_count: int
    errors: list[ImportRowError]
