from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from app.services.pdf_generator import render_pay_stub_pdf
from app.services.xml_validator import validate_payroll_xml

router = APIRouter()


@router.post("/pay-stub")
async def generate_pay_stub(request: Request) -> Response:
    """
    Accept a payroll XML payload and return a print-ready pay stub PDF.

    Phase 1: validate XML against payroll.xsd, then render PDF with WeasyPrint.
    """
    xml_body = (await request.body()).decode("utf-8")

    if not xml_body.strip():
        return JSONResponse(status_code=400, content={"error": "Request body is empty."})

    try:
        payroll_data = validate_payroll_xml(xml_body)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})

    pdf_bytes = render_pay_stub_pdf(payroll_data)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="pay-stub.pdf"'},
    )
