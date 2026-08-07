"""Onboarding — explicit client employer and employee registration."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db_models import (
    ACTIVE_STATUS,
    INACTIVE_STATUS,
    EmployeeRecord,
    EmployerRecord,
    PayPeriodRecord,
)
from app.exceptions import (
    DuplicateEmployerError,
    DuplicateEmployeeError,
    EmployerNameLockedError,
    EmployerNotFoundError,
    InactiveEmployerError,
    InactiveEmployeeError,
    OnboardingEmployeeNotFoundError,
    PayrollIdentityMismatchError,
)
from app.models.onboarding import (
    EmployeeCreateRequest,
    EmployeeResponse,
    EmployeeUpdateRequest,
    EmployerCreateRequest,
    EmployerListItem,
    EmployerResponse,
    EmployerUpdateRequest,
    PartyAddressInput,
    PartyAddressResponse,
)
from app.services.provider_config import filing_employer_display_name
from app.sin import normalize_sin


def _address_response(
    line1: str | None,
    city: str | None,
    province: str | None,
    postal_code: str | None,
) -> PartyAddressResponse:
    return PartyAddressResponse(
        line1=line1,
        city=city,
        province=province,
        postalCode=postal_code,
    )


def _apply_address(
    record: EmployerRecord | EmployeeRecord,
    address: PartyAddressInput | None,
) -> None:
    if address is None:
        return
    record.address_line1 = address.line1
    record.city = address.city
    record.province = address.province
    record.postal_code = address.postal_code


def _employer_has_payroll(db: Session, employer_id: int) -> bool:
    return (
        db.query(PayPeriodRecord.id)
        .join(EmployeeRecord, PayPeriodRecord.employee_id == EmployeeRecord.id)
        .filter(EmployeeRecord.employer_id == employer_id)
        .first()
        is not None
    )


def _employee_count(db: Session, employer_id: int) -> int:
    return (
        db.query(func.count(EmployeeRecord.id))
        .filter(EmployeeRecord.employer_id == employer_id)
        .scalar()
        or 0
    )


def _get_employer(db: Session, employer_id: int) -> EmployerRecord:
    employer = db.query(EmployerRecord).filter_by(id=employer_id).one_or_none()
    if employer is None:
        raise EmployerNotFoundError(employer_id)
    return employer


def _get_employee_for_employer(db: Session, employer_id: int, employee_id: int) -> EmployeeRecord:
    employee = (
        db.query(EmployeeRecord)
        .filter_by(id=employee_id, employer_id=employer_id)
        .one_or_none()
    )
    if employee is None:
        raise OnboardingEmployeeNotFoundError(employer_id, employee_id)
    return employee


def _employer_response(db: Session, employer: EmployerRecord, *, include_lock: bool = True) -> EmployerResponse:
    name_locked = _employer_has_payroll(db, employer.id) if include_lock else False
    return EmployerResponse(
        id=employer.id,
        name=employer.name,
        filingDisplayName=filing_employer_display_name(employer.name),
        address=_address_response(
            employer.address_line1,
            employer.city,
            employer.province,
            employer.postal_code,
        ),
        status=employer.status,  # type: ignore[arg-type]
        createdAt=employer.created_at,
        employeeCount=_employee_count(db, employer.id),
        nameLocked=name_locked,
    )


def _employee_response(employee: EmployeeRecord, employer: EmployerRecord) -> EmployeeResponse:
    return EmployeeResponse(
        id=employee.id,
        employerId=employer.id,
        employerName=employer.name,
        name=employee.name,
        sin=employee.sin,
        address=_address_response(
            employee.address_line1,
            employee.city,
            employee.province,
            employee.postal_code,
        ),
        employmentProvince=employee.employment_province,
        status=employee.status,  # type: ignore[arg-type]
        createdAt=employee.created_at,
    )


def _resolve_employment_province(
    payload: EmployeeCreateRequest | EmployeeUpdateRequest,
    existing: EmployeeRecord | None = None,
) -> str | None:
    if payload.employment_province is not None:
        return payload.employment_province
    if payload.address is not None and payload.address.province is not None:
        return payload.address.province
    if existing is not None:
        return existing.employment_province
    return None


def create_employer(db: Session, payload: EmployerCreateRequest) -> EmployerResponse:
    existing = db.query(EmployerRecord).filter_by(name=payload.name).one_or_none()
    if existing is not None:
        raise DuplicateEmployerError(payload.name)

    employer = EmployerRecord(name=payload.name, status=ACTIVE_STATUS)
    _apply_address(employer, payload.address)
    db.add(employer)
    db.commit()
    db.refresh(employer)
    return _employer_response(db, employer)


def list_employers(
    db: Session,
    *,
    name: str | None = None,
    status: str | None = ACTIVE_STATUS,
) -> list[EmployerListItem]:
    query = db.query(EmployerRecord).order_by(EmployerRecord.name)
    if name:
        query = query.filter(EmployerRecord.name.ilike(f"%{name.strip()}%"))
    if status:
        query = query.filter(EmployerRecord.status == status)

    employers = query.all()
    return [
        EmployerListItem(
            id=employer.id,
            name=employer.name,
            filingDisplayName=filing_employer_display_name(employer.name),
            status=employer.status,  # type: ignore[arg-type]
            employeeCount=_employee_count(db, employer.id),
        )
        for employer in employers
    ]


def get_employer(db: Session, employer_id: int) -> EmployerResponse:
    employer = _get_employer(db, employer_id)
    return _employer_response(db, employer)


def update_employer(db: Session, employer_id: int, payload: EmployerUpdateRequest) -> EmployerResponse:
    employer = _get_employer(db, employer_id)

    if payload.name is not None and payload.name != employer.name:
        if _employer_has_payroll(db, employer_id):
            raise EmployerNameLockedError(employer_id)
        conflict = db.query(EmployerRecord).filter_by(name=payload.name).one_or_none()
        if conflict is not None and conflict.id != employer_id:
            raise DuplicateEmployerError(payload.name)
        employer.name = payload.name

    if payload.address is not None:
        _apply_address(employer, payload.address)

    if payload.status is not None:
        employer.status = payload.status

    db.commit()
    db.refresh(employer)
    return _employer_response(db, employer)


def create_employee(
    db: Session,
    employer_id: int,
    payload: EmployeeCreateRequest,
) -> EmployeeResponse:
    employer = _get_employer(db, employer_id)
    if employer.status == INACTIVE_STATUS:
        raise InactiveEmployerError(employer_id)

    existing = (
        db.query(EmployeeRecord)
        .filter_by(employer_id=employer_id, sin=payload.sin)
        .one_or_none()
    )
    if existing is not None:
        raise DuplicateEmployeeError(payload.sin, employer_id)

    employee = EmployeeRecord(
        employer_id=employer_id,
        name=payload.name,
        sin=payload.sin,
        status=ACTIVE_STATUS,
        employment_province=_resolve_employment_province(payload),
    )
    _apply_address(employee, payload.address)
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return _employee_response(employee, employer)


def list_employees_for_employer(db: Session, employer_id: int) -> list[EmployeeResponse]:
    employer = _get_employer(db, employer_id)
    employees = (
        db.query(EmployeeRecord)
        .filter_by(employer_id=employer_id)
        .order_by(EmployeeRecord.name)
        .all()
    )
    return [_employee_response(employee, employer) for employee in employees]


def get_employee(db: Session, employer_id: int, employee_id: int) -> EmployeeResponse:
    employer = _get_employer(db, employer_id)
    employee = _get_employee_for_employer(db, employer_id, employee_id)
    return _employee_response(employee, employer)


def update_employee(
    db: Session,
    employer_id: int,
    employee_id: int,
    payload: EmployeeUpdateRequest,
) -> EmployeeResponse:
    employer = _get_employer(db, employer_id)
    employee = _get_employee_for_employer(db, employer_id, employee_id)

    if payload.name is not None:
        employee.name = payload.name

    if payload.address is not None:
        _apply_address(employee, payload.address)

    if payload.employment_province is not None or payload.address is not None:
        employee.employment_province = _resolve_employment_province(payload, employee)

    if payload.status is not None:
        employee.status = payload.status

    db.commit()
    db.refresh(employee)
    return _employee_response(employee, employer)


def ensure_employer_active(db: Session, employer_id: int) -> EmployerRecord:
    employer = _get_employer(db, employer_id)
    if employer.status == INACTIVE_STATUS:
        raise InactiveEmployerError(employer_id)
    return employer


def ensure_employee_active(db: Session, employee_id: int) -> EmployeeRecord:
    employee = db.query(EmployeeRecord).filter_by(id=employee_id).one_or_none()
    if employee is None:
        raise OnboardingEmployeeNotFoundError(-1, employee_id)
    if employee.status == INACTIVE_STATUS:
        raise InactiveEmployeeError(employee_id)
    return employee


def resolve_employer_for_payroll(
    db: Session,
    *,
    employer_id: int | None,
    name: str | None,
) -> EmployerRecord:
    if employer_id is not None:
        employer = db.query(EmployerRecord).filter_by(id=employer_id).one_or_none()
        if employer is None:
            raise EmployerNotFoundError(employer_id)
        if employer.status == INACTIVE_STATUS:
            raise InactiveEmployerError(employer_id)
        if name is not None and name.strip() != employer.name:
            raise PayrollIdentityMismatchError(
                f"Employer name {name.strip()!r} does not match registered employer "
                f"{employer.name!r} (id={employer_id})."
            )
        return employer

    if name is None or not name.strip():
        raise PayrollIdentityMismatchError("employer.name is required when employer.id is omitted.")

    trimmed_name = name.strip()
    employer = db.query(EmployerRecord).filter_by(name=trimmed_name).one_or_none()
    if employer is None:
        employer = EmployerRecord(name=trimmed_name, status=ACTIVE_STATUS)
        db.add(employer)
        db.flush()
        return employer

    if employer.status == INACTIVE_STATUS:
        raise InactiveEmployerError(employer.id)
    return employer


def resolve_employee_for_payroll(
    db: Session,
    employer: EmployerRecord,
    *,
    employee_id: int | None,
    name: str,
    sin: str,
) -> EmployeeRecord:
    normalized_sin = normalize_sin(sin)

    if employee_id is not None:
        employee = db.query(EmployeeRecord).filter_by(id=employee_id).one_or_none()
        if employee is None:
            raise OnboardingEmployeeNotFoundError(employer.id, employee_id)
        if employee.employer_id != employer.id:
            raise PayrollIdentityMismatchError(
                f"Employee {employee_id} does not belong to employer {employer.id}."
            )
        if employee.status == INACTIVE_STATUS:
            raise InactiveEmployeeError(employee_id)
        if employee.sin != normalized_sin:
            raise PayrollIdentityMismatchError(
                f"Employee SIN does not match registered employee {employee_id}."
            )
        employee.name = name.strip()
        return employee

    employee = (
        db.query(EmployeeRecord)
        .filter_by(employer_id=employer.id, sin=normalized_sin)
        .one_or_none()
    )
    if employee is None:
        employee = EmployeeRecord(
            employer_id=employer.id,
            name=name.strip(),
            sin=normalized_sin,
            status=ACTIVE_STATUS,
        )
        db.add(employee)
        db.flush()
        return employee

    if employee.status == INACTIVE_STATUS:
        raise InactiveEmployeeError(employee.id)
    employee.name = name.strip()
    return employee
