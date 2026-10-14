"""Tests for Revenu Québec TP-1015.F-V provincial income tax."""

from decimal import Decimal

import pytest

from app.models.deductions import CalculateDeductionsRequest
from app.services.payroll_deductions_service import calculate_payroll_deductions
from app.tax.rq.provincial import QuebecTaxInput, calculate_quebec_income_tax
from app.tax.rq.rates_2026_01 import QC_BRACKETS


def test_qc_bracket_lookup_first_bracket() -> None:
    rate, constant = QC_BRACKETS.lookup(Decimal("50000"))
    assert rate == Decimal("0.14")
    assert constant == Decimal("0")


def test_qc_weekly_salary_provincial_tax() -> None:
    """First-period weekly employee — $1,000 gross, Québec, claim code 1."""
    result = calculate_quebec_income_tax(
        QuebecTaxInput(
            gross_pay=Decimal("1000"),
            cpp=Decimal("58.76"),
            ei=Decimal("13.00"),
            qpip=Decimal("4.30"),
            pay_periods_per_year=52,
            provincial_claim_code=1,
        )
    )
    assert result.annual_taxable_income == Decimal("51514.84")
    assert result.provincial_income_tax == Decimal("78.33")


def test_qc_claim_code_zero_increases_tax() -> None:
    default_claim = calculate_quebec_income_tax(
        QuebecTaxInput(
            gross_pay=Decimal("2000"),
            cpp=Decimal("120"),
            ei=Decimal("26"),
            qpip=Decimal("8.60"),
            pay_periods_per_year=26,
            provincial_claim_code=1,
        )
    )
    no_claim = calculate_quebec_income_tax(
        QuebecTaxInput(
            gross_pay=Decimal("2000"),
            cpp=Decimal("120"),
            ei=Decimal("26"),
            qpip=Decimal("8.60"),
            pay_periods_per_year=26,
            provincial_claim_code=0,
        )
    )
    assert no_claim.provincial_income_tax > default_claim.provincial_income_tax


def test_invalid_qc_claim_code_raises() -> None:
    with pytest.raises(ValueError, match="provincialClaimCode"):
        calculate_quebec_income_tax(
            QuebecTaxInput(
                gross_pay=Decimal("1000"),
                cpp=Decimal("50"),
                ei=Decimal("13"),
                qpip=Decimal("4.30"),
                pay_periods_per_year=52,
                provincial_claim_code=11,
            )
        )


def test_qc_payroll_deductions_split_federal_and_provincial() -> None:
    response = calculate_payroll_deductions(
        CalculateDeductionsRequest.model_validate(
            {
                "grossPay": "1000.00",
                "payPeriodsPerYear": 52,
                "province": "QC",
            }
        )
    )
    assert response.provincial_income_tax > Decimal("0")
    assert response.federal_income_tax > Decimal("0")
    assert response.provincial_income_tax != response.federal_income_tax
    assert response.income_tax == response.federal_income_tax + response.provincial_income_tax
    assert response.quebec is not None
    assert response.net_pay == (
        Decimal("1000.00")
        - response.cpp
        - response.ei
        - response.qpip
        - response.income_tax
    )


def test_on_payroll_deductions_have_no_provincial_tax() -> None:
    response = calculate_payroll_deductions(
        CalculateDeductionsRequest.model_validate(
            {
                "grossPay": "1000.00",
                "payPeriodsPerYear": 52,
                "province": "ON",
            }
        )
    )
    assert response.provincial_income_tax == Decimal("0.00")
    assert response.income_tax == response.federal_income_tax
    assert response.quebec is None
