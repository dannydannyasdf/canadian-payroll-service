from decimal import Decimal

import pymupdf

from app.services.pdf_generator import render_pay_stub_pdf


def test_pay_stub_pdf_shows_qpip_for_qc_employment() -> None:
    pdf_bytes = render_pay_stub_pdf(
        {
            "employer_name": "Acme Productions Ltd.",
            "employee_name": "Jane Freelancer",
            "employee_sin": "130-692-544",
            "period_start": "2026-01-01",
            "period_end": "2026-01-07",
            "pay_date": "2026-01-10",
            "tax_year": 2026,
            "employment_province": "QC",
            "gross_pay": Decimal("5000.00"),
            "cpp": Decimal("288.00"),
            "ei": Decimal("82.00"),
            "qpip": Decimal("21.50"),
            "income_tax": Decimal("1100.00"),
            "net_pay": Decimal("3508.50"),
            "ytd_gross_pay": Decimal("5000.00"),
            "ytd_cpp": Decimal("288.00"),
            "ytd_ei": Decimal("82.00"),
            "ytd_qpip": Decimal("21.50"),
            "ytd_income_tax": Decimal("1100.00"),
            "ytd_net_pay": Decimal("3508.50"),
        }
    )

    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    text = doc[0].get_text()
    doc.close()

    assert "QPIP" in text
    assert "QPP" in text
    assert "CPP" not in text
