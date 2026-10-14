"""Revenu Québec TP-1015.F-V rate tables — 2026-01 edition."""

from __future__ import annotations

from decimal import Decimal

from app.tax.t4127.brackets import TaxBracketTable

QC_LOWEST_RATE = Decimal("0.14")
QC_BASIC_PERSONAL_AMOUNT = Decimal("18952")

QC_BRACKETS = TaxBracketTable(
    thresholds=(
        Decimal("0"),
        Decimal("54345"),
        Decimal("108680"),
        Decimal("132245"),
    ),
    rates=(
        Decimal("0.14"),
        Decimal("0.19"),
        Decimal("0.24"),
        Decimal("0.2575"),
    ),
    constants=(
        Decimal("0"),
        Decimal("2717.25"),
        Decimal("8151.25"),
        Decimal("10465.54"),
    ),
)

# TP-1015.3-V deduction-code midpoints (Option 1), indexed 2.05% from 2025-01.
QC_CLAIM_CODE_TC: dict[int, Decimal] = {
    0: Decimal("0"),
    1: Decimal("18952.00"),
    2: Decimal("20349.18"),
    3: Decimal("23199.13"),
    4: Decimal("25988.57"),
    5: Decimal("28833.77"),
    6: Decimal("31683.96"),
    7: Decimal("34454.25"),
    8: Decimal("37347.14"),
    9: Decimal("40194.23"),
    10: Decimal("43048.92"),
}
