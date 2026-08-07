from datetime import datetime
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SIN_PATTERN = re.compile(r"^\d{3}-\d{3}-\d{3}$")

RecordStatus = Literal["active", "inactive"]

CANADIAN_PROVINCES = frozenset(
    {"AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "QC", "SK", "YT"}
)


class PartyAddressInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    line1: str | None = None
    city: str | None = None
    province: str | None = None
    postal_code: str | None = Field(default=None, alias="postalCode")

    @field_validator("province")
    @classmethod
    def validate_province(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.upper()
        if normalized not in CANADIAN_PROVINCES:
            raise ValueError(f"province must be a Canadian province/territory code, got {value!r}")
        return normalized


class PartyAddressResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    line1: str | None = None
    city: str | None = None
    province: str | None = None
    postalCode: str | None = None


class EmployerCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    address: PartyAddressInput | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip()


class EmployerUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    address: PartyAddressInput | None = None
    status: RecordStatus | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class EmployerResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    filingDisplayName: str
    address: PartyAddressResponse
    status: RecordStatus
    createdAt: datetime
    employeeCount: int | None = None
    nameLocked: bool = False


class EmployerListItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    filingDisplayName: str
    status: RecordStatus
    employeeCount: int


class EmployeeCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=1, max_length=255)
    sin: str
    address: PartyAddressInput | None = None
    employment_province: str | None = Field(default=None, alias="employmentProvince")

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("sin")
    @classmethod
    def validate_sin(cls, value: str) -> str:
        if not SIN_PATTERN.match(value):
            raise ValueError("SIN must match format 123-456-789")
        return value

    @field_validator("employment_province")
    @classmethod
    def validate_employment_province(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.upper()
        if normalized not in CANADIAN_PROVINCES:
            raise ValueError(f"employmentProvince must be a Canadian province/territory code, got {value!r}")
        return normalized


class EmployeeUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(default=None, min_length=1, max_length=255)
    address: PartyAddressInput | None = None
    employment_province: str | None = Field(default=None, alias="employmentProvince")
    status: RecordStatus | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @field_validator("employment_province")
    @classmethod
    def validate_employment_province(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.upper()
        if normalized not in CANADIAN_PROVINCES:
            raise ValueError(f"employmentProvince must be a Canadian province/territory code, got {value!r}")
        return normalized


class EmployeeResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    employerId: int
    employerName: str
    name: str
    sin: str
    address: PartyAddressResponse
    employmentProvince: str | None
    status: RecordStatus
    createdAt: datetime
