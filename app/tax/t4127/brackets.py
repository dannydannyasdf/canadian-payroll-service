"""Bracket lookup for T4127 progressive tax rates."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class TaxBracketTable:
    thresholds: tuple[Decimal, ...]
    rates: tuple[Decimal, ...]
    constants: tuple[Decimal, ...]

    def lookup(self, annual_taxable_income: Decimal) -> tuple[Decimal, Decimal]:
        """Return (R, K) for annual taxable income A."""
        income = max(annual_taxable_income, Decimal("0"))
        rate = self.rates[0]
        constant = self.constants[0]
        for index in range(len(self.thresholds) - 1, -1, -1):
            if income >= self.thresholds[index]:
                rate = self.rates[index]
                constant = self.constants[index]
                break
        return rate, constant
