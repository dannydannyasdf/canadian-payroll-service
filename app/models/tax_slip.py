from pydantic import BaseModel, Field


class TaxPartyAddress(BaseModel):
    line1: str | None = None
    city: str | None = None
    province: str | None = None
    postalCode: str | None = None


class T4EmployerSummary(BaseModel):
    name: str
    businessNumber: str | None = None
    payrollAccountNumber: str | None = None
    address: TaxPartyAddress


class T4EmployeeSummary(BaseModel):
    id: int
    name: str
    sin: str
    address: TaxPartyAddress
    employmentProvince: str | None = None


class T4SlipPreview(BaseModel):
    """JSON preview of a T4 slip before PDF / CRA e-file generation."""

    taxYear: int
    employee: T4EmployeeSummary
    employer: T4EmployerSummary
    boxes: dict[str, str] = Field(description="CRA T4 box number to amount")
    boxLabels: dict[str, str]
    disclaimers: list[str]
    status: str = "preview"


class Releve1SlipPreview(BaseModel):
    """JSON preview of a Relevé 1 slip before PDF / RQ e-file generation."""

    taxYear: int
    employee: T4EmployeeSummary
    employer: T4EmployerSummary
    boxes: dict[str, str] = Field(description="Revenu Québec box letter to amount")
    boxLabels: dict[str, str]
    disclaimers: list[str]
    status: str = "preview"
