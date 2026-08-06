import base64

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cumulative import PayStubResponse
from app.models.payroll import PayrollPayload
from app.exceptions import DuplicatePayPeriodError
from app.services.pdf_generator import render_pay_stub_pdf
from app.services.xml_validator import validate_payroll_xml
from app.services.ytd_service import accumulate_ytd

router = APIRouter()


def _pay_stub_response(payload: PayrollPayload, db: Session) -> PayStubResponse:
    try:
        cumulative = accumulate_ytd(db, payload)
    except DuplicatePayPeriodError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    render_data = {**payload.to_render_dict(), **cumulative.to_render_dict()}
    pdf_bytes = render_pay_stub_pdf(render_data)

    return PayStubResponse(
        cumulative=cumulative,
        payStubPdfBase64=base64.b64encode(pdf_bytes).decode("ascii"),
    )


@router.post("/pay-stub", response_model=PayStubResponse)
def generate_pay_stub(payload: PayrollPayload, db: Session = Depends(get_db)) -> PayStubResponse:
    """
    Accept a payroll JSON payload, update year-to-date totals, and return:
    - cumulative JSON (YTD totals for the tax year)
    - pay stub PDF (base64-encoded)
    """
    return _pay_stub_response(payload, db)


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

    return _pay_stub_response(payload, db)
