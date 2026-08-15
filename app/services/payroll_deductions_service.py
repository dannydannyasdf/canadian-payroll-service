"""Payroll deduction calculation service (CRA T4127)."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from app.models.deductions import CalculateDeductionsRequest, CalculateDeductionsResponse, FederalTaxBreakdown
from app.tax.t4127.cpp_ei import CppEiInput, calculate_cpp_ei
from app.tax.t4127.federal import FederalTaxInput, calculate_federal_income_tax

MONEY_QUANT = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def calculate_payroll_deductions(payload: CalculateDeductionsRequest) -> CalculateDeductionsResponse:
    cpp_ei_input = CppEiInput(
        gross_pay=payload.gross_pay,
        pay_periods_per_year=payload.pay_periods_per_year,
        province=payload.province,
        ytd_cpp=payload.ytd_cpp,
        ytd_cpp2=payload.ytd_cpp2,
        ytd_pensionable_earnings=payload.ytd_pensionable_earnings,
        ytd_ei=payload.ytd_ei,
        ytd_qpip=payload.ytd_qpip,
        ytd_insurable_earnings=payload.ytd_insurable_earnings,
        pension_months=payload.pension_months,
    )
    cpp_ei = calculate_cpp_ei(cpp_ei_input)

    cpp = payload.cpp if payload.cpp is not None else cpp_ei.cpp
    ei = payload.ei if payload.ei is not None else cpp_ei.ei

    federal_result = calculate_federal_income_tax(
        FederalTaxInput(
            gross_pay=payload.gross_pay,
            cpp=cpp,
            ei=ei,
            pay_periods_per_year=payload.pay_periods_per_year,
            federal_claim_code=payload.federal_claim_code,
            province=payload.province,
            insurable_earnings=payload.insurable_earnings or payload.gross_pay,
            ytd_bonus_taxable=payload.ytd_bonus_taxable,
            ytd_cpp_additional_deduction=payload.ytd_cpp_additional_deduction,
            pension_months=payload.pension_months,
            additional_tax_per_period=payload.additional_tax_per_period,
        )
    )

    net_pay = _money(payload.gross_pay - cpp - ei - cpp_ei.qpip - federal_result.federal_income_tax)

    federal = FederalTaxBreakdown(
        annualTaxableIncome=federal_result.annual_taxable_income,
        annualBasicFederalTax=federal_result.annual_basic_federal_tax,
        annualFederalTax=federal_result.annual_federal_tax,
        federalIncomeTax=federal_result.federal_income_tax,
        cppAdditionalDeduction=federal_result.cpp_additional_deduction,
    )
    return CalculateDeductionsResponse(
        cpp=cpp,
        cpp2=cpp_ei.cpp2,
        ei=ei,
        qpip=cpp_ei.qpip,
        incomeTax=federal_result.federal_income_tax,
        netPay=net_pay,
        federal=federal,
    )
