"""File exports for a renewal month."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from sqlalchemy.orm import Session

from ..core.ugc_text import build_file, build_sheet_text
from ..reports.calculation_excel import write_calculation_workbook
from ..reports.pdf import write_batch_pdf
from ..reports.ugc_excel import title_text, write_ugc_workbook
from . import audit, renewals, settings
from .errors import ServiceError


def check_ugc_text(session: Session, batch_id: int) -> list[str]:
    batch = renewals.get_batch(session, batch_id)
    _, errors = build_file(renewals.ugc_rows(session, batch))
    return errors


def export_ugc_text(session: Session, actor: str, batch_id: int, path: Path) -> Path:
    batch = renewals.get_batch(session, batch_id)
    if not batch.entries:
        raise ServiceError("This month has no employees.")
    ending = "\r\n" if settings.get(session, "text_line_ending") == "CRLF" else "\n"
    s = settings.get_all(session)
    text, errors = build_sheet_text(renewals.ugc_rows(session, batch), title_text(date.today().month),
                                    s["university_name"], s["signatory_title"], batch.letter_date, ending)
    if errors:
        raise ServiceError("The UGC text file was not created:\n" + "\n".join(errors))
    Path(path).write_bytes(text.encode("cp1252"))
    audit.record(session, actor, "export.ugc_text", "batch", batch.id,
                 f"{renewals.batch_label(batch)} -> {Path(path).name}")
    return Path(path)


def export_ugc_excel(session: Session, actor: str, batch_id: int, path: Path) -> Path:
    batch = renewals.get_batch(session, batch_id)
    s = settings.get_all(session)
    write_ugc_workbook(path, renewals.ugc_rows(session, batch), date.today().month, s["university_name"],
                       s["signatory_title"], batch.letter_date)
    audit.record(session, actor, "export.ugc_excel", "batch", batch.id,
                 f"{renewals.batch_label(batch)} -> {Path(path).name}")
    return Path(path)


def export_calculation_excel(session: Session, actor: str, batch_id: int, path: Path) -> Path:
    batch = renewals.get_batch(session, batch_id)
    title = f"{renewals.batch_label(batch).upper()}  PF LOAN - {settings.get(session, 'university_name')}"
    write_calculation_workbook(path, batch, settings.loan_rules(session), title)
    audit.record(session, actor, "export.calculation_excel", "batch", batch.id, Path(path).name)
    return Path(path)


def export_pdf(session: Session, actor: str, batch_id: int, path: Path) -> Path:
    batch = renewals.get_batch(session, batch_id)
    write_batch_pdf(path, batch, settings.get(session, "university_name"))
    audit.record(session, actor, "export.pdf", "batch", batch.id, Path(path).name)
    return Path(path)


def default_filename(session: Session, batch_id: int, kind: str) -> str:
    batch = renewals.get_batch(session, batch_id)
    stem = f"UPF_renewal_{batch.request_year}_{batch.request_month:02d}"
    return {"text": f"{stem}.txt", "excel": f"{stem}_UGC.xlsx", "calc": f"{stem}_calculation.xlsx",
            "pdf": f"{stem}.pdf"}[kind]
