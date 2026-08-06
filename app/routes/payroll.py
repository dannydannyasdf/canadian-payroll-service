from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from app.models.payroll import PayrollPayload
from app.services.pdf_generator import render_pay_stub_pdf
from app.services.xml_validator import validate_payroll_xml

router = APIRouter()


def _pay_stub_response(payload: PayrollPayload) -> Response:
    pdf_bytes = render_pay_stub_pdf(payload.to_render_dict())

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="pay-stub.pdf"'},
    )


@router.post("/pay-stub")
def generate_pay_stub(payload: PayrollPayload) -> Response:
    """
    Accept a payroll JSON payload and return a print-ready pay stub PDF.

    This is the primary API for modern clients. See /docs for the schema.
    """
    return _pay_stub_response(payload)


@router.post("/pay-stub/xml")
async def generate_pay_stub_xml(request: Request) -> Response:
    """
    Accept a payroll XML payload and return a print-ready pay stub PDF.

    Legacy/alternate ingress path — validates against schemas/payroll.xsd.
    """
    xml_body = (await request.body()).decode("utf-8")

    if not xml_body.strip():
        return JSONResponse(status_code=400, content={"error": "Request body is empty."})

    try:
        payload = validate_payroll_xml(xml_body)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})

    return _pay_stub_response(payload)
