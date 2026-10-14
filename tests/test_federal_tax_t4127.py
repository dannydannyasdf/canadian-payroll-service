"""Tests for CRA T4127 Option 1 federal income tax."""

from decimal import ROUND_HALF_UP, Decimal

import pytest

from app.tax.t4127.federal import FederalTaxInput, _annual_taxable_income, calculate_federal_income_tax
from app.tax.t4127.rates_jul_2026 import FEDERAL_BRACKETS


def test_bracket_lookup_first_federal_bracket() -> None:
    rate, constant = FEDERAL_BRACKETS.lookup(Decimal("50000"))
    assert rate == Decimal("0.14")
    assert constant == Decimal("0")


def test_bracket_lookup_second_federal_bracket() -> None:
    rate, constant = FEDERAL_BRACKETS.lookup(Decimal("60000"))
    assert rate == Decimal("0.205")
    assert constant == Decimal("3804")


def test_cra_bonus_example_step2_t3_formula() -> None:
    """T4127 regular bonus example — Step 2 published factors (T1 = $4,434.52)."""
    annual_taxable = Decimal("52975.28")
    t3 = (
        (Decimal("0.14") * annual_taxable)
        - Decimal("2303.28")
        - Decimal("468.60")
        - Decimal("210.14")
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    assert t3 == Decimal("4434.52")


def test_cra_bonus_example_step2_annual_taxable_income() -> None:
    """Annual taxable income A from T4127 bonus example Step 2."""
    assert _annual_taxable_income(
        FederalTaxInput(
            gross_pay=Decimal("1000"),
            cpp=Decimal("58.37"),
            ei=Decimal("16.30"),
            pay_periods_per_year=52,
            province="ON",
            ytd_bonus_taxable=Decimal("1485.40"),
        )
    ) == Decimal("52975.28")


def test_simple_weekly_salary_federal_tax() -> None:
    """First-period weekly employee — $1,000 gross, Ontario, claim code 1."""
    result = calculate_federal_income_tax(
        FederalTaxInput(
            gross_pay=Decimal("1000"),
            cpp=Decimal("204.25"),
            ei=Decimal("16.30"),
            pay_periods_per_year=52,
            province="ON",
            federal_claim_code=1,
        )
    )
    assert result.annual_taxable_income == Decimal("50214.84")
    assert result.annual_basic_federal_tax == Decimal("3905.27")
    assert result.federal_income_tax == Decimal("75.10")


def test_quebec_abatement_reduces_annual_federal_tax() -> None:
    ontario = calculate_federal_income_tax(
        FederalTaxInput(
            gross_pay=Decimal("1000"),
            cpp=Decimal("204.25"),
            ei=Decimal("16.30"),
            pay_periods_per_year=52,
            province="ON",
        )
    )
    quebec = calculate_federal_income_tax(
        FederalTaxInput(
            gross_pay=Decimal("1000"),
            cpp=Decimal("220.00"),
            ei=Decimal("13.00"),
            pay_periods_per_year=52,
            province="QC",
        )
    )
    assert quebec.annual_federal_tax < ontario.annual_federal_tax


def test_claim_code_zero_increases_tax() -> None:
    default_claim = calculate_federal_income_tax(
        FederalTaxInput(
            gross_pay=Decimal("2000"),
            cpp=Decimal("120"),
            ei=Decimal("32"),
            pay_periods_per_year=26,
            province="ON",
            federal_claim_code=1,
        )
    )
    no_claim = calculate_federal_income_tax(
        FederalTaxInput(
            gross_pay=Decimal("2000"),
            cpp=Decimal("120"),
            ei=Decimal("32"),
            pay_periods_per_year=26,
            province="ON",
            federal_claim_code=0,
        )
    )
    assert no_claim.federal_income_tax > default_claim.federal_income_tax


def test_invalid_claim_code_raises() -> None:
    with pytest.raises(ValueError, match="federalClaimCode"):
        calculate_federal_income_tax(
            FederalTaxInput(
                gross_pay=Decimal("1000"),
                cpp=Decimal("50"),
                ei=Decimal("16"),
                pay_periods_per_year=52,
                federal_claim_code=11,
            )
        )


def test_calculate_deductions_api_model() -> None:
    from app.models.deductions import CalculateDeductionsRequest
    from app.services.payroll_deductions_service import calculate_payroll_deductions

    response = calculate_payroll_deductions(
        CalculateDeductionsRequest.model_validate(
            {
                "grossPay": "1000.00",
                "payPeriodsPerYear": 52,
                "province": "ON",
            }
        )
    )
    assert response.cpp == Decimal("55.50")
    assert response.ei == Decimal("16.30")
    assert response.qpip == Decimal("0.00")
    assert response.provincial_income_tax == Decimal("0.00")
    assert response.income_tax == response.federal_income_tax
    assert response.net_pay == Decimal("1000.00") - response.cpp - response.ei - response.income_tax
