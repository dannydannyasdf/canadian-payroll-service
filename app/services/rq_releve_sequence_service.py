"""Allocate and persist official Relevé 1 slip numbers (NoReleve)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db_models import RqReleveSequence, YtdRecord
from app.rq_releve_number import format_releve_number
from app.services.provider_config import RQ_RELEVE_SEQ_BASE
from app.services.tax_slip_service import YtdNotFoundError


def ensure_rq_releve_no(db: Session, employee_id: int, tax_year: int) -> str:
    """Return the persisted 9-digit NoReleve for an employee/tax year, allocating if needed."""
    ytd = (
        db.query(YtdRecord)
        .filter_by(employee_id=employee_id, tax_year=tax_year)
        .one_or_none()
    )
    if ytd is None:
        raise YtdNotFoundError(employee_id, tax_year)

    if ytd.rq_releve_no:
        return ytd.rq_releve_no

    counter = db.query(RqReleveSequence).filter_by(id=1).one_or_none()
    if counter is None:
        counter = RqReleveSequence(id=1, next_base=RQ_RELEVE_SEQ_BASE)
        db.add(counter)
        db.flush()

    base8 = counter.next_base
    releve_no = format_releve_number(base8)
    ytd.rq_releve_no = releve_no
    counter.next_base = base8 + 1
    db.commit()
    db.refresh(ytd)
    return releve_no
