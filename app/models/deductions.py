"""Request/response models for payroll deduction calculations."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CalculateDeductionsRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    gross_pay: Decimal = Field(alias="grossPay", gt=0)
    cpp: Decimal = Field(ge=0, description="Employee CPP or QPP contribution for this pay period (factor C).")
    ei: Decimal = Field(ge=0, description="Employee EI premium for this pay period.")
    pay_periods_per_year: int = Field(alias="payPeriodsPerYear", default=52, gt=0, le=53)
    province: str = Field(
        default="ON",
        min_length=2,
        max_length=2,
        description="Employment province code (QC uses QPP/QPIP credits and federal abatement).",
    )
    federal_claim_code: int = Field(
        alias="federalClaimCode",
        default=1,
        ge=0,
        le=10,
        description="Federal TD1 claim code (0–10). Default 1 = maximum BPAF.",
    )
    insurable_earnings: Decimal | None = Field(
        default=None,
        alias="insurableEarnings",
        ge=0,
        description="EI/QPIP insurable earnings for the period; defaults to grossPay.",
    )
    ytd_bonus_taxable: Decimal = Field(
        default=Decimal("0"),
        alias="ytdBonusTaxable",
        ge=0,
        description="Prior non-periodic payments included in annualized income (B1 − F4 − F5BYTD).",
    )
    ytd_cpp_additional_deduction: Decimal = Field(
        default=Decimal("0"),
        alias="ytdCppAdditionalDeduction",
        ge=0,
        description="Prior F5BYTD amount to subtract from annualized income.",
    )
    additional_tax_per_period: Decimal = Field(
        default=Decimal("0"),
        alias="additionalTaxPerPeriod",
        ge=0,
        description="Extra tax per period requested on TD1 (factor L).",
    )

    @field_validator("province")
    @classmethod
    def normalize_province(cls, value: str) -> str:
        return value.upper()


class FederalTaxBreakdown(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    annual_taxable_income: Decimal = Field(alias="annualTaxableIncome")
    annual_basic_federal_tax: Decimal = Field(alias="annualBasicFederalTax")
    annual_federal_tax: Decimal = Field(alias="annualFederalTax")
    federal_income_tax: Decimal = Field(alias="federalIncomeTax")
    cpp_additional_deduction: Decimal = Field(alias="cppAdditionalDeduction")
    method: str = "T4127 Option 1 (July 2026)"
    provincial_income_tax: Decimal | None = Field(
        default=None,
        alias="provincialIncomeTax",
        description="Not calculated yet — use Revenu Québec formulas for QC provincial tax.",
    )


class CalculateDeductionsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    federal: FederalTaxBreakdown
    income_tax: Decimal = Field(
        alias="incomeTax",
        description="Total income tax for the period. Currently equals federal only.",
    )
