"""Tests for CRA T4127 CPP, EI, and QPIP (Chapters 6–7)."""

from decimal import Decimal

from app.tax.t4127.cpp_ei import CppEiInput, calculate_cpp, calculate_cpp_ei, calculate_ei, calculate_qpip


def test_weekly_ontario_cpp() -> None:
    cpp, cpp2 = calculate_cpp(
        CppEiInput(gross_pay=Decimal("1000"), pay_periods_per_year=52, province="ON")
    )
    assert cpp == Decimal("55.50")
    assert cpp2 == Decimal("0.00")


def test_weekly_ontario_ei() -> None:
    ei = calculate_ei(CppEiInput(gross_pay=Decimal("1000"), pay_periods_per_year=52, province="ON"))
    assert ei == Decimal("16.30")


def test_semimonthly_ontario_cpp_from_t4127_scenario() -> None:
    cpp, _cpp2 = calculate_cpp(
        CppEiInput(gross_pay=Decimal("4200"), pay_periods_per_year=24, province="ON")
    )
    assert cpp == Decimal("241.22")


def test_semimonthly_ontario_ei() -> None:
    ei = calculate_ei(CppEiInput(gross_pay=Decimal("4200"), pay_periods_per_year=24, province="ON"))
    assert ei == Decimal("68.46")


def test_quebec_qpip() -> None:
    qpip = calculate_qpip(
        CppEiInput(gross_pay=Decimal("5000"), pay_periods_per_year=52, province="QC")
    )
    assert qpip == Decimal("21.50")


def test_quebec_ei_lower_rate() -> None:
    ei = calculate_ei(CppEiInput(gross_pay=Decimal("1000"), pay_periods_per_year=52, province="QC"))
    assert ei == Decimal("13.00")


def test_calculate_cpp_ei_combined() -> None:
    result = calculate_cpp_ei(
        CppEiInput(gross_pay=Decimal("1000"), pay_periods_per_year=52, province="ON")
    )
    assert result.cpp == Decimal("55.50")
    assert result.ei == Decimal("16.30")
    assert result.qpip == Decimal("0.00")
