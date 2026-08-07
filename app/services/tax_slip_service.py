from sqlalchemy.orm import Session, joinedload

from app.db_models import EmployeeRecord, YtdRecord
from app.models.tax_slip import (
    Releve1SlipPreview,
    T4EmployeeSummary,
    T4SlipPreview,
    TaxPartyAddress,
)
from app.services.provider_config import build_filing_employer_summary
from app.services.stub_archive_service import EmployeeNotFoundError
from app.tax.box_mapping import (
    RELEVE1_BOX_LABELS,
    RELEVE1_PREP_DISCLAIMERS,
    T4_BOX_LABELS,
    T4_PREP_DISCLAIMERS,
    map_ytd_to_releve1_boxes,
    map_ytd_to_t4_boxes,
)


class YtdNotFoundError(Exception):
    def __init__(self, employee_id: int, tax_year: int) -> None:
        self.employee_id = employee_id
        self.tax_year = tax_year
        super().__init__(f"No YTD totals for employee {employee_id} in tax year {tax_year}.")


def _party_address(
    line1: str | None,
    city: str | None,
    province: str | None,
    postal_code: str | None,
) -> TaxPartyAddress:
    return TaxPartyAddress(
        line1=line1,
        city=city,
        province=province,
        postalCode=postal_code,
    )


def _load_employee_ytd(db: Session, employee_id: int, tax_year: int) -> tuple[EmployeeRecord, YtdRecord]:
    employee = (
        db.query(EmployeeRecord)
        .options(joinedload(EmployeeRecord.employer))
        .filter_by(id=employee_id)
        .one_or_none()
    )
    if employee is None:
        raise EmployeeNotFoundError(employee_id)

    ytd = (
        db.query(YtdRecord)
        .filter_by(employee_id=employee_id, tax_year=tax_year)
        .one_or_none()
    )
    if ytd is None:
        raise YtdNotFoundError(employee_id, tax_year)

    return employee, ytd


def build_t4_preview(db: Session, employee_id: int, tax_year: int) -> T4SlipPreview:
    employee, ytd = _load_employee_ytd(db, employee_id, tax_year)
    employer = employee.employer

    return T4SlipPreview(
        taxYear=tax_year,
        employee=T4EmployeeSummary(
            id=employee.id,
            name=employee.name,
            sin=employee.sin,
            employmentProvince=employee.employment_province,
            address=_party_address(
                employee.address_line1,
                employee.city,
                employee.province,
                employee.postal_code,
            ),
        ),
        employer=build_filing_employer_summary(employer.name),
        boxes=map_ytd_to_t4_boxes(ytd),
        boxLabels=T4_BOX_LABELS,
        disclaimers=list(T4_PREP_DISCLAIMERS),
    )


def build_releve1_preview(db: Session, employee_id: int, tax_year: int) -> Releve1SlipPreview:
    employee, ytd = _load_employee_ytd(db, employee_id, tax_year)
    employer = employee.employer

    return Releve1SlipPreview(
        taxYear=tax_year,
        employee=T4EmployeeSummary(
            id=employee.id,
            name=employee.name,
            sin=employee.sin,
            employmentProvince=employee.employment_province,
            address=_party_address(
                employee.address_line1,
                employee.city,
                employee.province,
                employee.postal_code,
            ),
        ),
        employer=build_filing_employer_summary(employer.name),
        boxes=map_ytd_to_releve1_boxes(ytd),
        boxLabels=RELEVE1_BOX_LABELS,
        disclaimers=list(RELEVE1_PREP_DISCLAIMERS),
    )
