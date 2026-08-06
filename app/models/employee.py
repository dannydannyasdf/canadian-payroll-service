from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class EmployeeSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    sin: str
    employer_name: str = Field(alias="employerName")
