"""PDF summary of a renewal month."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..core.money import format_money
from ..db.models import RenewalBatch
from ..services.renewals import batch_label, totals

NAVY = colors.HexColor("#1F3A68")


def write_batch_pdf(path: Path, batch: RenewalBatch, university_name: str) -> Path:
    doc = SimpleDocTemplate(str(path), pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm,
                            topMargin=12 * mm, bottomMargin=12 * mm, title=f"UPF renewals {batch_label(batch)}")
    styles = getSampleStyleSheet()
    story = [
        Paragraph(f"<b>{university_name}</b>", styles["Title"]),
        Paragraph(f"U.P.F. loan renewals for {batch_label(batch)} ({batch.status})", styles["Heading2"]),
        Spacer(1, 4 * mm),
    ]
    head = ["#", "Name", "PF No.", "NIC", "Last loan", "Instalment", "Loan approved", "Existing balance",
            "Balance payable", "Other loans", "Loan in hand"]
    data = [head]
    for i, e in enumerate(batch.entries, start=1):
        last = f"{e.last_loan_month:02d}/{e.last_loan_year}" if e.last_loan_month and e.last_loan_year else ""
        data.append([
            i, e.employee.name, e.employee.pf_number, e.employee.nic, last, format_money(e.instalment),
            format_money(e.loan_approved), format_money(e.existing_loan_balance), format_money(e.balance_payable),
            format_money(e.balance_payable - e.loan_in_hand), format_money(e.loan_in_hand),
        ])
    t = totals(batch)
    data.append(["", "Total", "", "", "", "", format_money(t["loan_approved"]),
                 format_money(t["existing_loan_balance"]), format_money(t["balance_payable"]), "",
                 format_money(t["loan_in_hand"])])
    table = Table(data, repeatRows=1, colWidths=[8 * mm, 62 * mm, 20 * mm, 26 * mm, 18 * mm, 20 * mm,
                                                 26 * mm, 26 * mm, 26 * mm, 20 * mm, 26 * mm])
    table.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 8),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8),
        ("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 8),
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F3F6FB")]),
        ("LINEABOVE", (0, -1), (-1, -1), 0.8, NAVY),
        ("ALIGN", (5, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -2), 0.25, colors.HexColor("#D5DCE8")),
    ]))
    story.append(table)
    doc.build(story)
    return Path(path)
