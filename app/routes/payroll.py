import base64

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import DuplicatePayPeriodError
from app.models.cumulative import PayStubResponse
from app.models.payroll import PayrollPayload
from app.services.billing_service import record_billing_event
from app.services.pdf_generator import render_pay_stub_pdf
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
