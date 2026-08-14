import pytest

from app.services.releve1_official_form import official_releve1_form_available, render_releve1_official_form_pdf
from app.services.t4_official_form import official_t4_form_available, render_t4_official_form_pdf
from tests.conftest import make_releve1_slip, make_t4_slip


@pytest.mark.skipif(not official_t4_form_available(), reason="CRA T4 form asset not present")
def test_t4_official_pdf_overlay_returns_bytes() -> None:
    pdf_bytes = render_t4_official_form_pdf(make_t4_slip(employment_province="ON"))

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000


@pytest.mark.skipif(not official_releve1_form_available(), reason="Relevé 1 form asset not present")
def test_releve1_official_pdf_overlay_returns_bytes() -> None:
    pdf_bytes = render_releve1_official_form_pdf(make_releve1_slip(employment_province="QC"))

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000
