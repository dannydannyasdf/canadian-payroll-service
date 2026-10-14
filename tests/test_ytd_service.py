from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.db_models import EmployeeRecord, PayPeriodRecord, PayPeriodRecord
from app.demo_defaults import DEMO_EMPLOYMENT_PROVINCE, DEMO_SAMPLE_SIN
from app.exceptions import DuplicatePayPeriodError
from app.models.payroll import Deductions, Earnings, Employee, Employer, PayPeriod, PayrollPayload
from app.services.ytd_service import accumulate_ytd


def _sample_payload() -> PayrollPayload:
    return PayrollPayload(
        employer=Employer(name="Acme Productions Ltd."),
        employee=Employee(name="Jane Freelancer", sin=DEMO_SAMPLE_SIN),
        payPeriod=PayPeriod(
            startDate=date(2026, 1, 1),
            endDate=date(2026, 1, 7),
            payDate=date(2026, 1, 10),
        ),
        earnings=Earnings(grossPay=Decimal("5000.00")),
        deductions=Deductions(
            cpp=Decimal("288.00"),
            ei=Decimal("82.00"),
            federalIncomeTax=Decimal("895.98"),
            provincialIncomeTax=Decimal("1009.70"),
            incomeTax=Decimal("1905.68"),
            qpip=Decimal("21.50"),
        ),
        netPay=Decimal("2702.82"),
    )


def test_accumulate_ytd_rejects_duplicate_pay_period(db_session: Session) -> None:
    payload = _sample_payload()

    accumulate_ytd(db_session, payload)

    with pytest.raises(DuplicatePayPeriodError):
        accumulate_ytd(db_session, payload)


def test_accumulate_ytd_persists_comments(db_session: Session) -> None:
    payload = _sample_payload()
    payload = payload.model_copy(
        update={"comments": "Shown on stub.", "comments2": "Private employer note."}
    )

    accumulate_ytd(db_session, payload)

    period = db_session.query(PayPeriodRecord).one()
    assert period.comments == "Shown on stub."
    assert period.comments2 == "Private employer note."


def test_accumulate_ytd_sets_demo_employment_province(db_session: Session) -> None:
    response = accumulate_ytd(db_session, _sample_payload())

    employee = db_session.query(EmployeeRecord).filter_by(id=response.employee_id).one()
    assert employee.employment_province == DEMO_EMPLOYMENT_PROVINCE
    assert response.employment_province == DEMO_EMPLOYMENT_PROVINCE
    assert response.totals.qpip == Decimal("21.50")
    assert (
        db_session.query(PayPeriodRecord)
        .filter_by(employee_id=employee.id)
        .count()
        == 1
    )
