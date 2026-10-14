from decimal import Decimal

import pymupdf

from app.services.pdf_generator import render_pay_stub_pdf


def test_pay_stub_pdf_shows_comments() -> None:
    pdf_bytes = render_pay_stub_pdf(
        {
            "employer_name": "Acme Productions Ltd.",
            "employee_name": "Jane Freelancer",
            "employee_sin": "130-692-544",
            "period_start": "2026-01-01",
            "period_end": "2026-01-07",
            "pay_date": "2026-01-10",
            "tax_year": 2026,
            "employment_province": "ON",
            "gross_pay": Decimal("1000.00"),
            "cpp": Decimal("55.50"),
            "ei": Decimal("16.30"),
            "qpip": Decimal("0.00"),
            "income_tax": Decimal("81.61"),
            "provincial_income_tax": Decimal("0.00"),
            "net_pay": Decimal("846.59"),
            "comments": "Kit rental reimbursement included.",
            "ytd_gross_pay": Decimal("1000.00"),
            "ytd_cpp": Decimal("55.50"),
            "ytd_ei": Decimal("16.30"),
            "ytd_qpip": Decimal("0.00"),
            "ytd_income_tax": Decimal("81.61"),
            "ytd_provincial_income_tax": Decimal("0.00"),
            "ytd_net_pay": Decimal("846.59"),
        }
    )

    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    text = doc[0].get_text()
    doc.close()

    assert "Comments:" in text
    assert "Kit rental reimbursement included." in text


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
            "federal_income_tax": Decimal("895.98"),
            "provincial_income_tax": Decimal("1009.70"),
            "income_tax": Decimal("895.98"),
            "net_pay": Decimal("2702.82"),
            "ytd_gross_pay": Decimal("5000.00"),
            "ytd_cpp": Decimal("288.00"),
            "ytd_ei": Decimal("82.00"),
            "ytd_qpip": Decimal("21.50"),
            "ytd_federal_income_tax": Decimal("895.98"),
            "ytd_provincial_income_tax": Decimal("1009.70"),
            "ytd_income_tax": Decimal("895.98"),
            "ytd_net_pay": Decimal("2702.82"),
        }
    )

    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    text = doc[0].get_text()
    doc.close()

    assert "QPIP" in text
    assert "QPP" in text
    assert "Québec" in text
    assert "CPP" not in text
