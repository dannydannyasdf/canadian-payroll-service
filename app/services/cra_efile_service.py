"""Generate CRA T4 e-file XML from stored YTD totals.

When the official CRA schema package is present under schemas/cra/, exports validate
against T619_T4.xsd and use CRA element names. Otherwise we fall back to the internal
preview schema (t4_efile_preview.xsd).

Official XSD packages are published by the CRA at:
https://www.canada.ca/en/revenue-agency/services/e-services/filing-information-returns-electronically-t4-t5-other-types-returns-overview/filing-information-returns-electronically-t4-t5-other-types-returns-what-you-should-know-before.html
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

import xmlschema
from lxml import etree
from sqlalchemy.orm import Session, joinedload

from app.db_models import EmployeeRecord, YtdRecord
from app.models.tax_slip import T4SlipPreview
from app.services.stub_archive_service import EmployeeNotFoundError
from app.services.tax_slip_service import build_t4_preview

CRA_SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas" / "cra"
CRA_EFILE_PREVIEW_XSD = CRA_SCHEMA_DIR / "t4_efile_preview.xsd"
CRA_OFFICIAL_SUBMISSION_XSD = CRA_SCHEMA_DIR / "T619_T4.xsd"
CRA_OFFICIAL_T4_XSD = CRA_SCHEMA_DIR / "t4.xsd"
OFFICIAL_CRA_PACKAGE_FILES = ("simple.xsd", "complex.xsd", "t4.xsd", "T619_T4.xsd")
CRA_EFILE_PREVIEW_NS = "https://payroll.example.ca/schema/cra-efile-preview/v1"
CRA_PREVIEW_NSMAP = {None: CRA_EFILE_PREVIEW_NS}

from app.services.provider_config import (
    CONTACT_AREA,
    CONTACT_EMAIL,
    CONTACT_PHONE,
    DEFAULT_EMPLOYMENT_PROVINCE,
    PAYROLL_ACCOUNT_EFILE,
    PROVIDER_CONTACT_NAME,
    PROVIDER_NAME,
    TRANSMITTER_BN9,
    normalize_payroll_account,
)


class CraFilingNotFoundError(Exception):
    def __init__(self, tax_year: int) -> None:
        self.tax_year = tax_year
        super().__init__(f"No YTD totals found for tax year {tax_year}.")


@lru_cache(maxsize=1)
def _get_official_schema() -> xmlschema.XMLSchema | None:
    if not CRA_OFFICIAL_SUBMISSION_XSD.is_file():
        return None
    try:
        return xmlschema.XMLSchema(str(CRA_OFFICIAL_SUBMISSION_XSD))
    except xmlschema.XMLSchemaParseError:
        return None


def official_schema_available() -> bool:
    return _get_official_schema() is not None


def cra_schema_inventory() -> dict[str, object]:
    missing_files = [
        name for name in OFFICIAL_CRA_PACKAGE_FILES if not (CRA_SCHEMA_DIR / name).is_file()
    ]
    official_schema = _get_official_schema()
    official_loadable = official_schema is not None
    official_error: str | None = None

    if not CRA_OFFICIAL_SUBMISSION_XSD.is_file():
        official_error = "Official T619_T4.xsd not found."
    elif missing_files:
        official_error = f"Missing schema files: {', '.join(missing_files)}"
    elif not official_loadable:
        official_error = "Official submission schema failed to load."

    return {
        "schemaDir": str(CRA_SCHEMA_DIR),
        "previewSchema": CRA_EFILE_PREVIEW_XSD.name,
        "officialSubmissionSchema": CRA_OFFICIAL_SUBMISSION_XSD.name,
        "officialT4Schema": CRA_OFFICIAL_T4_XSD.name if CRA_OFFICIAL_T4_XSD.is_file() else None,
        "missingOfficialSchemas": missing_files,
        "officialT4Loadable": official_loadable,
        "officialT4Error": official_error,
        "activeValidationSchema": (
            CRA_OFFICIAL_SUBMISSION_XSD.name if official_loadable else CRA_EFILE_PREVIEW_XSD.name
        ),
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


def _cra_amount(value: str | Decimal) -> str:
    return f"{_money(value):.2f}"


def _payroll_account(slip: T4SlipPreview) -> str:
    raw = slip.employer.payrollAccountNumber or PAYROLL_ACCOUNT_EFILE
    return normalize_payroll_account(raw)


def _employment_province(slip: T4SlipPreview) -> str:
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


def _submission_reference_id() -> str:
    return datetime.now(timezone.utc).strftime("%y%m%d%H")


# --- Official CRA XML ---------------------------------------------------------


def _build_official_t619() -> etree._Element:
    t619 = etree.Element("T619")

    account = etree.SubElement(t619, "TransmitterAccountNumber")
    _append_text(account, "bn9", TRANSMITTER_BN9)

    _append_text(t619, "sbmt_ref_id", _submission_reference_id())
    _append_text(t619, "summ_cnt", 1)
    _append_text(t619, "lang_cd", "E")

    transmitter_name = etree.SubElement(t619, "TransmitterName")
    _append_text(transmitter_name, "l1_nm", PROVIDER_NAME[:35])

    _append_text(t619, "TransmitterCountryCode", "CAN")

    contact = etree.SubElement(t619, "CNTC")
    _append_text(contact, "cntc_nm", PROVIDER_CONTACT_NAME[:35])
    _append_text(contact, "cntc_area_cd", CONTACT_AREA)
    _append_text(contact, "cntc_phn_nbr", CONTACT_PHONE)
    _append_text(contact, "cntc_email_area", CONTACT_EMAIL[:60])

    return t619


def _build_official_t4_amt(boxes: dict[str, str], province: str) -> etree._Element:
    amounts = etree.Element("T4_AMT")
    _append_text(amounts, "empt_incamt", _cra_amount(boxes["14"]))

    pension_amount = _cra_amount(boxes["16"])
    if province == "QC":
        _append_text(amounts, "qpp_cntrb_amt", pension_amount)
    else:
        _append_text(amounts, "cpp_cntrb_amt", pension_amount)

    _append_text(amounts, "empe_eip_amt", _cra_amount(boxes["18"]))
    _append_text(amounts, "itx_ddct_amt", _cra_amount(boxes["22"]))
    _append_text(amounts, "ei_insu_ern_amt", _cra_amount(boxes["24"]))
    _append_text(amounts, "cpp_qpp_ern_amt", _cra_amount(boxes["26"]))
    return amounts


def _build_official_t4_slip(slip: T4SlipPreview) -> etree._Element:
    surname, given_name = _split_employee_name(slip.employee.name)
    province = _employment_province(slip)
    payroll_account = _payroll_account(slip)

    slip_el = etree.Element("T4Slip")

    employee_name = etree.SubElement(slip_el, "EMPE_NM")
    _append_text(employee_name, "snm", surname[:20])
    _append_text(employee_name, "gvn_nm", given_name[:12])

    _append_text(slip_el, "sin", _normalize_sin(slip.employee.sin))
    _append_text(slip_el, "bn", payroll_account)
    _append_text(slip_el, "cpp_qpp_xmpt_cd", 0)
    _append_text(slip_el, "ei_xmpt_cd", 0)
    # TODO: support Amended (A) and Cancel (C) via rpt_tcd — see slipDataType in simple.xsd
    _append_text(slip_el, "rpt_tcd", "O")
    _append_text(slip_el, "empt_prov_cd", province)
    _append_text(slip_el, "empr_dntl_ben_rpt_cd", os.environ.get("PAYROLL_CRA_DENTAL_CODE", "1"))

    slip_el.append(_build_official_t4_amt(slip.boxes, province))
    return slip_el


def _sum_boxes(slips: list[T4SlipPreview], box: str) -> Decimal:
    return sum((_money(slip.boxes[box]) for slip in slips), Decimal("0.00"))


def _sum_pension(slips: list[T4SlipPreview]) -> Decimal:
    return _sum_boxes(slips, "16")


def _build_official_t4_summary(slips: list[T4SlipPreview], tax_year: int) -> etree._Element:
    employer = slips[0].employer
    payroll_account = _payroll_account(slips[0])

    summary = etree.Element("T4Summary")
    _append_text(summary, "bn", payroll_account)

    employer_name = etree.SubElement(summary, "EMPR_NM")
    _append_text(employer_name, "l1_nm", employer.name[:100])

    contact = etree.SubElement(summary, "CNTC")
    _append_text(contact, "cntc_nm", PROVIDER_CONTACT_NAME[:100])
    _append_text(contact, "cntc_area_cd", CONTACT_AREA)
    _append_text(contact, "cntc_phn_nbr", CONTACT_PHONE)

    _append_text(summary, "tx_yr", tax_year)
    _append_text(summary, "slp_cnt", len(slips))
    _append_text(summary, "rpt_tcd", "O")

    totals = etree.SubElement(summary, "T4_TAMT")
    _append_text(totals, "tot_empt_incamt", _cra_amount(_sum_boxes(slips, "14")))
    _append_text(totals, "tot_empe_cpp_amt", _cra_amount(_sum_pension(slips)))
    _append_text(totals, "tot_empe_eip_amt", _cra_amount(_sum_boxes(slips, "18")))
    _append_text(totals, "tot_itx_ddct_amt", _cra_amount(_sum_boxes(slips, "22")))

    return summary


def build_official_cra_submission_xml(slips: list[T4SlipPreview], tax_year: int) -> str:
    if not slips:
        raise CraFilingNotFoundError(tax_year)

    root = etree.Element("Submission")
    root.append(_build_official_t619())

    return_el = etree.SubElement(root, "Return")
    t4_return = etree.SubElement(return_el, "T4")

    for slip in slips:
        t4_return.append(_build_official_t4_slip(slip))
    t4_return.append(_build_official_t4_summary(slips, tax_year))

    xml_bytes = etree.tostring(
        root,
        xml_declaration=True,
        encoding="UTF-8",
        pretty_print=True,
    )
    return xml_bytes.decode("utf-8")


def validate_official_cra_efile_xml(xml_text: str) -> None:
    schema = _get_official_schema()
    if schema is None:
        raise ValueError("Official CRA submission schema is not available.")
    try:
        schema.validate(xml_text)
    except xmlschema.XMLSchemaValidationError as exc:
        raise ValueError(f"Invalid official CRA e-file XML: {exc.reason}") from exc


# --- Preview XML (fallback) ---------------------------------------------------


def _build_preview_amounts(parent: etree._Element, boxes: dict[str, str], province: str) -> None:
    amounts = etree.SubElement(parent, "amounts")
    _append_text(amounts, "emptIncamt", _cra_amount(boxes["14"]))

    pension_amount = _cra_amount(boxes["16"])
    if province == "QC":
        _append_text(amounts, "qppCntrbAmt", pension_amount)
    else:
        _append_text(amounts, "cppCntrbAmt", pension_amount)

    _append_text(amounts, "empeEipAmt", _cra_amount(boxes["18"]))
    _append_text(amounts, "itxDdctAmt", _cra_amount(boxes["22"]))
    _append_text(amounts, "eiInsuErnAmt", _cra_amount(boxes["24"]))
    _append_text(amounts, "cppQppErnAmt", _cra_amount(boxes["26"]))


def _build_preview_t4_slip(slip: T4SlipPreview) -> etree._Element:
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
    _build_preview_amounts(slip_el, slip.boxes, province)
    return slip_el


def build_preview_cra_submission_xml(slips: list[T4SlipPreview], tax_year: int) -> str:
    if not slips:
        raise CraFilingNotFoundError(tax_year)

    root = etree.Element("Submission", nsmap=CRA_PREVIEW_NSMAP)
    root.set("taxYear", str(tax_year))
    root.set("status", "preview")

    t619 = etree.SubElement(root, "T619")
    _append_text(t619, "transmitterName", PROVIDER_NAME)
    _append_text(t619, "contactName", PROVIDER_CONTACT_NAME)

    t4_return = etree.SubElement(root, "T4Return")
    summary = etree.SubElement(t4_return, "T4Summary")
    _append_text(summary, "payrollAccountNumber", _payroll_account(slips[0]))
    _append_text(summary, "totEmptIncamt", _cra_amount(_sum_boxes(slips, "14")))

    pension_total = _sum_pension(slips)
    if _employment_province(slips[0]) == "QC":
        _append_text(summary, "totQppCntrbAmt", _cra_amount(pension_total))
    else:
        _append_text(summary, "totCppCntrbAmt", _cra_amount(pension_total))

    _append_text(summary, "totEmpeEipAmt", _cra_amount(_sum_boxes(slips, "18")))
    _append_text(summary, "totItxDdctAmt", _cra_amount(_sum_boxes(slips, "22")))
    _append_text(summary, "totEiInsuErnAmt", _cra_amount(_sum_boxes(slips, "24")))
    _append_text(summary, "totCppQppErnAmt", _cra_amount(_sum_boxes(slips, "26")))
    _append_text(summary, "slipCount", len(slips))

    for slip in slips:
        t4_return.append(_build_preview_t4_slip(slip))

    xml_bytes = etree.tostring(
        root,
        xml_declaration=True,
        encoding="UTF-8",
        pretty_print=True,
    )
    return xml_bytes.decode("utf-8")


def validate_preview_cra_efile_xml(xml_text: str) -> None:
    schema = xmlschema.XMLSchema(str(CRA_EFILE_PREVIEW_XSD))
    try:
        schema.validate(xml_text)
    except xmlschema.XMLSchemaValidationError as exc:
        raise ValueError(f"Invalid CRA e-file preview XML: {exc.reason}") from exc


# --- Public API ---------------------------------------------------------------


def build_and_validate_cra_submission_xml(
    slips: list[T4SlipPreview],
    tax_year: int,
    *,
    official: bool | None = None,
) -> str:
    use_official = official_schema_available() if official is None else official

    if use_official:
        xml_text = build_official_cra_submission_xml(slips, tax_year)
        validate_official_cra_efile_xml(xml_text)
        return xml_text

    xml_text = build_preview_cra_submission_xml(slips, tax_year)
    validate_preview_cra_efile_xml(xml_text)
    return xml_text


def build_employee_t4_efile_xml(
    db: Session,
    employee_id: int,
    tax_year: int,
    *,
    official: bool | None = None,
) -> str:
    slip = build_t4_preview(db, employee_id, tax_year)
    return build_and_validate_cra_submission_xml([slip], tax_year, official=official)


def build_cra_filing_xml(
    db: Session,
    tax_year: int,
    *,
    official: bool | None = None,
) -> str:
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
    return build_and_validate_cra_submission_xml(previews, tax_year, official=official)
