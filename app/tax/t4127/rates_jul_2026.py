"""CRA T4127 rate tables — 123rd edition effective July 1, 2026.

Source: Table 8.1 and Table 8.2 in T4127-JUL, bundled from
https://www.canada.ca/content/dam/cra-arc/formspubs/pub/t4127-jul/rates-income-thresholds-constants-26e.csv
"""

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

# Table 8.9 — federal claim code 1 (maximum BPAF), Option 1.
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

CPP_TOTAL_RATE = Decimal("0.0595")
CPP_BASE_RATE = Decimal("0.0495")
CPP_MAX_BASE_CONTRIBUTION = Decimal("3519.45")

QPP_TOTAL_RATE = Decimal("0.0630")
QPP_BASE_RATE = Decimal("0.0530")
QPP_MAX_BASE_CONTRIBUTION = Decimal("3768.30")

EI_MAX_PREMIUM = Decimal("1123.07")
EI_MAX_PREMIUM_QC = Decimal("895.70")
QPIP_RATE = Decimal("0.0043")
QPIP_MAX_PREMIUM = Decimal("442.90")

LCF_MAX = Decimal("750")
