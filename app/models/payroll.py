from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.sin import normalize_sin


class Employer(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int | None = None
    name: str


class Employee(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int | None = None
    name: str
    sin: str

    @field_validator("sin")
    @classmethod
    def validate_sin(cls, value: str) -> str:
        return normalize_sin(value)


class PayPeriod(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    start_date: date = Field(alias="startDate")
    end_date: date = Field(alias="endDate")
    pay_date: date = Field(alias="payDate")


class Earnings(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    gross_pay: Decimal = Field(alias="grossPay")


class Deductions(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cpp: Decimal
    ei: Decimal
    income_tax: Decimal = Field(alias="incomeTax")
    federal_income_tax: Decimal | None = Field(default=None, alias="federalIncomeTax", ge=0)
    provincial_income_tax: Decimal | None = Field(default=None, alias="provincialIncomeTax", ge=0)
    qpip: Decimal = Field(default=Decimal("0"), ge=0)

    @model_validator(mode="after")
    def resolve_income_tax_split(self) -> "Deductions":
        if self.federal_income_tax is not None or self.provincial_income_tax is not None:
            federal = self.federal_income_tax or Decimal("0")
            provincial = self.provincial_income_tax or Decimal("0")
            expected_total = federal + provincial
            if self.income_tax != expected_total:
                raise ValueError(
                    f"incomeTax must equal federalIncomeTax plus provincialIncomeTax "
                    f"(expected {expected_total}, got {self.income_tax})"
                )
            self.federal_income_tax = federal
            self.provincial_income_tax = provincial
        else:
            self.federal_income_tax = self.income_tax
            self.provincial_income_tax = Decimal("0")
        return self

    @property
    def total_income_tax(self) -> Decimal:
        return self.federal_income_tax + self.provincial_income_tax


class PayrollPayload(BaseModel):
    """
    Canonical payroll input — used by both JSON and XML ingress paths.
    """

    model_config = ConfigDict(populate_by_name=True)

    employer: Employer
    employee: Employee
    pay_period: PayPeriod = Field(alias="payPeriod")
    earnings: Earnings
    deductions: Deductions
    net_pay: Decimal = Field(alias="netPay")
    comments: str | None = Field(default=None, max_length=2000)
    comments2: str | None = Field(default=None, max_length=2000)

    @field_validator("net_pay")
    @classmethod
    def validate_net_pay(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError("netPay must be zero or greater")
        return value

    @model_validator(mode="after")
    def validate_net_matches_deductions(self) -> "PayrollPayload":
        expected_net = (
            self.earnings.gross_pay
            - self.deductions.cpp
            - self.deductions.ei
            - self.deductions.qpip
            - self.deductions.federal_income_tax
            - self.deductions.provincial_income_tax
        )
        if self.net_pay != expected_net:
            raise ValueError(
                f"netPay must equal grossPay minus CPP, EI, QPIP, federal income tax, and "
                f"provincial income tax (expected {expected_net}, got {self.net_pay})"
            )
        return self

    def to_render_dict(self) -> dict:
        """Flat dict for the Jinja2 pay stub template."""
        return {
            "employer_name": self.employer.name,
            "employee_name": self.employee.name,
            "employee_sin": self.employee.sin,
            "period_start": self.pay_period.start_date.isoformat(),
            "period_end": self.pay_period.end_date.isoformat(),
            "pay_date": self.pay_period.pay_date.isoformat(),
            "gross_pay": self.earnings.gross_pay,
            "cpp": self.deductions.cpp,
            "ei": self.deductions.ei,
            "qpip": self.deductions.qpip,
            "federal_income_tax": self.deductions.federal_income_tax,
            "provincial_income_tax": self.deductions.provincial_income_tax,
            "income_tax": self.deductions.federal_income_tax,
            "net_pay": self.net_pay,
            "comments": self.comments,
        }
