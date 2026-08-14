from __future__ import annotations

from collections.abc import Generator
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app import db_models  # noqa: F401
from app.database import Base
from app.db_models import EmployeeRecord, EmployerRecord, YtdRecord
from app.demo_defaults import DEMO_EMPLOYMENT_PROVINCE, DEMO_SAMPLE_SIN
from app.models.tax_slip import Releve1SlipPreview, T4EmployeeSummary, T4EmployerSummary, T4SlipPreview, TaxPartyAddress


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def make_employer_summary() -> T4EmployerSummary:
    return T4EmployerSummary(
        name="Acme Productions Ltd.@Gamma Personnel Inc.",
        businessNumber="106688385",
        payrollAccountNumber="10668 8385 RP0001",
        address=TaxPartyAddress(
            line1="B301-2001 University, C.P. 71316",
            city="Montréal",
            province="QC",
            postalCode="H3A 3S9",
        ),
    )


def make_employee_summary(
    *,
    employee_id: int = 1,
    employment_province: str | None = "QC",
) -> T4EmployeeSummary:
    return T4EmployeeSummary(
        id=employee_id,
        name="Jane Freelancer",
        sin=DEMO_SAMPLE_SIN,
        employmentProvince=employment_province,
        address=TaxPartyAddress(
            line1="1 Rue Example",
            city="Montréal",
            province="QC",
            postalCode="H1H1H1",
        ),
    )


def make_releve1_slip(
    *,
    employee_id: int = 1,
    employment_province: str | None = "QC",
) -> Releve1SlipPreview:
    return Releve1SlipPreview(
        taxYear=2026,
        employee=make_employee_summary(
            employee_id=employee_id,
            employment_province=employment_province,
        ),
        employer=make_employer_summary(),
        boxes={
            "A": "10000.00",
            "B": "576.00",
            "C": "164.00",
            "E": "2200.00",
            "G": "10000.00",
            "I": "10000.00",
        },
        boxLabels={},
        disclaimers=[],
        status="preview",
    )


def make_t4_slip(
    *,
    employee_id: int = 1,
    employment_province: str | None = "ON",
) -> T4SlipPreview:
    return T4SlipPreview(
        taxYear=2026,
        employee=make_employee_summary(
            employee_id=employee_id,
            employment_province=employment_province,
        ),
        employer=make_employer_summary(),
        boxes={
            "10": employment_province or "ON",
            "12": DEMO_SAMPLE_SIN.replace("-", ""),
            "14": "10000.00",
            "16": "576.00",
            "18": "164.00",
            "22": "2200.00",
            "24": "10000.00",
            "26": "10000.00",
        },
        boxLabels={},
        disclaimers=[],
        status="preview",
    )


def seed_employee_with_ytd(
    db: Session,
    *,
    employment_province: str | None,
    tax_year: int = 2026,
) -> EmployeeRecord:
    employer = EmployerRecord(name="Acme Productions Ltd.", status="active")
    db.add(employer)
    db.flush()

    employee = EmployeeRecord(
        employer_id=employer.id,
        name="Jane Freelancer",
        sin=DEMO_SAMPLE_SIN,
        status="active",
        employment_province=employment_province,
    )
    db.add(employee)
    db.flush()

    db.add(
        YtdRecord(
            employee_id=employee.id,
            tax_year=tax_year,
            gross_pay=Decimal("10000.00"),
            cpp=Decimal("576.00"),
            ei=Decimal("164.00"),
            income_tax=Decimal("2200.00"),
            net_pay=Decimal("7060.00"),
            last_period_start=date(2026, 1, 1),
            last_period_end=date(2026, 1, 7),
            last_pay_date=date(2026, 1, 10),
        )
    )
    db.commit()
    db.refresh(employee)
    return employee
