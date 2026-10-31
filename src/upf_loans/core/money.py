"""Money helpers.

All money is handled as :class:`decimal.Decimal` in the application and stored
in the database as an integer number of cents. Floats are never used for money.
"""

from __future__ import annotations

from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")
ZERO = Decimal("0")


class MoneyError(ValueError):
    """Raised when a value cannot be interpreted as money."""


def to_decimal(value: object) -> Decimal:
    """Convert user/Excel input to Decimal without going through binary floats."""
    if value is None or value == "":
        return ZERO
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        raise MoneyError(f"Not a money value: {value!r}")
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        # Excel hands us floats; repr() gives the shortest exact round-trip text.
        return Decimal(repr(value))
    text = str(value).strip().replace(",", "")
    if not text:
        return ZERO
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise MoneyError(f"Not a valid amount: {value!r}") from exc


def round_cents(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def excel_int(value: Decimal) -> Decimal:
    """Excel INT(): round down towards negative infinity."""
    return value.to_integral_value(rounding=ROUND_FLOOR)


def to_cents(value: object) -> int:
    return int(round_cents(to_decimal(value)) * 100)


def from_cents(cents: int | None) -> Decimal:
    if cents is None:
        return ZERO
    return (Decimal(cents) / 100).quantize(CENT)


def format_money(value: Decimal | None, blank_zero: bool = False) -> str:
    if value is None:
        return ""
    if blank_zero and value == 0:
        return ""
    return f"{round_cents(value):,.2f}"
