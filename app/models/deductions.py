"""Request/response models for payroll deduction calculations."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CalculateDeductionsRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    gross_pay: Decimal = Field(alias="grossPay", gt=0)
    cpp: Decimal | None = Field(
        default=None,
        ge=0,
        description="Optional override for employee CPP/QPP (factor C + C2). Computed when omitted.",
    )
    ei: Decimal | None = Field(
        default=None,
        ge=0,
        description="Optional override for EI premium. Computed when omitted.",
    )
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
    provincial_claim_code: int = Field(
        alias="provincialClaimCode",
        default=1,
        ge=0,
        le=10,
        description="Québec TP-1015.3-V deduction code (0–10). Used when province is QC.",
    )
    insurable_earnings: Decimal | None = Field(
        default=None,
        alias="insurableEarnings",
        ge=0,
        description="EI/QPIP insurable earnings for the period; defaults to grossPay.",
    )
    ytd_cpp: Decimal = Field(default=Decimal("0"), alias="ytdCpp", ge=0)
    ytd_cpp2: Decimal = Field(default=Decimal("0"), alias="ytdCpp2", ge=0)
    ytd_pensionable_earnings: Decimal = Field(default=Decimal("0"), alias="ytdPensionableEarnings", ge=0)
    ytd_ei: Decimal = Field(default=Decimal("0"), alias="ytdEi", ge=0)
    ytd_qpip: Decimal = Field(default=Decimal("0"), alias="ytdQpip", ge=0)
    ytd_insurable_earnings: Decimal = Field(default=Decimal("0"), alias="ytdInsurableEarnings", ge=0)
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
    pension_months: int = Field(
        default=12,
        alias="pensionMonths",
        ge=1,
        le=12,
        description="Months of CPP/QPP contributions required (factor PM).",
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
        description="Québec provincial income tax for the period (QC only).",
    )


class QuebecTaxBreakdown(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    annual_taxable_income: Decimal = Field(alias="annualTaxableIncome")
    annual_basic_quebec_tax: Decimal = Field(alias="annualBasicQuebecTax")
    annual_quebec_tax: Decimal = Field(alias="annualQuebecTax")
    provincial_income_tax: Decimal = Field(alias="provincialIncomeTax")
    method: str = "TP-1015.F-V Option 1 (2026-01)"


class CalculateDeductionsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cpp: Decimal = Field(description="Employee CPP or QPP contribution for the period (C + C2).")
    cpp2: Decimal = Field(description="Second additional CPP/QPP contribution (C2).")
    ei: Decimal
    qpip: Decimal = Field(description="Québec Parental Insurance Plan premium (QC only).")
    federal_income_tax: Decimal = Field(alias="federalIncomeTax")
    provincial_income_tax: Decimal = Field(
        default=Decimal("0"),
        alias="provincialIncomeTax",
        description="Québec provincial income tax for the period (QC only).",
    )
    income_tax: Decimal = Field(
        alias="incomeTax",
        description="Total income tax withheld for the period (federal + provincial).",
    )
    net_pay: Decimal = Field(alias="netPay")
    federal: FederalTaxBreakdown
    quebec: QuebecTaxBreakdown | None = None
