"""Québec provincial income tax withholding — Revenu Québec TP-1015.F-V (Option 1).

Implements the regular periodic payment formula for Québec income tax only.
Federal tax is calculated separately via CRA T4127.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.tax.rq.rates_2026_01 import QC_BRACKETS, QC_CLAIM_CODE_TC, QC_LOWEST_RATE
from app.tax.t4127.federal import _f5_from_cpp
from app.tax.t4127.rates_jul_2026 import (
    EI_MAX_PREMIUM_QC,
    QPIP_MAX_PREMIUM,
    QPIP_RATE,
    QPP_BASE_RATE,
    QPP_MAX_BASE_CONTRIBUTION,
    QPP_TOTAL_RATE,
)

MONEY_QUANT = Decimal("0.01")


@dataclass(frozen=True)
class QuebecTaxInput:
    gross_pay: Decimal
    cpp: Decimal
    ei: Decimal
    qpip: Decimal
    pay_periods_per_year: int
    provincial_claim_code: int = 1
    insurable_earnings: Decimal | None = None
    ytd_bonus_taxable: Decimal = Decimal("0")
    ytd_cpp_additional_deduction: Decimal = Decimal("0")
    pension_months: int = 12
    additional_tax_per_period: Decimal = Decimal("0")


@dataclass(frozen=True)
class QuebecTaxResult:
    annual_taxable_income: Decimal
    annual_basic_quebec_tax: Decimal
    annual_quebec_tax: Decimal
    provincial_income_tax: Decimal


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _annual_taxable_income(data: QuebecTaxInput) -> Decimal:
    """TP-1015.F-V Step 1 — regular periodic payment (no current-period bonus)."""
    f5a = _f5_from_cpp(data.cpp, quebec=True)
    periodic = data.gross_pay - f5a
    annualized = Decimal(data.pay_periods_per_year) * periodic
    annualized += data.ytd_bonus_taxable - data.ytd_cpp_additional_deduction
    return _money(max(annualized, Decimal("0")))


def _total_claim(claim_code: int) -> Decimal:
    try:
        return QC_CLAIM_CODE_TC[claim_code]
    except KeyError as exc:
        raise ValueError("provincialClaimCode must be between 0 and 10") from exc


def _k1(total_claim: Decimal) -> Decimal:
    return _money(QC_LOWEST_RATE * total_claim)


def _k2_qpp_ei_qpip(data: QuebecTaxInput) -> Decimal:
    pm_factor = Decimal(data.pension_months) / Decimal("12")
    p = Decimal(data.pay_periods_per_year)
    base_ratio = QPP_BASE_RATE / QPP_TOTAL_RATE
    max_base = QPP_MAX_BASE_CONTRIBUTION * pm_factor

    qpp_annualized = min(p * data.cpp * base_ratio, max_base)
    ei_annualized = min(p * data.ei, EI_MAX_PREMIUM_QC)
    insurable = data.insurable_earnings if data.insurable_earnings is not None else data.gross_pay
    qpip_annualized = min(p * insurable * QPIP_RATE, QPIP_MAX_PREMIUM)

    credit = QC_LOWEST_RATE * (qpp_annualized + ei_annualized + qpip_annualized)
    return _money(credit)


def _annual_basic_quebec_tax(annual_taxable_income: Decimal, data: QuebecTaxInput) -> Decimal:
    rate, constant = QC_BRACKETS.lookup(annual_taxable_income)
    total_claim = _total_claim(data.provincial_claim_code)
    tax = (rate * annual_taxable_income) - constant - _k1(total_claim) - _k2_qpp_ei_qpip(data)
    return _money(max(tax, Decimal("0")))


def calculate_quebec_income_tax(data: QuebecTaxInput) -> QuebecTaxResult:
    """Calculate per-period Québec provincial income tax using TP-1015.F-V Option 1."""
    if data.pay_periods_per_year <= 0:
        raise ValueError("payPeriodsPerYear must be positive")

    annual_a = _annual_taxable_income(data)
    annual_tax = _annual_basic_quebec_tax(annual_a, data)
    per_period = _money(annual_tax / Decimal(data.pay_periods_per_year) + data.additional_tax_per_period)

    return QuebecTaxResult(
        annual_taxable_income=annual_a,
        annual_basic_quebec_tax=annual_tax,
        annual_quebec_tax=annual_tax,
        provincial_income_tax=per_period,
    )
