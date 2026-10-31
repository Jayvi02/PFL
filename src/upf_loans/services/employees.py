"""Employee records."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..core.validation import normalise_nic, normalise_pf_number, validate_nic, validate_pf_number
from ..db.models import Employee, RenewalEntry
from . import audit
from .errors import ServiceError

EDITABLE = ("pf_number", "name", "nic", "department", "category", "designation", "is_active")


@dataclass
class EmployeeData:
    pf_number: str
    name: str
    nic: str
    department: str = ""
    category: str = "N"
    designation: str = ""
    is_active: bool = True

    def cleaned(self) -> "EmployeeData":
        return EmployeeData(
            pf_number=normalise_pf_number(self.pf_number),
            name=" ".join((self.name or "").split()).upper(),
            nic=normalise_nic(self.nic),
            department=(self.department or "").strip(),
            category=(self.category or "N").strip().upper()[:1] or "N",
            designation=(self.designation or "").strip(),
            is_active=bool(self.is_active),
        )


def validate(session: Session, data: EmployeeData, employee_id: int | None = None) -> dict[str, str]:
    errors: dict[str, str] = {}
    if msg := validate_pf_number(data.pf_number):
        errors["pf_number"] = msg
    if not data.name:
        errors["name"] = "Name is required."
    elif len(data.name) > 50:
        errors["name"] = "Name must be at most 50 characters (UGC limit)."
    if msg := validate_nic(data.nic):
        errors["nic"] = msg
    if data.category not in ("A", "N"):
        errors["category"] = "Category must be A (academic) or N (non-academic)."
    if "pf_number" not in errors:
        clash = session.scalar(select(Employee).where(Employee.pf_number == data.pf_number))
        if clash and clash.id != employee_id:
            errors["pf_number"] = f"PF number already belongs to {clash.name}."
    return errors


def duplicate_nic(session: Session, nic: str, employee_id: int | None = None) -> Employee | None:
    for emp in session.scalars(select(Employee).where(Employee.nic == nic)):
        if emp.id != employee_id:
            return emp
    return None


def save(session: Session, actor: str, data: EmployeeData, employee_id: int | None = None) -> Employee:
    data = data.cleaned()
    errors = validate(session, data, employee_id)
    if errors:
        raise ServiceError("\n".join(errors.values()))
    if employee_id is None:
        emp = Employee(**{k: getattr(data, k) for k in EDITABLE})
        session.add(emp)
        session.flush()
        audit.record(session, actor, "employee.create", "employee", emp.id, f"{emp.pf_number} {emp.name}")
        return emp
    emp = session.get(Employee, employee_id)
    if emp is None:
        raise ServiceError("Employee not found.")
    changes = {}
    for key in EDITABLE:
        new = getattr(data, key)
        if getattr(emp, key) != new:
            changes[key] = {"from": getattr(emp, key), "to": new}
            setattr(emp, key, new)
    if changes:
        audit.record(session, actor, "employee.update", "employee", emp.id, emp.pf_number, changes)
    return emp


def search(session: Session, text: str = "", include_inactive: bool = True) -> list[Employee]:
    stmt = select(Employee).order_by(Employee.name)
    if text:
        like = f"%{text.strip()}%"
        stmt = stmt.where(or_(Employee.name.ilike(like), Employee.pf_number.ilike(like), Employee.nic.ilike(like)))
    if not include_inactive:
        stmt = stmt.where(Employee.is_active.is_(True))
    return list(session.scalars(stmt))


def history(session: Session, employee_id: int) -> list[RenewalEntry]:
    from ..db.models import RenewalBatch

    stmt = (
        select(RenewalEntry)
        .join(RenewalBatch)
        .where(RenewalEntry.employee_id == employee_id)
        .order_by(RenewalBatch.request_year.desc(), RenewalBatch.request_month.desc())
    )
    return list(session.scalars(stmt))
