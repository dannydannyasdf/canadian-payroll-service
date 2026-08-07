from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import (
    DuplicateEmployeeError,
    DuplicateEmployerError,
    EmployerNameLockedError,
    EmployerNotFoundError,
    InactiveEmployerError,
    OnboardingEmployeeNotFoundError,
)
from app.models.onboarding import (
    EmployeeCreateRequest,
    EmployeeResponse,
    EmployeeUpdateRequest,
    EmployerCreateRequest,
    EmployerListItem,
    EmployerResponse,
    EmployerUpdateRequest,
)
from app.services.onboarding_service import (
    create_employee,
    create_employer,
    get_employee,
    get_employer,
    list_employees_for_employer,
    list_employers,
    update_employee,
    update_employer,
)

router = APIRouter()


@router.post("/employers", response_model=EmployerResponse, status_code=status.HTTP_201_CREATED)
def register_employer(
    payload: EmployerCreateRequest,
    db: Session = Depends(get_db),
) -> EmployerResponse:
    """Register a new client employer before running payroll."""
    try:
        return create_employer(db, payload)
    except DuplicateEmployerError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/employers", response_model=list[EmployerListItem])
def get_employers(
    name: str | None = Query(default=None, description="Filter by employer name substring"),
    status_filter: Literal["active", "inactive", "all"] = Query(
        default="active",
        alias="status",
        description="Filter by status (use all to include inactive employers)",
    ),
    db: Session = Depends(get_db),
) -> list[EmployerListItem]:
    """List registered client employers."""
    status = None if status_filter == "all" else status_filter
    return list_employers(db, name=name, status=status)


@router.get("/employers/{employer_id}", response_model=EmployerResponse)
def get_employer_by_id(employer_id: int, db: Session = Depends(get_db)) -> EmployerResponse:
    try:
        return get_employer(db, employer_id)
    except EmployerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/employers/{employer_id}", response_model=EmployerResponse)
def patch_employer(
    employer_id: int,
    payload: EmployerUpdateRequest,
    db: Session = Depends(get_db),
) -> EmployerResponse:
    try:
        return update_employer(db, employer_id, payload)
    except EmployerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DuplicateEmployerError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except EmployerNameLockedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post(
    "/employers/{employer_id}/employees",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_employee(
    employer_id: int,
    payload: EmployeeCreateRequest,
    db: Session = Depends(get_db),
) -> EmployeeResponse:
    """Register an employee under a client employer."""
    try:
        return create_employee(db, employer_id, payload)
    except EmployerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InactiveEmployerError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except DuplicateEmployeeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/employers/{employer_id}/employees", response_model=list[EmployeeResponse])
def get_employers_employees(employer_id: int, db: Session = Depends(get_db)) -> list[EmployeeResponse]:
    try:
        return list_employees_for_employer(db, employer_id)
    except EmployerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/employers/{employer_id}/employees/{employee_id}", response_model=EmployeeResponse)
def get_employer_employee(
    employer_id: int,
    employee_id: int,
    db: Session = Depends(get_db),
) -> EmployeeResponse:
    try:
        return get_employee(db, employer_id, employee_id)
    except EmployerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except OnboardingEmployeeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/employers/{employer_id}/employees/{employee_id}", response_model=EmployeeResponse)
def patch_employer_employee(
    employer_id: int,
    employee_id: int,
    payload: EmployeeUpdateRequest,
    db: Session = Depends(get_db),
) -> EmployeeResponse:
    try:
        return update_employee(db, employer_id, employee_id, payload)
    except EmployerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except OnboardingEmployeeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
