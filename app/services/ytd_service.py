from sqlalchemy.orm import Session

from app.db_models import EmployeeRecord, PayPeriodRecord, YtdRecord
from app.exceptions import DuplicatePayPeriodError
from app.models.cumulative import CumulativeResponse, CumulativeTotals, LastPayPeriod
from app.models.payroll import PayrollPayload
from app.services.onboarding_service import resolve_employee_for_payroll, resolve_employer_for_payroll

def _find_existing_pay_period(
    db: Session,
    employee: EmployeeRecord,
    payload: PayrollPayload,
) -> PayPeriodRecord | None:
    return (
        db.query(PayPeriodRecord)
        .filter_by(
            employee_id=employee.id,
            period_start=payload.pay_period.start_date,
            period_end=payload.pay_period.end_date,
        )
        .one_or_none()
    )


def _get_or_create_ytd(db: Session, employee: EmployeeRecord, tax_year: int) -> YtdRecord:
    from decimal import Decimal

    ytd = (
        db.query(YtdRecord)
        .filter_by(employee_id=employee.id, tax_year=tax_year)
        .one_or_none()
    )
    if ytd is None:
        ytd = YtdRecord(
            employee_id=employee.id,
            tax_year=tax_year,
            gross_pay=Decimal("0.00"),
            cpp=Decimal("0.00"),
            ei=Decimal("0.00"),
            qpip=Decimal("0.00"),
            income_tax=Decimal("0.00"),
            net_pay=Decimal("0.00"),
        )
        db.add(ytd)
        db.flush()
    return ytd


def accumulate_ytd(db: Session, payload: PayrollPayload) -> CumulativeResponse:
    """
    Record this pay period, add amounts to YTD totals, and return cumulative state.

    Raises DuplicatePayPeriodError if this employee/period was already submitted.
    """
    tax_year = payload.pay_period.pay_date.year

    employer = resolve_employer_for_payroll(
        db,
        employer_id=payload.employer.id,
        name=payload.employer.name,
    )
    employee = resolve_employee_for_payroll(
        db,
        employer,
        employee_id=payload.employee.id,
        name=payload.employee.name,
        sin=payload.employee.sin,
    )

    if _find_existing_pay_period(db, employee, payload) is not None:
        raise DuplicatePayPeriodError(
            employee_sin=employee.sin,
            period_start=payload.pay_period.start_date,
            period_end=payload.pay_period.end_date,
        )

    db.add(
        PayPeriodRecord(
            employee_id=employee.id,
            tax_year=tax_year,
            period_start=payload.pay_period.start_date,
            period_end=payload.pay_period.end_date,
            pay_date=payload.pay_period.pay_date,
            gross_pay=payload.earnings.gross_pay,
            cpp=payload.deductions.cpp,
            ei=payload.deductions.ei,
            qpip=payload.deductions.qpip,
            income_tax=payload.deductions.income_tax,
            net_pay=payload.net_pay,
        )
    )

    ytd = _get_or_create_ytd(db, employee, tax_year)

    ytd.gross_pay += payload.earnings.gross_pay
    ytd.cpp += payload.deductions.cpp
    ytd.ei += payload.deductions.ei
    ytd.qpip += payload.deductions.qpip
    ytd.income_tax += payload.deductions.income_tax
    ytd.net_pay += payload.net_pay
    ytd.last_period_start = payload.pay_period.start_date
    ytd.last_period_end = payload.pay_period.end_date
    ytd.last_pay_date = payload.pay_period.pay_date

    db.commit()
    db.refresh(ytd)

    return CumulativeResponse(
        taxYear=tax_year,
        employeeId=employee.id,
        employerName=employer.name,
        employeeName=employee.name,
        employeeSin=employee.sin,
        employmentProvince=employee.employment_province,
        totals=CumulativeTotals(
            grossPay=ytd.gross_pay,
            cpp=ytd.cpp,
            ei=ytd.ei,
            qpip=ytd.qpip,
            incomeTax=ytd.income_tax,
            netPay=ytd.net_pay,
        ),
        lastPayPeriod=LastPayPeriod(
            startDate=ytd.last_period_start,
            endDate=ytd.last_period_end,
            payDate=ytd.last_pay_date,
        ),
    )
