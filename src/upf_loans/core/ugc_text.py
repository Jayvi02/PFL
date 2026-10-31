"""Fixed-width UGC renewal text file.

Field widths come from the width mask in row 4 of the "new format2007" sheet:

    NAME                  50  CCCC...C (50)
    PF-NUMBER              8  22222222
    ID-NUMBER (NIC)       10  2222222222
    LOAN REQUEST MONTH     2  22
    LOAN REQUEST YEAR      4  2222
    LAST LOAN MONTH        2  22
    LAST LOAN YEAR         4  2222
    LOAN APPROVED         15  444444444444444   (format 000000000000.00)
    EXISTING LOAN BALANCE 15  444444444444444
    BALANCE PAYABLE       15  444444444444444
    UNIVERSITY CODE        2  " R"

One line per employee, 127 characters. The serial number and the totals row of
the printed sheet are not part of the 2007 layout and are not written.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .money import round_cents

LINE_LENGTH = 127


class UgcFormatError(ValueError):
    pass


@dataclass(frozen=True)
class UgcRow:
    name: str
    pf_number: str
    nic: str
    request_month: int
    request_year: int
    last_loan_month: int | None
    last_loan_year: int | None
    loan_approved: Decimal
    existing_balance: Decimal
    balance_payable: Decimal
    university_code: str


@dataclass(frozen=True)
class Field:
    label: str
    width: int


FIELDS = (
    Field("NAME", 50),
    Field("PF-NUMBER", 8),
    Field("ID-NUMBER", 10),
    Field("LOAN REQUEST MONTH", 2),
    Field("LOAN REQUEST YEAR", 4),
    Field("LAST LOAN MONTH", 2),
    Field("LAST LOAN YEAR", 4),
    Field("LOAN APPROVED", 15),
    Field("EXISTING LOAN BALANCE", 15),
    Field("BALANCE PAYABLE", 15),
    Field("UNIVERSITY CODE", 2),
)
assert sum(f.width for f in FIELDS) == LINE_LENGTH


def _text(value: str, width: int, label: str, who: str) -> str:
    value = (value or "").strip()
    if len(value) > width:
        raise UgcFormatError(f"{who}: {label} '{value}' is {len(value)} characters; the limit is {width}.")
    try:
        value.encode("ascii")
    except UnicodeEncodeError as exc:
        raise UgcFormatError(f"{who}: {label} '{value}' contains non-English characters.") from exc
    return value.ljust(width)


def _number(value: int | None, width: int, label: str, who: str, required: bool = True) -> str:
    if value is None:
        if required:
            raise UgcFormatError(f"{who}: {label} is missing.")
        return " " * width
    if value < 0 or len(str(value)) > width:
        raise UgcFormatError(f"{who}: {label} '{value}' does not fit in {width} digits.")
    return str(value).zfill(width)


def _amount(value: Decimal, label: str, who: str) -> str:
    value = round_cents(value)
    if value < 0:
        raise UgcFormatError(f"{who}: {label} is negative ({value}).")
    text = f"{value:015.2f}"
    if len(text) != 15:
        raise UgcFormatError(f"{who}: {label} {value} is too large for 15 characters.")
    return text


def format_row(row: UgcRow) -> str:
    who = row.pf_number or row.name or "row"
    if not 1 <= row.request_month <= 12:
        raise UgcFormatError(f"{who}: request month must be 1 to 12.")
    if row.last_loan_month is not None and not 1 <= row.last_loan_month <= 12:
        raise UgcFormatError(f"{who}: last loan month must be 1 to 12.")
    parts = [
        _text(row.name, 50, "name", who),
        _text(row.pf_number, 8, "PF number", who),
        _text(row.nic, 10, "NIC", who),
        _number(row.request_month, 2, "request month", who),
        _number(row.request_year, 4, "request year", who),
        _number(row.last_loan_month, 2, "last loan month", who, required=False),
        _number(row.last_loan_year, 4, "last loan year", who, required=False),
        _amount(row.loan_approved, "loan approved", who),
        _amount(row.existing_balance, "existing loan balance", who),
        _amount(row.balance_payable, "balance payable", who),
        _text(row.university_code, 2, "university code", who).rstrip().rjust(2),
    ]
    line = "".join(parts)
    assert len(line) == LINE_LENGTH, len(line)
    return line


def build_file(rows: list[UgcRow], line_ending: str = "\r\n") -> tuple[str, list[str]]:
    """Return (file_text, errors). The text is empty when any row has an error."""
    lines: list[str] = []
    errors: list[str] = []
    for row in rows:
        try:
            lines.append(format_row(row))
        except UgcFormatError as exc:
            errors.append(str(exc))
    if errors:
        return "", errors
    return "".join(line + line_ending for line in lines), []
