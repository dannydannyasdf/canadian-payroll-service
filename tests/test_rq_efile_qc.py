from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.db_models import EmployeeRecord, EmployerRecord, YtdRecord
from app.demo_defaults import DEMO_EMPLOYMENT_PROVINCE, DEMO_SAMPLE_SIN
from app.services.onboarding_service import resolve_employee_for_payroll
from app.services.rq_efile_service import (
    RqFilingNotApplicableError,
    RqFilingNotFoundError,
    build_employee_releve1_efile_xml,
    build_rq_filing_xml,
)
from app.services.provider_config import build_filing_employer_summary
from tests.conftest import make_releve1_slip, seed_employee_with_ytd

ON_SAMPLE_SIN = "483-630-647"


def test_resolve_employee_for_payroll_sets_demo_qc(db_session: Session) -> None:
    employer = EmployerRecord(name="Acme Productions Ltd.", status="active")
    db_session.add(employer)
    db_session.flush()

    employee = resolve_employee_for_payroll(
        db_session,
        employer,
        employee_id=None,
        name="Jane Freelancer",
        sin=DEMO_SAMPLE_SIN,
    )

    assert employee.employment_province == DEMO_EMPLOYMENT_PROVINCE


def test_build_employee_releve1_efile_xml_rejects_non_qc(db_session: Session) -> None:
    employee = seed_employee_with_ytd(db_session, employment_province="ON")

    with pytest.raises(RqFilingNotApplicableError) as exc_info:
        build_employee_releve1_efile_xml(db_session, employee.id, 2026, official=False)

    assert exc_info.value.province == "ON"


def test_build_employee_releve1_efile_xml_accepts_qc(db_session: Session) -> None:
    employee = seed_employee_with_ytd(db_session, employment_province="QC")

    xml_text = build_employee_releve1_efile_xml(db_session, employee.id, 2026, official=False)

    assert "Releve1Slip" in xml_text


def test_build_rq_filing_xml_filters_to_qc_only(db_session: Session) -> None:
    qc_employee = seed_employee_with_ytd(db_session, employment_province="QC")
    employer = qc_employee.employer

    on_employee = EmployeeRecord(
        employer_id=employer.id,
        name="Ontario Worker",
        sin=ON_SAMPLE_SIN,
        status="active",
        employment_province="ON",
    )
    db_session.add(on_employee)
    db_session.flush()
    db_session.add(
        YtdRecord(
            employee_id=on_employee.id,
            tax_year=2026,
            gross_pay=Decimal("5000.00"),
            cpp=Decimal("288.00"),
            ei=Decimal("82.00"),
            income_tax=Decimal("1905.68"),
            federal_income_tax=Decimal("895.98"),
            provincial_income_tax=Decimal("1009.70"),
            net_pay=Decimal("2702.82"),
            last_period_start=date(2026, 1, 8),
            last_period_end=date(2026, 1, 14),
            last_pay_date=date(2026, 1, 17),
        )
    )
    db_session.commit()

    xml_text = build_rq_filing_xml(db_session, 2026, official=False)

    assert "Releve1Slip" in xml_text
    assert "Ontario Worker" not in xml_text


def test_build_rq_filing_xml_raises_when_no_qc_employees(db_session: Session) -> None:
    seed_employee_with_ytd(db_session, employment_province="ON")

    with pytest.raises(RqFilingNotFoundError):
        build_rq_filing_xml(db_session, 2026, official=False)


def test_build_rq_filing_xml_groups_slips_by_employer(db_session: Session) -> None:
    qc_employee = seed_employee_with_ytd(db_session, employment_province="QC")

    other_employer = EmployerRecord(name="Other Client Ltd.", status="active")
    db_session.add(other_employer)
    db_session.flush()

    other_employee = EmployeeRecord(
        employer_id=other_employer.id,
        name="Other QC Worker",
        sin="123-456-789",
        status="active",
        employment_province="QC",
    )
    db_session.add(other_employee)
    db_session.flush()
    db_session.add(
        YtdRecord(
            employee_id=other_employee.id,
            tax_year=2026,
            gross_pay=Decimal("8000.00"),
            cpp=Decimal("460.80"),
            ei=Decimal("131.20"),
            income_tax=Decimal("1500.00"),
            federal_income_tax=Decimal("700.00"),
            provincial_income_tax=Decimal("800.00"),
            net_pay=Decimal("5908.00"),
            last_period_start=date(2026, 1, 8),
            last_period_end=date(2026, 1, 14),
            last_pay_date=date(2026, 1, 17),
        )
    )
    db_session.commit()

    xml_text = build_rq_filing_xml(db_session, 2026, official=False)

    assert xml_text.count("<Releve1Return>") == 2
    assert "Freelancer" in xml_text
    assert "Worker" in xml_text
    assert qc_employee.employer.name in xml_text
    assert other_employer.name in xml_text


def test_build_official_rq_submission_xml_groups_by_employer() -> None:
    from app.services.rq_efile_service import build_official_rq_submission_xml

    slip_one = make_releve1_slip(employee_id=1)
    slip_two = make_releve1_slip(employee_id=2)
    slip_two = slip_two.model_copy(
        update={"employer": build_filing_employer_summary("Other Client Ltd.")}
    )

    xml_text = build_official_rq_submission_xml([slip_one, slip_two], 2026)

    assert xml_text.count("<Groupe01>") == 2
    assert xml_text.count("<T>") == 2
    assert xml_text.count("<NbReleves>1</NbReleves>") == 2
