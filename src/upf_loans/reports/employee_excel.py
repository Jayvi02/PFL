from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

from ..db.models import Employee

HEADERS = ["PF Number", "Name", "NIC", "Department", "Academic/Non-academic", "Designation", "Active"]


def write_employee_workbook(path: Path, employees: list[Employee]) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "Employees"
    ws.append(HEADERS)
    for c in ws[1]:
        c.font = Font(bold=True)
    for e in employees:
        ws.append([e.pf_number, e.name, e.nic, e.department, "Academic" if e.category == "A" else "Non-academic",
                   e.designation, "Yes" if e.is_active else "No"])
    for col, w in zip("ABCDEFG", (12, 36, 16, 28, 20, 28, 8)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    wb.save(path)
    return Path(path)
