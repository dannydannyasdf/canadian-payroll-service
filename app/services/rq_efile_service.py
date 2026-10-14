"""Generate Revenu Québec Relevé 1 e-file XML from stored YTD totals.

When the official schema package is present under schemas/rq/, exports validate
against Transmission.xsd and use Revenu Québec element names. Otherwise we fall
back to the internal preview schema (releve1_efile_preview.xsd).
"""

from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from pathlib import Path

import xmlschema
from lxml import etree
from sqlalchemy.orm import Session, joinedload

from app.db_models import EmployeeRecord, YtdRecord
from app.models.tax_slip import Releve1SlipPreview, TaxPartyAddress
from app.services.provider_config import (
    CONTACT_AREA,
    CONTACT_EMAIL,
    CONTACT_PHONE,
    DEFAULT_EMPLOYMENT_PROVINCE,
    PROVIDER_ADDRESS_LINE1,
    PROVIDER_CITY,
    PROVIDER_CONTACT_NAME,
    PROVIDER_NAME,
    PROVIDER_POSTAL_CODE,
    PROVIDER_PROVINCE,
    RQ_CERTIFICATION_NO,
    RQ_DOSSIER_NO,
    RQ_EMPLOYER_ID,
    RQ_NEQ,
    RQ_PARTNER_ID,
    RQ_PREPARATEUR_NO,
    RQ_PRODUCT_ID,
    RQ_SCHEMA_VERSION,
    RQ_SOFTWARE_NAME,
    RQ_SOFTWARE_VERSION,
)
from app.services.rq_releve_sequence_service import ensure_rq_releve_no
from app.services.stub_archive_service import EmployeeNotFoundError
from app.services.tax_slip_service import build_releve1_preview

RQ_SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas" / "rq"
RQ_EFILE_PREVIEW_XSD = RQ_SCHEMA_DIR / "releve1_efile_preview.xsd"
RQ_OFFICIAL_TRANSMISSION_XSD = RQ_SCHEMA_DIR / "Transmission.xsd"
OFFICIAL_RQ_PACKAGE_FILES = ("Transmission.xsd", "P.xsd", "Groupes.xsd", "R01.xsd", "T01.xsd")
RQ_PREVIEW_NS = "https://payroll.example.ca/schema/rq-efile-preview/v1"
RQ_PREVIEW_NSMAP = {None: RQ_PREVIEW_NS}
RQ_OFFICIAL_NS = "http://www.mrq.gouv.qc.ca/T5"
RQ_OFFICIAL_NSMAP = {None: RQ_OFFICIAL_NS}
QC_PROVINCE = "QC"


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


@lru_cache(maxsize=1)
def _get_official_schema() -> xmlschema.XMLSchema | None:
    if not RQ_OFFICIAL_TRANSMISSION_XSD.is_file():
        return None
    try:
        return xmlschema.XMLSchema(str(RQ_OFFICIAL_TRANSMISSION_XSD))
    except xmlschema.XMLSchemaParseError:
        return None


def official_schema_available() -> bool:
    return _get_official_schema() is not None


def rq_schema_inventory() -> dict[str, object]:
    missing_files = [
        name for name in OFFICIAL_RQ_PACKAGE_FILES if not (RQ_SCHEMA_DIR / name).is_file()
    ]
    official_schema = _get_official_schema()
    official_loadable = official_schema is not None
    official_error: str | None = None

    if not RQ_OFFICIAL_TRANSMISSION_XSD.is_file():
        official_error = "Official Transmission.xsd not found."
    elif missing_files:
        official_error = f"Missing schema files: {', '.join(missing_files)}"
    elif not official_loadable:
        official_error = "Official transmission schema failed to load."

    preview_available = RQ_EFILE_PREVIEW_XSD.is_file()
    return {
        "schemaDir": str(RQ_SCHEMA_DIR),
        "previewSchema": RQ_EFILE_PREVIEW_XSD.name if preview_available else None,
        "officialTransmissionSchema": (
            RQ_OFFICIAL_TRANSMISSION_XSD.name if RQ_OFFICIAL_TRANSMISSION_XSD.is_file() else None
        ),
        "officialSchemaVersion": RQ_SCHEMA_VERSION if official_loadable else None,
        "missingOfficialSchemas": missing_files,
        "officialSchemaAvailable": official_loadable,
        "officialSchemaError": official_error,
        "activeValidationSchema": (
            RQ_OFFICIAL_TRANSMISSION_XSD.name
            if official_loadable
            else (RQ_EFILE_PREVIEW_XSD.name if preview_available else None)
        ),
        "rqEmployerIdConfigured": bool(RQ_EMPLOYER_ID),
        "rqPartnerIdConfigured": bool(RQ_PARTNER_ID),
    }


def _split_employee_name(full_name: str) -> tuple[str, str]:
    parts = full_name.strip().split()
    if len(parts) == 1:
        return parts[0], parts[0]
    return parts[-1], " ".join(parts[:-1])


def _split_name_lines(name: str, *, max_len: int = 30) -> tuple[str, str | None]:
    text = name.strip()
    if len(text) <= max_len:
        return text, None
    split_at = text.rfind(" ", 0, max_len + 1)
    if split_at <= 0:
        return text[:max_len], text[max_len : max_len * 2] or None
    first = text[:split_at].strip()
    second = text[split_at:].strip() or None
    if second and len(second) > max_len:
        second = second[:max_len]
    return first, second


def _normalize_sin(sin: str) -> str:
    digits = "".join(ch for ch in sin if ch.isdigit())
    return digits.zfill(9)[-9:]


def _money(value: str | Decimal) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _rq_amount(value: str | Decimal) -> str:
    return f"{_money(value):.2f}"


def _rq_official_amount(value: str | Decimal) -> str:
    return _rq_amount(value).replace(".", ",")


def _postal_code(value: str | None) -> str | None:
    if not value:
        return None
    return value.replace(" ", "").upper()


def _employment_province(slip: Releve1SlipPreview) -> str:
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


def _append_address(parent: etree._Element, address: TaxPartyAddress, *, fallback_line1: str) -> None:
    adresse = etree.SubElement(parent, "Adresse")
    _append_text(adresse, "Ligne1", (address.line1 or fallback_line1)[:30])
    if address.city:
        _append_text(adresse, "Ville", address.city[:30])
    if address.province:
        _append_text(adresse, "Province", address.province[:20])
    postal_code = _postal_code(address.postalCode)
    if postal_code:
        _append_text(adresse, "CodePostal", postal_code)


def _releve_number(slip: Releve1SlipPreview) -> str:
    if slip.releveNumber:
        return slip.releveNumber
    return f"{slip.taxYear % 100:02d}{slip.employee.id:07d}"


def _prepare_official_slips(db: Session, slips: list[Releve1SlipPreview]) -> list[Releve1SlipPreview]:
    prepared: list[Releve1SlipPreview] = []
    for slip in slips:
        releve_no = ensure_rq_releve_no(db, slip.employee.id, slip.taxYear)
        prepared.append(slip.model_copy(update={"releveNumber": releve_no}))
    return prepared


def _sum_boxes(slips: list[Releve1SlipPreview], box: str) -> Decimal:
    return sum((_money(slip.boxes[box]) for slip in slips), Decimal("0.00"))


# --- Official Revenu Québec XML ------------------------------------------------


def _build_official_p_block(tax_year: int) -> etree._Element:
    p = etree.Element("P")
    _append_text(p, "Annee", str(tax_year))
    _append_text(p, "TypeEnvoi", "1")

    preparateur = etree.SubElement(p, "Preparateur")
    _append_text(preparateur, "No", RQ_PREPARATEUR_NO)
    _append_text(preparateur, "Type", "1")
    nom1, nom2 = _split_name_lines(PROVIDER_NAME)
    _append_text(preparateur, "Nom1", nom1)
    if nom2:
        _append_text(preparateur, "Nom2", nom2)
    adresse = etree.SubElement(preparateur, "Adresse")
    _append_text(adresse, "Ligne1", PROVIDER_ADDRESS_LINE1[:30])
    _append_text(adresse, "Ville", PROVIDER_CITY[:30])
    _append_text(adresse, "Province", PROVIDER_PROVINCE[:20])
    _append_text(adresse, "CodePostal", _postal_code(PROVIDER_POSTAL_CODE))

    informatique = etree.SubElement(p, "Informatique")
    _append_text(informatique, "Nom", PROVIDER_CONTACT_NAME[:30])
    _append_text(informatique, "IndRegional", CONTACT_AREA)
    _append_text(informatique, "Tel", CONTACT_PHONE)

    comptabilite = etree.SubElement(p, "Comptabilite")
    _append_text(comptabilite, "Nom", PROVIDER_CONTACT_NAME[:30])
    _append_text(comptabilite, "IndRegional", CONTACT_AREA)
    _append_text(comptabilite, "Tel", CONTACT_PHONE)

    _append_text(p, "NoCertification", RQ_CERTIFICATION_NO)
    _append_text(p, "NomLogiciel", RQ_SOFTWARE_NAME[:40])
    _append_text(p, "VersionLogiciel", RQ_SOFTWARE_VERSION[:15])
    _append_text(p, "CourrielResponsable", CONTACT_EMAIL[:60])
    _append_text(p, "IdPartenaireReleves", RQ_PARTNER_ID)
    _append_text(p, "IdProduitReleves", RQ_PRODUCT_ID)
    return p


def _build_official_montants(parent: etree._Element, boxes: dict[str, str]) -> None:
    montants = etree.SubElement(parent, "Montants")
    _append_text(montants, "A_RevenuEmploi", _rq_official_amount(boxes["A"]))
    _append_text(montants, "BA_CotisationRRQ", _rq_official_amount(boxes["B"]))
    _append_text(montants, "C_CotisationAssEmploi", _rq_official_amount(boxes["C"]))
    _append_text(montants, "E_ImpotQue", _rq_official_amount(boxes["E"]))
    _append_text(montants, "G_SalaireAdmisRRQ", _rq_official_amount(boxes["G"]))
    _append_text(montants, "I_SalaireAdmisRQAP", _rq_official_amount(boxes["I"]))


def _build_official_r_slip(slip: Releve1SlipPreview) -> etree._Element:
    surname, given_name = _split_employee_name(slip.employee.name)
    r_el = etree.Element("R")
    _append_text(r_el, "Annee", str(slip.taxYear))
    _append_text(r_el, "NoReleve", _releve_number(slip))

    identification = etree.SubElement(r_el, "Identification")
    employe = etree.SubElement(identification, "Employe")
    _append_text(employe, "NAS", _normalize_sin(slip.employee.sin))
    _append_text(employe, "NomFamille", surname[:30])
    _append_text(employe, "Prenom", given_name[:30])

    _append_address(r_el, slip.employee.address, fallback_line1="Adresse non fournie")
    _build_official_montants(r_el, slip.boxes)
    return r_el


def _build_official_t_summary(slips: list[Releve1SlipPreview], tax_year: int) -> etree._Element:
    employer = slips[0].employer
    t_el = etree.Element("T")
    _append_text(t_el, "Annee", str(tax_year))
    _append_text(t_el, "NbReleves", len(slips))

    employeur = etree.SubElement(t_el, "Employeur")
    _append_text(employeur, "NoId", RQ_EMPLOYER_ID)
    _append_text(employeur, "TypeDossier", "RS")
    _append_text(employeur, "NoDossier", RQ_DOSSIER_NO)
    _append_text(employeur, "NEQ", RQ_NEQ)

    nom1, nom2 = _split_name_lines(employer.name)
    _append_text(employeur, "Nom1", nom1)
    if nom2:
        _append_text(employeur, "Nom2", nom2)

    _append_address(employeur, employer.address, fallback_line1=PROVIDER_ADDRESS_LINE1)
    return t_el


def _group_slips_by_employer(slips: list[Releve1SlipPreview]) -> list[list[Releve1SlipPreview]]:
    """Group RL-1 slips so each employer gets its own Groupe01 / Releve1Return."""
    groups: dict[str, list[Releve1SlipPreview]] = {}
    order: list[str] = []
    for slip in slips:
        employer_key = slip.employer.name
        if employer_key not in groups:
            groups[employer_key] = []
            order.append(employer_key)
        groups[employer_key].append(slip)
    return [groups[key] for key in order]


def _build_official_groupe01(slips: list[Releve1SlipPreview], tax_year: int) -> etree._Element:
    groupe = etree.Element("Groupe01")
    for slip in slips:
        groupe.append(_build_official_r_slip(slip))
    groupe.append(_build_official_t_summary(slips, tax_year))
    return groupe


def build_official_rq_submission_xml(slips: list[Releve1SlipPreview], tax_year: int) -> str:
    if not slips:
        raise RqFilingNotFoundError(tax_year)

    root = etree.Element("Transmission", nsmap=RQ_OFFICIAL_NSMAP)
    root.set("VersionSchema", RQ_SCHEMA_VERSION)
    root.append(_build_official_p_block(tax_year))

    for employer_slips in _group_slips_by_employer(slips):
        root.append(_build_official_groupe01(employer_slips, tax_year))

    xml_bytes = etree.tostring(
        root,
        xml_declaration=True,
        encoding="UTF-8",
        pretty_print=True,
    )
    return xml_bytes.decode("utf-8")


def validate_official_rq_efile_xml(xml_text: str) -> None:
    schema = _get_official_schema()
    if schema is None:
        raise ValueError("Official Revenu Québec transmission schema is not available.")
    try:
        schema.validate(xml_text)
    except xmlschema.XMLSchemaValidationError as exc:
        raise ValueError(f"Invalid official Relevé 1 e-file XML: {exc.reason}") from exc


# --- Preview XML (fallback) ---------------------------------------------------


def _build_transmitter() -> etree._Element:
    transmitter = etree.Element("Transmitter")
    _append_text(transmitter, "name", PROVIDER_NAME)
    _append_text(transmitter, "contactName", PROVIDER_CONTACT_NAME)
    _append_text(transmitter, "rqEmployerId", RQ_NEQ)
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
    _append_text(summary, "rqEmployerId", RQ_NEQ)
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

    for employer_slips in _group_slips_by_employer(slips):
        releve_return = etree.SubElement(root, "Releve1Return")
        releve_return.append(_build_releve1_summary(employer_slips))
        for slip in employer_slips:
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


# --- Public API ---------------------------------------------------------------


def build_and_validate_rq_submission_xml(
    slips: list[Releve1SlipPreview],
    tax_year: int,
    *,
    official: bool | None = None,
    db: Session | None = None,
) -> str:
    use_official = official_schema_available() if official is None else official

    if use_official:
        if db is None:
            raise ValueError("Database session is required for official Relevé 1 e-file XML.")
        slips = _prepare_official_slips(db, slips)
        xml_text = build_official_rq_submission_xml(slips, tax_year)
        validate_official_rq_efile_xml(xml_text)
        return xml_text

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
    *,
    official: bool | None = None,
) -> str:
    slip = build_releve1_preview(db, employee_id, tax_year)
    _require_quebec_employment(slip)
    return build_and_validate_rq_submission_xml([slip], tax_year, official=official, db=db)


def build_rq_filing_xml(
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
        raise RqFilingNotFoundError(tax_year)

    previews: list[Releve1SlipPreview] = []
    for row in rows:
        slip = build_releve1_preview(db, row.employee_id, tax_year)
        if _employment_province(slip) == QC_PROVINCE:
            previews.append(slip)

    if not previews:
        raise RqFilingNotFoundError(tax_year)

    return build_and_validate_rq_submission_xml(previews, tax_year, official=official, db=db)
