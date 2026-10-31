"""Editable system settings, including the loan rule multipliers."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from ..core.eligibility import LoanRules
from ..db.models import SystemSetting
from . import audit
from .errors import ServiceError

DEFAULTS: dict[str, str] = {
    **LoanRules().as_dict(),
    "university_name": "UNIVERSITY OF RUHUNA",
    "university_code": "F",
    "signatory_title": "BURSAR",
    "text_line_ending": "CRLF",
    "backup_keep": "30",
}

RULE_KEYS = tuple(LoanRules().as_dict().keys())


def get_all(session: Session) -> dict[str, str]:
    values = dict(DEFAULTS)
    for row in session.query(SystemSetting).all():
        values[row.key] = row.value
    return values


def get(session: Session, key: str) -> str:
    row = session.get(SystemSetting, key)
    return row.value if row else DEFAULTS.get(key, "")


def loan_rules(session: Session) -> LoanRules:
    return LoanRules.from_dict(get_all(session))


def save(session: Session, username: str, changes: dict[str, str]) -> None:
    current = get_all(session)
    merged = {**current, **changes}
    try:
        rules = LoanRules.from_dict(merged)
    except (InvalidOperation, ValueError) as exc:
        raise ServiceError("Loan rules must be numbers.") from exc
    errors = rules.validate()
    if errors:
        raise ServiceError("\n".join(errors))
    code = merged.get("university_code", "").strip()
    if not 1 <= len(code) <= 2:
        raise ServiceError("University code must be 1 or 2 characters.")
    changed = {}
    for key, value in changes.items():
        value = str(value).strip()
        if key in RULE_KEYS:
            value = str(Decimal(value).normalize()) if key != "instalment_months" else str(int(value))
        if current.get(key) != value:
            changed[key] = {"from": current.get(key), "to": value}
            row = session.get(SystemSetting, key)
            if row is None:
                session.add(SystemSetting(key=key, value=value))
            else:
                row.value = value
    if changed:
        audit.record(session, username, "settings.update", "settings", summary=", ".join(changed), details=changed)
