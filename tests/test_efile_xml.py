import pytest

from app.services.cra_efile_service import (
    build_and_validate_cra_submission_xml,
    official_schema_available as cra_official_available,
)
from app.services.rq_efile_service import (
    build_and_validate_rq_submission_xml,
    build_employee_releve1_efile_xml,
    official_schema_available as rq_official_available,
)
from tests.conftest import make_releve1_slip, make_t4_slip, seed_employee_with_ytd


@pytest.mark.skipif(not cra_official_available(), reason="CRA official XSD package not present")
def test_cra_official_xml_validates() -> None:
    xml_text = build_and_validate_cra_submission_xml([make_t4_slip()], 2026, official=True)
    assert "<Submission>" in xml_text
    assert "<T4>" in xml_text
    assert "2026" in xml_text


@pytest.mark.skipif(not rq_official_available(), reason="RQ official XSD package not present")
def test_rq_official_xml_validates(db_session) -> None:
    employee = seed_employee_with_ytd(db_session, employment_province="QC")
    xml_text = build_employee_releve1_efile_xml(db_session, employee.id, 2026, official=True)
    assert "Transmission" in xml_text
    assert "Groupe01" in xml_text
    assert "A_RevenuEmploi" in xml_text
    assert "10000,00" in xml_text
    assert "<NoId>1003372801</NoId>" in xml_text
    assert "<NEQ>1142427765</NEQ>" in xml_text


def test_cra_preview_xml_validates() -> None:
    xml_text = build_and_validate_cra_submission_xml([make_t4_slip()], 2026, official=False)
    assert "Submission" in xml_text
    assert "preview" in xml_text


def test_rq_preview_xml_validates() -> None:
    xml_text = build_and_validate_rq_submission_xml([make_releve1_slip()], 2026, official=False)
    assert "Submission" in xml_text
    assert "Releve1Slip" in xml_text
