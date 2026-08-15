"""CPP/QPP, CPP2, EI, and QPIP — CRA T4127 Chapters 6–7."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.tax.t4127.rates_jul_2026 import (
    CPP2_MAX_CONTRIBUTION,
    CPP2_RATE,
    CPP_BASIC_EXEMPTION,
    CPP_MAX_TOTAL_CONTRIBUTION,
    CPP_TOTAL_RATE,
    CPP_YMPE,
    EI_MAX_INSURABLE_EARNINGS,
    EI_MAX_PREMIUM,
    EI_MAX_PREMIUM_QC,
    EI_RATE,
    EI_RATE_QC,
    QPIP_MAX_INSURABLE_EARNINGS,
    QPIP_MAX_PREMIUM,
    QPIP_RATE,
    QPP_MAX_TOTAL_CONTRIBUTION,
    QPP_TOTAL_RATE,
)

QC_PROVINCE = "QC"
MONEY_QUANT = Decimal("0.01")


@dataclass(frozen=True)
class CppEiInput:
    gross_pay: Decimal
    pay_periods_per_year: int
    province: str = "ON"
    ytd_cpp: Decimal = Decimal("0")
    ytd_cpp2: Decimal = Decimal("0")
    ytd_pensionable_earnings: Decimal = Decimal("0")
    ytd_ei: Decimal = Decimal("0")
    ytd_qpip: Decimal = Decimal("0")
    ytd_insurable_earnings: Decimal = Decimal("0")
    pension_months: int = 12


@dataclass(frozen=True)
class CppEiResult:
    cpp: Decimal
    cpp2: Decimal
    ei: Decimal
    qpip: Decimal


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _is_quebec(province: str) -> bool:
    return province.upper() == QC_PROVINCE


def _capped_insurable(
    gross_pay: Decimal,
    *,
    ytd_insurable: Decimal,
    annual_max: Decimal,
) -> Decimal:
    remaining = annual_max - ytd_insurable
    if remaining <= 0:
        return Decimal("0")
    return min(gross_pay, remaining)


def calculate_cpp(data: CppEiInput) -> tuple[Decimal, Decimal]:
    """Return (C, C2) employee CPP or QPP contributions for the pay period."""
    if data.pay_periods_per_year <= 0:
        raise ValueError("payPeriodsPerYear must be positive")

    quebec = _is_quebec(data.province)
    max_total = QPP_MAX_TOTAL_CONTRIBUTION if quebec else CPP_MAX_TOTAL_CONTRIBUTION
    rate = QPP_TOTAL_RATE if quebec else CPP_TOTAL_RATE
    pm_factor = Decimal(data.pension_months) / Decimal("12")
    p = Decimal(data.pay_periods_per_year)
    pi = data.gross_pay

    basic_exemption_per_period = CPP_BASIC_EXEMPTION / p
    remaining_annual = max(max_total * pm_factor - data.ytd_cpp, Decimal("0"))
    periodic_amount = rate * (pi - basic_exemption_per_period)
    cpp = _money(max(Decimal("0"), min(remaining_annual, periodic_amount)))

    ympe_prorated = CPP_YMPE * pm_factor
    w = max(data.ytd_pensionable_earnings, ympe_prorated)
    remaining_cpp2 = max(CPP2_MAX_CONTRIBUTION * pm_factor - data.ytd_cpp2, Decimal("0"))
    cpp2_periodic = (data.ytd_pensionable_earnings + pi - w) * CPP2_RATE
    cpp2 = _money(max(Decimal("0"), min(remaining_cpp2, cpp2_periodic)))

    return cpp, cpp2


def calculate_ei(data: CppEiInput) -> Decimal:
    """Return EI premium for the pay period."""
    quebec = _is_quebec(data.province)
    max_premium = EI_MAX_PREMIUM_QC if quebec else EI_MAX_PREMIUM
    rate = EI_RATE_QC if quebec else EI_RATE

    insurable = _capped_insurable(
        data.gross_pay,
        ytd_insurable=data.ytd_insurable_earnings,
        annual_max=EI_MAX_INSURABLE_EARNINGS,
    )
    remaining = max(max_premium - data.ytd_ei, Decimal("0"))
    return _money(max(Decimal("0"), min(remaining, rate * insurable)))


def calculate_qpip(data: CppEiInput) -> Decimal:
    """Return QPIP premium for the pay period (Québec only)."""
    if not _is_quebec(data.province):
        return Decimal("0.00")

    insurable = _capped_insurable(
        data.gross_pay,
        ytd_insurable=data.ytd_insurable_earnings,
        annual_max=QPIP_MAX_INSURABLE_EARNINGS,
    )
    remaining = max(QPIP_MAX_PREMIUM - data.ytd_qpip, Decimal("0"))
    return _money(max(Decimal("0"), min(remaining, QPIP_RATE * insurable)))


def calculate_cpp_ei(data: CppEiInput) -> CppEiResult:
    cpp, cpp2 = calculate_cpp(data)
    ei = calculate_ei(data)
    qpip = calculate_qpip(data)
    return CppEiResult(cpp=_money(cpp + cpp2), cpp2=cpp2, ei=ei, qpip=qpip)
