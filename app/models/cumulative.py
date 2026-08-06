from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CumulativeTotals(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    gross_pay: Decimal = Field(alias="grossPay")
    cpp: Decimal
    ei: Decimal
    income_tax: Decimal = Field(alias="incomeTax")
    net_pay: Decimal = Field(alias="netPay")


class LastPayPeriod(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    start_date: date = Field(alias="startDate")
    end_date: date = Field(alias="endDate")
    pay_date: date = Field(alias="payDate")


class CumulativeResponse(BaseModel):
    """Year-to-date totals returned to the client after each pay stub run."""

    model_config = ConfigDict(populate_by_name=True)

    tax_year: int = Field(alias="taxYear")
    employee_id: int = Field(alias="employeeId")
    employer_name: str = Field(alias="employerName")
    employee_name: str = Field(alias="employeeName")
    employee_sin: str = Field(alias="employeeSin")
    totals: CumulativeTotals
    last_pay_period: LastPayPeriod = Field(alias="lastPayPeriod")

    def to_render_dict(self) -> dict[str, object]:
        """YTD fields for the Jinja2 pay stub template."""
        return {
            "tax_year": self.tax_year,
            "ytd_gross_pay": self.totals.gross_pay,
            "ytd_cpp": self.totals.cpp,
            "ytd_ei": self.totals.ei,
            "ytd_income_tax": self.totals.income_tax,
            "ytd_net_pay": self.totals.net_pay,
        }


class PayStubResponse(BaseModel):
    """JSON response: cumulative YTD state plus the generated pay stub PDF."""

    cumulative: CumulativeResponse
    pay_stub_pdf_base64: str = Field(alias="payStubPdfBase64")
