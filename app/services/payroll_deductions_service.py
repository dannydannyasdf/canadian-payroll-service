"""Payroll deduction calculation service (CRA T4127)."""

from __future__ import annotations

from app.models.deductions import CalculateDeductionsRequest, CalculateDeductionsResponse, FederalTaxBreakdown
from app.tax.t4127.federal import FederalTaxInput, calculate_federal_income_tax


def calculate_payroll_deductions(payload: CalculateDeductionsRequest) -> CalculateDeductionsResponse:
    result = calculate_federal_income_tax(
        FederalTaxInput(
            gross_pay=payload.gross_pay,
            cpp=payload.cpp,
            ei=payload.ei,
            pay_periods_per_year=payload.pay_periods_per_year,
            federal_claim_code=payload.federal_claim_code,
            province=payload.province,
            insurable_earnings=payload.insurable_earnings,
            ytd_bonus_taxable=payload.ytd_bonus_taxable,
            ytd_cpp_additional_deduction=payload.ytd_cpp_additional_deduction,
            additional_tax_per_period=payload.additional_tax_per_period,
        )
    )

    federal = FederalTaxBreakdown(
        annualTaxableIncome=result.annual_taxable_income,
        annualBasicFederalTax=result.annual_basic_federal_tax,
        annualFederalTax=result.annual_federal_tax,
        federalIncomeTax=result.federal_income_tax,
        cppAdditionalDeduction=result.cpp_additional_deduction,
    )
    return CalculateDeductionsResponse(federal=federal, incomeTax=result.federal_income_tax)
