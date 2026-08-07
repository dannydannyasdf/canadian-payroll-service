"""Generate Revenu Québec Relevé 1 e-file XML from stored YTD totals.

Exports validate against the internal preview schema (releve1_efile_preview.xsd).
Official Revenu Québec XSD packages can be added later under schemas/rq/.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import xmlschema
from lxml import etree
from sqlalchemy.orm import Session, joinedload

from app.db_models import EmployeeRecord, YtdRecord
from app.models.tax_slip import Releve1SlipPreview
from app.services.provider_config import (
    PROVIDER_CONTACT_NAME,
    PROVIDER_NAME,
    RQ_EMPLOYER_ID,
)
from app.services.stub_archive_service import EmployeeNotFoundError
from app.services.tax_slip_service import build_releve1_preview

RQ_SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas" / "rq"
RQ_EFILE_PREVIEW_XSD = RQ_SCHEMA_DIR / "releve1_efile_preview.xsd"
RQ_PREVIEW_NS = "https://payroll.example.ca/schema/rq-efile-preview/v1"
RQ_PREVIEW_NSMAP = {None: RQ_PREVIEW_NS}
QC_PROVINCE = "QC"
RELEVE1_BOXES = ("A", "B", "C", "E", "G", "I")


class RqFilingNotFoundError(Exception):
    def __init__(self, tax_year: int) -> None:
        self.tax_year = tax_year
        super().__init__(f"No Relevé 1 filing data found for tax year {tax_year}.")


class RqFilingNotApplicableError(Exception):
    def __init__(self, employee_id: int, province: str) -> None:
        self.employee_id = employee_id
        self.province = province
        super().__init__(
            f"Relevé 1 e-file is not applicable for employee {employee_id} "
            f"with employment province {province!r} (Quebec only)."
        )


def rq_schema_inventory() -> dict[str, object]:
    preview_available = RQ_EFILE_PREVIEW_XSD.is_file()
    return {
        "schemaDir": str(RQ_SCHEMA_DIR),
        "previewSchema": RQ_EFILE_PREVIEW_XSD.name if preview_available else None,
        "officialSchemaAvailable": False,
        "activeValidationSchema": RQ_EFILE_PREVIEW_XSD.name if preview_available else None,
        "rqEmployerIdConfigured": bool(RQ_EMPLOYER_ID),
    }


def _split_employee_name(full_name: str) -> tuple[str, str]:
    parts = full_name.strip().split()
    if len(parts) == 1:
        return parts[0], parts[0]
    return parts[-1], " ".join(parts[:-1])


def _normalize_sin(sin: str) -> str:
    digits = "".join(ch for ch in sin if ch.isdigit())
    return digits.zfill(9)[-9:]


def _money(value: str | Decimal) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _rq_amount(value: str | Decimal) -> str:
    return f"{_money(value):.2f}"


def _employment_province(slip: Releve1SlipPreview) -> str:
    from app.services.provider_config import DEFAULT_EMPLOYMENT_PROVINCE

    province = (
        slip.employee.employmentProvince
        or slip.employee.address.province
        or DEFAULT_EMPLOYMENT_PROVINCE
    )
    return province.upper()


def _append_text(parent: etree._Element, tag: str, value: str | Decimal | int | None) -> None:
    if value is None:
        return
    text = str(value).strip()
    if not text:
        return
    child = etree.SubElement(parent, tag)
    child.text = text


def _sum_boxes(slips: list[Releve1SlipPreview], box: str) -> Decimal:
    return sum((_money(slip.boxes[box]) for slip in slips), Decimal("0.00"))


def _build_transmitter() -> etree._Element:
    transmitter = etree.Element("Transmitter")
    _append_text(transmitter, "name", PROVIDER_NAME)
    _append_text(transmitter, "contactName", PROVIDER_CONTACT_NAME)
    _append_text(transmitter, "rqEmployerId", RQ_EMPLOYER_ID)
    return transmitter


def _build_releve1_amounts(parent: etree._Element, boxes: dict[str, str]) -> None:
    amounts = etree.SubElement(parent, "amounts")
    _append_text(amounts, "boxA", _rq_amount(boxes["A"]))
    _append_text(amounts, "boxB", _rq_amount(boxes["B"]))
    _append_text(amounts, "boxC", _rq_amount(boxes["C"]))
    _append_text(amounts, "boxE", _rq_amount(boxes["E"]))
    _append_text(amounts, "boxG", _rq_amount(boxes["G"]))
    _append_text(amounts, "boxI", _rq_amount(boxes["I"]))


def _build_releve1_slip(slip: Releve1SlipPreview) -> etree._Element:
    surname, given_name = _split_employee_name(slip.employee.name)
    slip_el = etree.Element("Releve1Slip")

    employee_name = etree.SubElement(slip_el, "employeeName")
    _append_text(employee_name, "surname", surname[:20])
    _append_text(employee_name, "givenName", given_name[:12])

    _append_text(slip_el, "sin", _normalize_sin(slip.employee.sin))
    _append_text(slip_el, "reportTypeCode", "O")
    _build_releve1_amounts(slip_el, slip.boxes)
    return slip_el


def _build_releve1_summary(slips: list[Releve1SlipPreview]) -> etree._Element:
    summary = etree.Element("Releve1Summary")
    _append_text(summary, "employerName", slips[0].employer.name[:100])
    _append_text(summary, "rqEmployerId", RQ_EMPLOYER_ID)
    _append_text(summary, "totBoxA", _rq_amount(_sum_boxes(slips, "A")))
    _append_text(summary, "totBoxB", _rq_amount(_sum_boxes(slips, "B")))
    _append_text(summary, "totBoxC", _rq_amount(_sum_boxes(slips, "C")))
    _append_text(summary, "totBoxE", _rq_amount(_sum_boxes(slips, "E")))
    _append_text(summary, "totBoxG", _rq_amount(_sum_boxes(slips, "G")))
    _append_text(summary, "totBoxI", _rq_amount(_sum_boxes(slips, "I")))
    _append_text(summary, "slipCount", len(slips))
    return summary


def build_preview_rq_submission_xml(slips: list[Releve1SlipPreview], tax_year: int) -> str:
    if not slips:
        raise RqFilingNotFoundError(tax_year)

    root = etree.Element("Submission", nsmap=RQ_PREVIEW_NSMAP)
    root.set("taxYear", str(tax_year))
    root.set("status", "preview")
    root.append(_build_transmitter())

    releve_return = etree.SubElement(root, "Releve1Return")
    releve_return.append(_build_releve1_summary(slips))
    for slip in slips:
        releve_return.append(_build_releve1_slip(slip))

    xml_bytes = etree.tostring(
        root,
        xml_declaration=True,
        encoding="UTF-8",
        pretty_print=True,
    )
    return xml_bytes.decode("utf-8")


def validate_preview_rq_efile_xml(xml_text: str) -> None:
    if not RQ_EFILE_PREVIEW_XSD.is_file():
        raise ValueError("Relevé 1 e-file preview schema is not available.")
    schema = xmlschema.XMLSchema(str(RQ_EFILE_PREVIEW_XSD))
    try:
        schema.validate(xml_text)
    except xmlschema.XMLSchemaValidationError as exc:
        raise ValueError(f"Invalid Relevé 1 e-file preview XML: {exc.reason}") from exc


def build_and_validate_rq_submission_xml(
    slips: list[Releve1SlipPreview],
    tax_year: int,
) -> str:
    xml_text = build_preview_rq_submission_xml(slips, tax_year)
    validate_preview_rq_efile_xml(xml_text)
    return xml_text


def _require_quebec_employment(slip: Releve1SlipPreview) -> None:
    province = _employment_province(slip)
    if province != QC_PROVINCE:
        raise RqFilingNotApplicableError(slip.employee.id, province)


def build_employee_releve1_efile_xml(
    db: Session,
    employee_id: int,
    tax_year: int,
) -> str:
    slip = build_releve1_preview(db, employee_id, tax_year)
    _require_quebec_employment(slip)
    return build_and_validate_rq_submission_xml([slip], tax_year)


def build_rq_filing_xml(db: Session, tax_year: int) -> str:
    rows = (
        db.query(YtdRecord)
        .options(joinedload(YtdRecord.employee).joinedload(EmployeeRecord.employer))
        .filter_by(tax_year=tax_year)
        .order_by(YtdRecord.employee_id)
        .all()
    )
    if not rows:
        raise RqFilingNotFoundError(tax_year)

    previews: list[Releve1SlipPreview] = []
    for row in rows:
        slip = build_releve1_preview(db, row.employee_id, tax_year)
        if _employment_province(slip) == QC_PROVINCE:
            previews.append(slip)

    if not previews:
        raise RqFilingNotFoundError(tax_year)

    return build_and_validate_rq_submission_xml(previews, tax_year)
