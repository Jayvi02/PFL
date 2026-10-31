from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import AuditLog


def record(
    session: Session,
    username: str,
    action: str,
    entity: str = "",
    entity_id: int | None = None,
    summary: str = "",
    details: dict | None = None,
) -> None:
    session.add(
        AuditLog(
            username=username,
            action=action,
            entity=entity,
            entity_id=entity_id,
            summary=summary,
            details_json=json.dumps(details or {}, default=str),
        )
    )


def recent(session: Session, limit: int = 50) -> list[AuditLog]:
    return list(session.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)))
