"""CRA T4127 rate tables — 123rd edition effective July 1, 2026."""

from __future__ import annotations

from decimal import Decimal

from app.tax.t4127.brackets import TaxBracketTable

FEDERAL_BRACKETS = TaxBracketTable(
    thresholds=(
        Decimal("0"),
        Decimal("58523"),
        Decimal("117045"),
        Decimal("181440"),
        Decimal("258482"),
    ),
    rates=(
        Decimal("0.14"),
        Decimal("0.205"),
        Decimal("0.26"),
        Decimal("0.29"),
        Decimal("0.33"),
    ),
    constants=(
        Decimal("0"),
        Decimal("3804"),
        Decimal("10241"),
        Decimal("15685"),
        Decimal("26024"),
    ),
)

FEDERAL_CLAIM_CODE_TC: dict[int, Decimal] = {
    0: Decimal("0"),
    1: Decimal("16452"),
    2: Decimal("17868.50"),
    3: Decimal("20701.50"),
    4: Decimal("23534.50"),
    5: Decimal("26367.50"),
    6: Decimal("29200.50"),
    7: Decimal("32033.50"),
    8: Decimal("34866.50"),
    9: Decimal("37699.50"),
    10: Decimal("40532.50"),
}

FEDERAL_LOWEST_RATE = Decimal("0.14")
CANADA_EMPLOYMENT_AMOUNT = Decimal("1501")
QC_FEDERAL_ABATEMENT_RATE = Decimal("0.165")

CPP_BASIC_EXEMPTION = Decimal("3500")
CPP_YMPE = Decimal("74600")
CPP_YAMPE = Decimal("85000")
CPP_TOTAL_RATE = Decimal("0.0595")
CPP_BASE_RATE = Decimal("0.0495")
CPP_MAX_TOTAL_CONTRIBUTION = Decimal("4230.45")
CPP_MAX_BASE_CONTRIBUTION = Decimal("3519.45")
CPP2_MAX_CONTRIBUTION = Decimal("416.00")
CPP2_RATE = Decimal("0.04")

QPP_TOTAL_RATE = Decimal("0.0630")
QPP_BASE_RATE = Decimal("0.0530")
QPP_MAX_TOTAL_CONTRIBUTION = Decimal("4479.30")
QPP_MAX_BASE_CONTRIBUTION = Decimal("3768.30")

EI_MAX_INSURABLE_EARNINGS = Decimal("68900")
EI_RATE = Decimal("0.0163")
EI_MAX_PREMIUM = Decimal("1123.07")
EI_RATE_QC = Decimal("0.0130")
EI_MAX_PREMIUM_QC = Decimal("895.70")

QPIP_MAX_INSURABLE_EARNINGS = Decimal("103000")
QPIP_RATE = Decimal("0.0043")
QPIP_MAX_PREMIUM = Decimal("442.90")

LCF_MAX = Decimal("750")
