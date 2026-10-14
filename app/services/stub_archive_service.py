from decimal import Decimal

from sqlalchemy.orm import Session, joinedload

from app.db_models import EmployeeRecord, PayPeriodRecord


class EmployeeNotFoundError(Exception):
    def __init__(self, employee_id: int) -> None:
        self.employee_id = employee_id
        super().__init__(f"Employee {employee_id} not found.")


class StubArchiveNotFoundError(Exception):
    def __init__(self, employee_id: int, tax_year: int) -> None:
        self.employee_id = employee_id
        self.tax_year = tax_year
        super().__init__(f"No pay stubs found for employee {employee_id} in tax year {tax_year}.")


def list_employees(db: Session, employer_id: int | None = None) -> list[dict]:
    query = db.query(EmployeeRecord).options(joinedload(EmployeeRecord.employer)).order_by(EmployeeRecord.name)
    if employer_id is not None:
        query = query.filter(EmployeeRecord.employer_id == employer_id)
    employees = query.all()
    return [
        {
            "id": employee.id,
            "name": employee.name,
            "sin": employee.sin,
            "employerId": employee.employer_id,
            "employerName": employee.employer.name,
        }
        for employee in employees
    ]


def build_stub_archive(db: Session, employee_id: int, tax_year: int) -> list[dict]:
    employee = (
        db.query(EmployeeRecord)
        .options(joinedload(EmployeeRecord.employer))
        .filter_by(id=employee_id)
        .one_or_none()
    )
    if employee is None:
        raise EmployeeNotFoundError(employee_id)

    periods = (
        db.query(PayPeriodRecord)
        .filter_by(employee_id=employee_id, tax_year=tax_year)
        .order_by(PayPeriodRecord.period_start, PayPeriodRecord.pay_date)
        .all()
    )
    if not periods:
        raise StubArchiveNotFoundError(employee_id, tax_year)

    running = {
        "gross_pay": Decimal("0.00"),
        "cpp": Decimal("0.00"),
        "ei": Decimal("0.00"),
        "qpip": Decimal("0.00"),
        "federal_income_tax": Decimal("0.00"),
        "provincial_income_tax": Decimal("0.00"),
        "income_tax": Decimal("0.00"),
        "net_pay": Decimal("0.00"),
    }

    stubs: list[dict] = []
    for period in periods:
        running["gross_pay"] += period.gross_pay
        running["cpp"] += period.cpp
        running["ei"] += period.ei
        running["qpip"] += period.qpip
        running["federal_income_tax"] += period.federal_income_tax
        running["provincial_income_tax"] += period.provincial_income_tax
        running["income_tax"] += period.income_tax
        running["net_pay"] += period.net_pay

        stubs.append(
            {
                "employer_name": employee.employer.name,
                "employee_name": employee.name,
                "employee_sin": employee.sin,
                "period_start": period.period_start.isoformat(),
                "period_end": period.period_end.isoformat(),
                "pay_date": period.pay_date.isoformat(),
                "tax_year": tax_year,
                "gross_pay": period.gross_pay,
                "cpp": period.cpp,
                "ei": period.ei,
                "qpip": period.qpip,
                "federal_income_tax": period.federal_income_tax,
                "provincial_income_tax": period.provincial_income_tax,
                "income_tax": period.federal_income_tax,
                "net_pay": period.net_pay,
                "comments": period.comments,
                "employment_province": employee.employment_province,
                "ytd_gross_pay": running["gross_pay"],
                "ytd_cpp": running["cpp"],
                "ytd_ei": running["ei"],
                "ytd_qpip": running["qpip"],
                "ytd_federal_income_tax": running["federal_income_tax"],
                "ytd_provincial_income_tax": running["provincial_income_tax"],
                "ytd_income_tax": running["federal_income_tax"],
                "ytd_net_pay": running["net_pay"],
            }
        )

    return stubs
