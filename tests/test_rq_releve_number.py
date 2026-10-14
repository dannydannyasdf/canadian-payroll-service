"""Tests for Revenu Québec RL-slip number allocation (IN-800-V)."""

from datetime import date
from decimal import Decimal

from app.db_models import EmployeeRecord, YtdRecord
from app.rq_releve_number import format_releve_number, mod7_check_digit
from app.services.rq_releve_sequence_service import ensure_rq_releve_no
from tests.conftest import seed_employee_with_ytd


def test_mod7_check_digit_example_from_in_800() -> None:
    assert mod7_check_digit(71_997_012) == 3
    assert format_releve_number(71_997_012) == "719970123"


def test_mod7_check_digit_exact_quotient() -> None:
    assert mod7_check_digit(14) == 0
    assert format_releve_number(14) == "000000140"


def test_ensure_rq_releve_no_persists_per_employee_year(db_session) -> None:
    employee = seed_employee_with_ytd(db_session, employment_province="QC")

    first = ensure_rq_releve_no(db_session, employee.id, 2026)
    second = ensure_rq_releve_no(db_session, employee.id, 2026)

    assert first == second
    assert len(first) == 9
    assert first.isdigit()


def test_ensure_rq_releve_no_allocates_sequential_numbers(db_session) -> None:
    first_employee = seed_employee_with_ytd(db_session, employment_province="QC")

    second_employee = EmployeeRecord(
        employer_id=first_employee.employer_id,
        name="Second QC Worker",
        sin="483-630-647",
        status="active",
        employment_province="QC",
    )
    db_session.add(second_employee)
    db_session.flush()
    db_session.add(
        YtdRecord(
            employee_id=second_employee.id,
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
    db_session.refresh(second_employee)

    first_no = ensure_rq_releve_no(db_session, first_employee.id, 2026)
    second_no = ensure_rq_releve_no(db_session, second_employee.id, 2026)

    assert first_no != second_no
    assert int(second_no[:8]) == int(first_no[:8]) + 1
