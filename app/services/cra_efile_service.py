"""Generate CRA T4 e-file preview XML from stored YTD totals.

Validation uses our internal preview schema (schemas/cra/t4_efile_preview.xsd).

The official CRA T4 slip/summary schema lives at schemas/cra/t4.xsd (v1.26). It
is one file from the CRA XML package and depends on sibling XSDs such as
simple.xsd, complex.xsd, and t619.xsd before it can validate a full submission.
"""

from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path

import xmlschema
from lxml import etree
from sqlalchemy.orm import Session, joinedload

from app.db_models import EmployeeRecord, YtdRecord
from app.models.tax_slip import T4SlipPreview
from app.services.stub_archive_service import EmployeeNotFoundError
from app.services.tax_slip_service import build_t4_preview

CRA_SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas" / "cra"
CRA_EFILE_XSD = CRA_SCHEMA_DIR / "t4_efile_preview.xsd"
CRA_OFFICIAL_T4_XSD = CRA_SCHEMA_DIR / "t4.xsd"
OFFICIAL_CRA_SIBLING_SCHEMAS = ("simple.xsd", "complex.xsd", "t619.xsd")
CRA_EFILE_NS = "https://payroll.example.ca/schema/cra-efile-preview/v1"
NSMAP = {None: CRA_EFILE_NS}

DEFAULT_PAYROLL_ACCOUNT = os.environ.get("PAYROLL_CRA_PAYROLL_ACCOUNT", "000000000RP0000")
DEFAULT_PROVINCE = os.environ.get("PAYROLL_DEFAULT_EMPLOYMENT_PROVINCE", "QC")
TRANSMITTER_NAME = os.environ.get("PAYROLL_PROVIDER_NAME", "Gamma Personnel Inc.")
CONTACT_NAME = os.environ.get("PAYROLL_PROVIDER_CONTACT_NAME", "Danny Majerovich")

CRA_EFILE_DISCLAIMERS = (
    "Preview XML only — not valid for CRA Internet File Transfer.",
    "Replace with the official CRA XSD package before production filing.",
    "Optional empty fields are omitted per CRA validation guidance.",
)


class CraFilingNotFoundError(Exception):
    def __init__(self, tax_year: int) -> None:
        self.tax_year = tax_year
        super().__init__(f"No YTD totals found for tax year {tax_year}.")


def cra_schema_inventory() -> dict[str, object]:
    """Report which CRA schema files are present under schemas/cra/."""
    missing_siblings = [
        name for name in OFFICIAL_CRA_SIBLING_SCHEMAS if not (CRA_SCHEMA_DIR / name).is_file()
    ]
    official_t4_loadable = False
    official_t4_error: str | None = None

    if CRA_OFFICIAL_T4_XSD.is_file() and not missing_siblings:
        try:
            xmlschema.XMLSchema(str(CRA_OFFICIAL_T4_XSD))
            official_t4_loadable = True
        except xmlschema.XMLSchemaParseError as exc:
            official_t4_error = str(exc)
    elif CRA_OFFICIAL_T4_XSD.is_file():
        official_t4_error = f"Missing sibling schemas: {', '.join(missing_siblings)}"
    else:
        official_t4_error = "Official t4.xsd not found."

    return {
        "schemaDir": str(CRA_SCHEMA_DIR),
        "previewSchema": CRA_EFILE_XSD.name,
        "officialT4Schema": CRA_OFFICIAL_T4_XSD.name if CRA_OFFICIAL_T4_XSD.is_file() else None,
        "missingOfficialSchemas": missing_siblings,
        "officialT4Loadable": official_t4_loadable,
        "officialT4Error": official_t4_error,
        "activeValidationSchema": CRA_EFILE_XSD.name,
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


def _payroll_account(slip: T4SlipPreview) -> str:
    return slip.employer.payrollAccountNumber or DEFAULT_PAYROLL_ACCOUNT


def _employment_province(slip: T4SlipPreview) -> str:
    province = slip.employee.address.province or slip.employer.address.province or DEFAULT_PROVINCE
    return province.upper()


def _append_text(parent: etree._Element, tag: str, value: str | Decimal | None) -> None:
    if value is None:
        return
    text = str(value).strip()
    if not text:
        return
    child = etree.SubElement(parent, tag)
    child.text = text


def _append_amounts(parent: etree._Element, boxes: dict[str, str], province: str) -> None:
    amounts = etree.SubElement(parent, "amounts")
    _append_text(amounts, "emptIncamt", _money(boxes["14"]))

    pension_amount = _money(boxes["16"])
    if province == "QC":
        _append_text(amounts, "qppCntrbAmt", pension_amount)
    else:
        _append_text(amounts, "cppCntrbAmt", pension_amount)

    _append_text(amounts, "empeEipAmt", _money(boxes["18"]))
    _append_text(amounts, "itxDdctAmt", _money(boxes["22"]))
    _append_text(amounts, "eiInsuErnAmt", _money(boxes["24"]))
    _append_text(amounts, "cppQppErnAmt", _money(boxes["26"]))


def _build_t4_slip_element(slip: T4SlipPreview) -> etree._Element:
    surname, given_name = _split_employee_name(slip.employee.name)
    province = _employment_province(slip)

    slip_el = etree.Element("T4Slip")
    employee_name = etree.SubElement(slip_el, "employeeName")
    _append_text(employee_name, "surname", surname[:20])
    _append_text(employee_name, "givenName", given_name[:12])
    _append_text(slip_el, "sin", _normalize_sin(slip.employee.sin))
    _append_text(slip_el, "payrollAccountNumber", _payroll_account(slip))
    _append_text(slip_el, "reportTypeCode", "O")
    _append_text(slip_el, "employmentProvinceCode", province)
    _append_amounts(slip_el, slip.boxes, province)
    return slip_el


def _sum_boxes(slips: list[T4SlipPreview], box: str) -> Decimal:
    total = Decimal("0.00")
    for slip in slips:
        total += _money(slip.boxes[box])
    return total


def _sum_pension(slips: list[T4SlipPreview]) -> tuple[Decimal, Decimal]:
    cpp_total = Decimal("0.00")
    qpp_total = Decimal("0.00")
    for slip in slips:
        amount = _money(slip.boxes["16"])
        if _employment_province(slip) == "QC":
            qpp_total += amount
        else:
            cpp_total += amount
    return cpp_total, qpp_total


def build_cra_submission_xml(slips: list[T4SlipPreview], tax_year: int) -> str:
    if not slips:
        raise CraFilingNotFoundError(tax_year)

    root = etree.Element("Submission", nsmap=NSMAP)
    root.set("taxYear", str(tax_year))
    root.set("status", "preview")

    t619 = etree.SubElement(root, "T619")
    _append_text(t619, "transmitterName", TRANSMITTER_NAME)
    _append_text(t619, "contactName", CONTACT_NAME)

    t4_return = etree.SubElement(root, "T4Return")
    summary = etree.SubElement(t4_return, "T4Summary")
    _append_text(summary, "payrollAccountNumber", _payroll_account(slips[0]))
    _append_text(summary, "totEmptIncamt", _sum_boxes(slips, "14"))

    cpp_total, qpp_total = _sum_pension(slips)
    if cpp_total > 0:
        _append_text(summary, "totCppCntrbAmt", cpp_total)
    if qpp_total > 0:
        _append_text(summary, "totQppCntrbAmt", qpp_total)

    _append_text(summary, "totEmpeEipAmt", _sum_boxes(slips, "18"))
    _append_text(summary, "totItxDdctAmt", _sum_boxes(slips, "22"))
    _append_text(summary, "totEiInsuErnAmt", _sum_boxes(slips, "24"))
    _append_text(summary, "totCppQppErnAmt", _sum_boxes(slips, "26"))
    _append_text(summary, "slipCount", len(slips))

    for slip in slips:
        t4_return.append(_build_t4_slip_element(slip))

    xml_bytes = etree.tostring(
        root,
        xml_declaration=True,
        encoding="UTF-8",
        pretty_print=True,
    )
    return xml_bytes.decode("utf-8")


def validate_cra_efile_xml(xml_text: str) -> None:
    schema = xmlschema.XMLSchema(str(CRA_EFILE_XSD))
    try:
        schema.validate(xml_text)
    except xmlschema.XMLSchemaValidationError as exc:
        raise ValueError(f"Invalid CRA e-file preview XML: {exc.reason}") from exc


def build_and_validate_cra_submission_xml(slips: list[T4SlipPreview], tax_year: int) -> str:
    xml_text = build_cra_submission_xml(slips, tax_year)
    validate_cra_efile_xml(xml_text)
    return xml_text


def build_employee_t4_efile_xml(db: Session, employee_id: int, tax_year: int) -> str:
    slip = build_t4_preview(db, employee_id, tax_year)
    return build_and_validate_cra_submission_xml([slip], tax_year)


def build_cra_filing_xml(db: Session, tax_year: int) -> str:
    rows = (
        db.query(YtdRecord)
        .options(joinedload(YtdRecord.employee).joinedload(EmployeeRecord.employer))
        .filter_by(tax_year=tax_year)
        .order_by(YtdRecord.employee_id)
        .all()
    )
    if not rows:
        raise CraFilingNotFoundError(tax_year)

    previews = [build_t4_preview(db, row.employee_id, tax_year) for row in rows]
    return build_and_validate_cra_submission_xml(previews, tax_year)
