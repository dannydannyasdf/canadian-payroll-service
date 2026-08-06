import base64

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import DuplicatePayPeriodError
from app.models.cumulative import PayStubResponse
from app.models.employee import EmployeeSummary
from app.models.payroll import PayrollPayload
from app.services.billing_service import record_billing_event
from app.services.pdf_generator import render_pay_stub_archive_pdf, render_pay_stub_pdf
from app.services.stub_archive_service import (
    EmployeeNotFoundError,
    StubArchiveNotFoundError,
    build_stub_archive,
    list_employees,
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
def get_employees(db: Session = Depends(get_db)) -> list[EmployeeSummary]:
    """List employees (use the id to download a stub archive)."""
    return [EmployeeSummary(**row) for row in list_employees(db)]


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
