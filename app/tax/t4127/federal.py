"""Federal income tax withholding — CRA T4127 Option 1 (Chapter 4).

Implements Steps 1–3 and Step 6 (federal portion only) for regular periodic
payments. Provincial/territorial tax (T2) and Québec provincial tax are not
included yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.tax.t4127.rates_jul_2026 import (
    CANADA_EMPLOYMENT_AMOUNT,
    CPP_BASE_RATE,
    CPP_MAX_BASE_CONTRIBUTION,
    CPP_TOTAL_RATE,
    EI_MAX_PREMIUM,
    EI_MAX_PREMIUM_QC,
    FEDERAL_BRACKETS,
    FEDERAL_CLAIM_CODE_TC,
    FEDERAL_LOWEST_RATE,
    QC_FEDERAL_ABATEMENT_RATE,
    QPIP_MAX_PREMIUM,
    QPIP_RATE,
    QPP_BASE_RATE,
    QPP_MAX_BASE_CONTRIBUTION,
    QPP_TOTAL_RATE,
)

QC_PROVINCE = "QC"
MONEY_QUANT = Decimal("0.01")


@dataclass(frozen=True)
class FederalTaxInput:
    gross_pay: Decimal
    cpp: Decimal
    ei: Decimal
    pay_periods_per_year: int
    federal_claim_code: int = 1  # TD1 federal claim code 0–10.
    province: str = "ON"
    insurable_earnings: Decimal | None = None
    ytd_bonus_taxable: Decimal = Decimal("0")
    ytd_cpp_additional_deduction: Decimal = Decimal("0")
    pension_months: int = 12
    additional_tax_per_period: Decimal = Decimal("0")
    labour_sponsored_credit_per_period: Decimal = Decimal("0")


@dataclass(frozen=True)
class FederalTaxResult:
    annual_taxable_income: Decimal
    annual_basic_federal_tax: Decimal
    annual_federal_tax: Decimal
    federal_income_tax: Decimal
    cpp_additional_deduction: Decimal


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _is_quebec(province: str) -> bool:
    return province.upper() == QC_PROVINCE


def _f5_from_cpp(cpp: Decimal, *, quebec: bool) -> Decimal:
    total_rate = QPP_TOTAL_RATE if quebec else CPP_TOTAL_RATE
    return _money(cpp * (Decimal("0.0100") / total_rate))


def _annual_taxable_income(data: FederalTaxInput) -> Decimal:
    """T4127 Step 1 — regular periodic payment (no current-period bonus)."""
    f5a = _f5_from_cpp(data.cpp, quebec=_is_quebec(data.province))
    periodic = data.gross_pay - f5a
    annualized = Decimal(data.pay_periods_per_year) * periodic
    annualized += data.ytd_bonus_taxable - data.ytd_cpp_additional_deduction
    return _money(max(annualized, Decimal("0")))


def _federal_total_claim(claim_code: int) -> Decimal:
    try:
        return FEDERAL_CLAIM_CODE_TC[claim_code]
    except KeyError as exc:
        raise ValueError("federalClaimCode must be between 0 and 10") from exc


def _k1(total_claim: Decimal) -> Decimal:
    return _money(FEDERAL_LOWEST_RATE * total_claim)


def _k2_cpp_ei(
    data: FederalTaxInput,
    *,
    quebec: bool,
) -> Decimal:
    pm_factor = Decimal(data.pension_months) / Decimal("12")
    p = Decimal(data.pay_periods_per_year)

    if quebec:
        base_ratio = QPP_BASE_RATE / QPP_TOTAL_RATE
        max_base = QPP_MAX_BASE_CONTRIBUTION * pm_factor
        ei_max = EI_MAX_PREMIUM_QC
    else:
        base_ratio = CPP_BASE_RATE / CPP_TOTAL_RATE
        max_base = CPP_MAX_BASE_CONTRIBUTION * pm_factor
        ei_max = EI_MAX_PREMIUM

    cpp_annualized = min(p * data.cpp * base_ratio, max_base)
    ei_annualized = min(p * data.ei, ei_max)

    credit = FEDERAL_LOWEST_RATE * (cpp_annualized + ei_annualized)

    if quebec:
        insurable = data.insurable_earnings if data.insurable_earnings is not None else data.gross_pay
        qpip_annualized = min(p * insurable * QPIP_RATE, QPIP_MAX_PREMIUM)
        credit += FEDERAL_LOWEST_RATE * qpip_annualized

    return _money(credit)


def _k4(annual_taxable_income: Decimal) -> Decimal:
    return _money(min(FEDERAL_LOWEST_RATE * annual_taxable_income, FEDERAL_LOWEST_RATE * CANADA_EMPLOYMENT_AMOUNT))


def _annual_basic_federal_tax(annual_taxable_income: Decimal, data: FederalTaxInput) -> Decimal:
    rate, constant = FEDERAL_BRACKETS.lookup(annual_taxable_income)
    total_claim = _federal_total_claim(data.federal_claim_code)
    k1 = _k1(total_claim)
    k2 = _k2_cpp_ei(data, quebec=_is_quebec(data.province))
    k4 = _k4(annual_taxable_income)

    tax = (rate * annual_taxable_income) - constant - k1 - k2 - k4
    return _money(max(tax, Decimal("0")))


def _annual_federal_tax_payable(t3: Decimal, data: FederalTaxInput) -> Decimal:
    lcf = data.labour_sponsored_credit_per_period * Decimal(data.pay_periods_per_year)
    after_lcf = max(t3 - lcf, Decimal("0"))

    if _is_quebec(data.province):
        after_lcf -= QC_FEDERAL_ABATEMENT_RATE * t3

    return _money(max(after_lcf, Decimal("0")))


def calculate_federal_income_tax(data: FederalTaxInput) -> FederalTaxResult:
    """Calculate per-period federal income tax using T4127 Option 1."""
    if data.pay_periods_per_year <= 0:
        raise ValueError("payPeriodsPerYear must be positive")

    annual_a = _annual_taxable_income(data)
    t3 = _annual_basic_federal_tax(annual_a, data)
    t1 = _annual_federal_tax_payable(t3, data)
    per_period = _money(t1 / Decimal(data.pay_periods_per_year) + data.additional_tax_per_period)

    return FederalTaxResult(
        annual_taxable_income=annual_a,
        annual_basic_federal_tax=t3,
        annual_federal_tax=t1,
        federal_income_tax=per_period,
        cpp_additional_deduction=_money(_f5_from_cpp(data.cpp, quebec=_is_quebec(data.province))),
    )
