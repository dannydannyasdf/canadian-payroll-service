import base64

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import (
    DuplicatePayPeriodError,
    EmployerNotFoundError,
    InactiveEmployeeError,
    InactiveEmployerError,
    OnboardingEmployeeNotFoundError,
    PayrollIdentityMismatchError,
)
from app.models.cumulative import PayStubResponse
from app.models.employee import EmployeeSummary
from app.models.payroll import PayrollPayload
from app.models.tax_slip import Releve1SlipPreview, T4SlipPreview
from app.services.billing_service import record_billing_event
from app.services.pdf_generator import render_pay_stub_archive_pdf, render_pay_stub_pdf, render_releve1_pdf, render_t4_pdf
from app.services.stub_archive_service import (
    EmployeeNotFoundError,
    StubArchiveNotFoundError,
    build_stub_archive,
    list_employees,
)
from app.services.tax_slip_service import YtdNotFoundError, build_releve1_preview, build_t4_preview
from app.services.cra_efile_service import (
    CraFilingNotFoundError,
    build_cra_filing_xml,
    build_employee_t4_efile_xml,
    cra_schema_inventory,
)
from app.services.xml_validator import validate_payroll_xml
from app.services.ytd_service import accumulate_ytd

router = APIRouter()

# Kong key-auth passes the consumer username to the app on authenticated requests.
KONG_CONSUMER_HEADER = "x-consumer-username"


def _consumer_from_request(request: Request) -> str | None:
    return request.headers.get(KONG_CONSUMER_HEADER)


def _pay_stub_response(payload: PayrollPayload, db: Session, request: Request) -> PayStubResponse:
    try:
        cumulative = accumulate_ytd(db, payload)
    except DuplicatePayPeriodError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InactiveEmployerError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except InactiveEmployeeError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except EmployerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except OnboardingEmployeeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PayrollIdentityMismatchError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    record_billing_event(
        db,
        consumer_username=_consumer_from_request(request),
        gross_pay=payload.earnings.gross_pay,
    )

    render_data = {**payload.to_render_dict(), **cumulative.to_render_dict()}
    pdf_bytes = render_pay_stub_pdf(render_data)

    return PayStubResponse(
        cumulative=cumulative,
        payStubPdfBase64=base64.b64encode(pdf_bytes).decode("ascii"),
    )


@router.post("/pay-stub", response_model=PayStubResponse)
def generate_pay_stub(
    payload: PayrollPayload,
    request: Request,
    db: Session = Depends(get_db),
) -> PayStubResponse:
    """
    Accept a payroll JSON payload, update year-to-date totals, and return:
    - cumulative JSON (YTD totals for the tax year)
    - pay stub PDF (base64-encoded)

    Optional employer.id and employee.id link to registered onboarding records.
    Inactive employers/employees are rejected with 403.

    Requires API key header when accessed through Kong: `apikey: <your-key>`
    """
    return _pay_stub_response(payload, db, request)


@router.post("/pay-stub/xml", response_model=PayStubResponse)
async def generate_pay_stub_xml(request: Request, db: Session = Depends(get_db)) -> PayStubResponse:
    """
    Accept a payroll XML payload, update year-to-date totals, and return
    the same JSON response shape as the primary JSON endpoint.
    """
    xml_body = (await request.body()).decode("utf-8")

    if not xml_body.strip():
        raise HTTPException(status_code=400, detail="Request body is empty.")

    try:
        payload = validate_payroll_xml(xml_body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _pay_stub_response(payload, db, request)


@router.get("/employees", response_model=list[EmployeeSummary])
def get_employees(
    employer_id: int | None = Query(default=None, alias="employerId"),
    db: Session = Depends(get_db),
) -> list[EmployeeSummary]:
    """List employees (optionally filter by employer id)."""
    return [EmployeeSummary(**row) for row in list_employees(db, employer_id=employer_id)]


@router.get("/employees/{employee_id}/stubs")
def download_stub_archive(
    employee_id: int,
    tax_year: int = Query(alias="taxYear", ge=2000, le=2100),
    db: Session = Depends(get_db),
) -> Response:
    """
    Download all pay stubs for an employee and tax year as one multi-page PDF.

    Requires API key when accessed through Kong: `apikey: <your-key>`
    """
    try:
        stubs = build_stub_archive(db, employee_id, tax_year)
    except EmployeeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except StubArchiveNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    pdf_bytes = render_pay_stub_archive_pdf(stubs)
    filename = f"pay-stubs-{employee_id}-{tax_year}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.get("/employees/{employee_id}/t4/xml")
def download_t4_efile_xml(
    employee_id: int,
    tax_year: int = Query(alias="taxYear", ge=2000, le=2100),
    official: bool | None = Query(default=None, description="Use official CRA schema when true"),
    db: Session = Depends(get_db),
) -> Response:
    """Download a CRA T4 e-file XML bundle for one employee."""
    try:
        xml_text = build_employee_t4_efile_xml(db, employee_id, tax_year, official=official)
    except EmployeeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except YtdNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    suffix = "official" if (official or (official is None and cra_schema_inventory()["officialT4Loadable"])) else "preview"
    filename = f"cra-t4-{employee_id}-{tax_year}-{suffix}.xml"
    return Response(
        content=xml_text,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/tax-filing/cra/schema-status")
def cra_schema_status() -> dict[str, object]:
    """Show which CRA XSD files are present and which schema validates exports today."""
    return cra_schema_inventory()


@router.get("/tax-filing/cra")
def download_cra_filing_xml(
    tax_year: int = Query(alias="taxYear", ge=2000, le=2100),
    official: bool | None = Query(default=None, description="Use official CRA schema when true"),
    db: Session = Depends(get_db),
) -> Response:
    """Download a CRA T4 e-file XML bundle for all employees in a tax year."""
    try:
        xml_text = build_cra_filing_xml(db, tax_year, official=official)
    except CraFilingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    suffix = "official" if (official or (official is None and cra_schema_inventory()["officialT4Loadable"])) else "preview"
    filename = f"cra-t4-filing-{tax_year}-{suffix}.xml"
    return Response(
        content=xml_text,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/employees/{employee_id}/t4/pdf")
def download_t4_pdf(
    employee_id: int,
    tax_year: int = Query(alias="taxYear", ge=2000, le=2100),
    db: Session = Depends(get_db),
) -> Response:
    """
    Download a T4 slip PDF mapped from stored YTD totals.

    Preview layout only — not a CRA-official form. Requires API key through Kong.
    """
    try:
        slip = build_t4_preview(db, employee_id, tax_year)
    except EmployeeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except YtdNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    pdf_bytes = render_t4_pdf(slip)
    filename = f"t4-{employee_id}-{tax_year}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.get("/employees/{employee_id}/t4", response_model=T4SlipPreview)
def preview_t4_slip(
    employee_id: int,
    tax_year: int = Query(alias="taxYear", ge=2000, le=2100),
    db: Session = Depends(get_db),
) -> T4SlipPreview:
    """Preview CRA T4 box values mapped from stored YTD totals (JSON)."""
    try:
        return build_t4_preview(db, employee_id, tax_year)
    except EmployeeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except YtdNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/employees/{employee_id}/releve1/pdf")
def download_releve1_pdf(
    employee_id: int,
    tax_year: int = Query(alias="taxYear", ge=2000, le=2100),
    db: Session = Depends(get_db),
) -> Response:
    """
    Download a Relevé 1 slip PDF mapped from stored YTD totals.

    Preview layout only — not an Revenu Québec-official form. Requires API key through Kong.
    """
    try:
        slip = build_releve1_preview(db, employee_id, tax_year)
    except EmployeeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except YtdNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    pdf_bytes = render_releve1_pdf(slip)
    filename = f"releve1-{employee_id}-{tax_year}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.get("/employees/{employee_id}/releve1", response_model=Releve1SlipPreview)
def preview_releve1_slip(
    employee_id: int,
    tax_year: int = Query(alias="taxYear", ge=2000, le=2100),
    db: Session = Depends(get_db),
) -> Releve1SlipPreview:
    """Preview Revenu Québec Relevé 1 box values mapped from stored YTD totals (JSON)."""
    try:
        return build_releve1_preview(db, employee_id, tax_year)
    except EmployeeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except YtdNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
