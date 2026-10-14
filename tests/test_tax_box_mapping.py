"""Tests for federal vs provincial income tax box mapping."""

from decimal import Decimal

from app.db_models import YtdRecord
from app.tax.box_mapping import map_ytd_to_releve1_boxes, map_ytd_to_t4_boxes


def test_t4_box_22_and_releve1_box_e_use_tax_split() -> None:
    ytd = YtdRecord(
        employee_id=1,
        tax_year=2026,
        gross_pay=Decimal("10000.00"),
        cpp=Decimal("576.00"),
        ei=Decimal("164.00"),
        qpip=Decimal("43.00"),
        federal_income_tax=Decimal("2260.58"),
        provincial_income_tax=Decimal("2285.42"),
        income_tax=Decimal("4546.00"),
        net_pay=Decimal("4671.00"),
    )

    t4_boxes = map_ytd_to_t4_boxes(ytd)
    releve_boxes = map_ytd_to_releve1_boxes(ytd)

    assert t4_boxes["22"] == "2260.58"
    assert releve_boxes["E"] == "2285.42"
    assert t4_boxes["22"] != releve_boxes["E"]
