"""Monthly renewal batches (the MAIN sheet + the PF LOAN send UGC sheet)."""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.eligibility import LoanInputs, LoanResult, calculate
from ..core.money import format_money
from ..core.ugc_text import UgcRow
from ..db.models import Employee, RenewalBatch, RenewalEntry, User
from . import audit, settings
from .errors import PermissionDenied, ServiceError

MONTHS = [
    "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
    "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER",
]


def month_name(month: int) -> str:
    return MONTHS[month - 1]


def batch_label(batch: RenewalBatch) -> str:
    return f"{month_name(batch.request_month).title()} {batch.request_year}"


def list_batches(session: Session) -> list[RenewalBatch]:
    stmt = select(RenewalBatch).order_by(RenewalBatch.request_year.desc(), RenewalBatch.request_month.desc())
    return list(session.scalars(stmt))


def get_batch(session: Session, batch_id: int) -> RenewalBatch:
    batch = session.get(RenewalBatch, batch_id)
    if batch is None:
        raise ServiceError("Renewal month not found.")
    return batch


def create_batch(session: Session, actor: User, month: int, year: int) -> RenewalBatch:
    if not 1 <= month <= 12:
        raise ServiceError("Month must be 1 to 12.")
    if not 2000 <= year <= 2100:
        raise ServiceError("Year looks wrong.")
    existing = session.scalar(
        select(RenewalBatch).where(RenewalBatch.request_month == month, RenewalBatch.request_year == year)
    )
    if existing:
        raise ServiceError(f"A renewal list for {month_name(month).title()} {year} already exists.")
    batch = RenewalBatch(request_month=month, request_year=year, letter_date=date.today().strftime("%d.%m.%Y"))
    session.add(batch)
    session.flush()
    audit.record(session, actor.username, "batch.create", "batch", batch.id, batch_label(batch))
    return batch


def _require_draft(batch: RenewalBatch) -> None:
    if batch.is_locked:
        raise ServiceError(f"{batch_label(batch)} is finalized and cannot be changed.")


def previous_entry(session: Session, employee_id: int, before: RenewalBatch | None = None) -> RenewalEntry | None:
    """The employee's most recent entry in another batch (used to pre-fill the form)."""
    stmt = select(RenewalEntry).join(RenewalBatch).where(RenewalEntry.employee_id == employee_id)
    if before is not None:
        stmt = stmt.where(RenewalBatch.id != before.id)
    stmt = stmt.order_by(RenewalBatch.request_year.desc(), RenewalBatch.request_month.desc()).limit(1)
    return session.scalar(stmt)


def suggested_last_loan(session: Session, employee_id: int, batch: RenewalBatch | None) -> tuple[int | None, int | None]:
    """Last loan month/year = the employee's latest finalized renewal, else their previous entry's value."""
    stmt = (
        select(RenewalBatch)
        .join(RenewalEntry)
        .where(RenewalEntry.employee_id == employee_id, RenewalBatch.status == "finalized")
        .order_by(RenewalBatch.request_year.desc(), RenewalBatch.request_month.desc())
    )
    if batch is not None:
        stmt = stmt.where(RenewalBatch.id != batch.id)
    last = session.scalars(stmt).first()
    if last:
        return last.request_month, last.request_year
    prev = previous_entry(session, employee_id, batch)
    if prev:
        return prev.last_loan_month, prev.last_loan_year
    return None, None


def save_entry(
    session: Session,
    actor: User,
    batch_id: int,
    employee_id: int,
    inputs: LoanInputs,
    last_loan_month: int | None,
    last_loan_year: int | None,
) -> tuple[RenewalEntry, LoanResult]:
    batch = get_batch(session, batch_id)
    _require_draft(batch)
    employee = session.get(Employee, employee_id)
    if employee is None:
        raise ServiceError("Employee not found.")
    if last_loan_month is not None and not 1 <= last_loan_month <= 12:
        raise ServiceError("Last loan month must be 1 to 12.")
    for name in RenewalEntry.INPUT_FIELDS:
        if getattr(inputs, name) < 0:
            raise ServiceError("Amounts cannot be negative.")
    rules = settings.loan_rules(session)
    result = calculate(inputs, rules)

    entry = session.scalar(
        select(RenewalEntry).where(RenewalEntry.batch_id == batch.id, RenewalEntry.employee_id == employee.id)
    )
    action = "entry.update"
    if entry is None:
        position = (session.scalar(select(func.max(RenewalEntry.position)).where(RenewalEntry.batch_id == batch.id)) or 0) + 1
        entry = RenewalEntry(batch_id=batch.id, employee_id=employee.id, position=position)
        session.add(entry)
        action = "entry.create"
    before = {name: str(getattr(entry, name)) for name in RenewalEntry.INPUT_FIELDS} if action == "entry.update" else {}
    entry.apply_inputs(inputs)
    entry.apply_result(result)
    entry.last_loan_month = last_loan_month
    entry.last_loan_year = last_loan_year
    entry.rules_json = json.dumps(rules.as_dict())
    session.flush()
    audit.record(
        session,
        actor.username,
        action,
        "entry",
        entry.id,
        f"{employee.pf_number} in {batch_label(batch)}: loan {format_money(result.loan_approved)}, "
        f"payable {format_money(result.balance_payable)}",
        {"before": before, "inputs": {n: str(getattr(inputs, n)) for n in RenewalEntry.INPUT_FIELDS}},
    )
    return entry, result


def remove_entry(session: Session, actor: User, entry_id: int) -> None:
    entry = session.get(RenewalEntry, entry_id)
    if entry is None:
        raise ServiceError("Entry not found.")
    _require_draft(entry.batch)
    audit.record(
        session, actor.username, "entry.remove", "entry", entry.id,
        f"{entry.employee.pf_number} from {batch_label(entry.batch)}",
        {n: str(getattr(entry, n)) for n in RenewalEntry.INPUT_FIELDS},
    )
    session.delete(entry)


def finalize(session: Session, actor: User, batch_id: int, letter_date: str) -> RenewalBatch:
    batch = get_batch(session, batch_id)
    _require_draft(batch)
    if not batch.entries:
        raise ServiceError("Add at least one employee before finalizing.")
    try:
        datetime.strptime(letter_date, "%d.%m.%Y")
    except ValueError as exc:
        raise ServiceError("Letter date must be dd.mm.yyyy.") from exc
    batch.status = "finalized"
    batch.letter_date = letter_date
    batch.finalized_at = datetime.now()
    batch.finalized_by = actor.username
    audit.record(session, actor.username, "batch.finalize", "batch", batch.id, batch_label(batch))
    return batch


def reopen(session: Session, actor: User, batch_id: int, reason: str) -> RenewalBatch:
    if not actor.is_admin:
        raise PermissionDenied("Only an administrator can reopen a finalized month.")
    if not reason.strip():
        raise ServiceError("A reason is required to reopen a finalized month.")
    batch = get_batch(session, batch_id)
    batch.status = "draft"
    audit.record(session, actor.username, "batch.reopen", "batch", batch.id, f"{batch_label(batch)}: {reason}")
    return batch


def delete_batch(session: Session, actor: User, batch_id: int) -> None:
    batch = get_batch(session, batch_id)
    _require_draft(batch)
    if batch.entries and not actor.is_admin:
        raise PermissionDenied("Only an administrator can delete a month that has entries.")
    audit.record(session, actor.username, "batch.delete", "batch", batch.id, f"{batch_label(batch)} ({len(batch.entries)} entries)")
    session.delete(batch)


def ugc_rows(session: Session, batch: RenewalBatch) -> list[UgcRow]:
    code = settings.get(session, "university_code")
    return [
        UgcRow(
            name=e.employee.name,
            pf_number=e.employee.pf_number,
            nic=e.employee.nic,
            request_month=batch.request_month,
            request_year=batch.request_year,
            last_loan_month=e.last_loan_month,
            last_loan_year=e.last_loan_year,
            loan_approved=e.loan_approved,
            existing_balance=e.existing_loan_balance,
            balance_payable=e.balance_payable,
            university_code=code,
        )
        for e in batch.entries
    ]


def totals(batch: RenewalBatch) -> dict[str, Decimal]:
    keys = ("loan_approved", "existing_loan_balance", "balance_payable", "loan_in_hand")
    return {k: sum((getattr(e, k) for e in batch.entries), Decimal(0)) for k in keys}
