"""Fill the official Revenu Québec RL-1 PDF blank by overlaying field values."""

from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path

import pymupdf

from app.models.tax_slip import Releve1SlipPreview, TaxPartyAddress
from app.services.provider_config import RQ_NEQ

APP_DIR = Path(__file__).resolve().parents[1]
DEFAULT_FORM_PATH = APP_DIR / "assets" / "forms" / "releve1-2026-10.pdf"
PROJECT_FORM_PATH = APP_DIR.parent / "RL-1(2026-10)_Logiciel_copie2_projet.pdf"
RELEVE1_FORM_PATH = Path(os.environ.get("PAYROLL_RELEVE1_FORM_PATH", DEFAULT_FORM_PATH))
if not RELEVE1_FORM_PATH.exists() and PROJECT_FORM_PATH.exists():
    RELEVE1_FORM_PATH = PROJECT_FORM_PATH

# Measured from RL-1(2026-10)_Logiciel_copie2_projet.pdf (letter, 612x792).
FIELDS: dict[str, tuple[float, float, float, float]] = {
    "year": (325.3, 46.0, 361.0, 55.7),
    "box_A": (67.0, 79.0, 96.0, 102.0),
    "box_B": (162.0, 79.0, 191.0, 102.0),
    "box_C": (352.0, 79.0, 381.0, 102.0),
    "box_E": (542.0, 79.0, 571.0, 102.0),
    "box_G": (162.0, 103.0, 191.0, 126.0),
    "box_I": (352.0, 103.0, 381.0, 126.0),
    "sin_1": (358.0, 604.0, 391.0, 621.0),
    "sin_2": (393.0, 604.0, 427.0, 621.0),
    "sin_3": (429.0, 604.0, 470.0, 621.0),
    "employer": (358.0, 640.0, 570.0, 705.0),
    "employee": (26.0, 656.0, 312.0, 712.0),
}


def official_releve1_form_available() -> bool:
    return RELEVE1_FORM_PATH.is_file()


def _split_employee_name(full_name: str) -> tuple[str, str]:
    parts = full_name.strip().split()
    if len(parts) == 1:
        return parts[0].upper(), parts[0]
    return parts[-1].upper(), " ".join(parts[:-1])


def _normalize_sin(sin: str) -> str:
    return "".join(ch for ch in sin if ch.isdigit())


def _sin_segments(sin: str) -> tuple[str, str, str]:
    digits = _normalize_sin(sin)
    return digits[:3], digits[3:6], digits[6:9]


def _amount(value: str) -> str:
    quantized = Decimal(value).quantize(Decimal("0.01"))
    text = f"{quantized:,.2f}"
    return text.replace(",", " ")


def _format_address(address: TaxPartyAddress) -> list[str]:
    lines: list[str] = []
    if address.line1:
        lines.append(address.line1)
    city_parts = [part for part in (address.city, address.province, address.postalCode) if part]
    if city_parts:
        lines.append(", ".join(city_parts))
    return lines


def _rect(field: tuple[float, float, float, float]) -> pymupdf.Rect:
    x0, y0, x1, y1 = field
    return pymupdf.Rect(x0, y0, x1, y1)


def _write_textbox(
    page: pymupdf.Page,
    rect: pymupdf.Rect,
    text: str,
    *,
    fontsize: float = 9,
    align: int = pymupdf.TEXT_ALIGN_LEFT,
) -> None:
    if not text.strip():
        return
    overflow = page.insert_textbox(
        rect,
        text,
        fontsize=fontsize,
        fontname="helv",
        color=(0, 0, 0),
        align=align,
    )
    if overflow >= 0:
        return

    text_width = pymupdf.get_text_length(text, fontname="helv", fontsize=fontsize)
    if align == pymupdf.TEXT_ALIGN_RIGHT:
        x = rect.x1 - text_width
    elif align == pymupdf.TEXT_ALIGN_CENTER:
        x = rect.x0 + (rect.width - text_width) / 2
    else:
        x = rect.x0
    y = rect.y0 + fontsize * 0.85
    page.insert_text((x, y), text, fontsize=fontsize, fontname="helv", color=(0, 0, 0))


def _employer_block(slip: Releve1SlipPreview) -> str:
    lines = [slip.employer.name]
    if RQ_NEQ:
        lines.append(f"NEQ {RQ_NEQ}")
    lines.extend(_format_address(slip.employer.address))
    return "\n".join(lines)


def _fill_form(page: pymupdf.Page, slip: Releve1SlipPreview) -> None:
    surname, given_name = _split_employee_name(slip.employee.name)
    sin1, sin2, sin3 = _sin_segments(slip.employee.sin)
    boxes = slip.boxes

    _write_textbox(
        page,
        _rect(FIELDS["year"]),
        str(slip.taxYear),
        fontsize=10,
        align=pymupdf.TEXT_ALIGN_CENTER,
    )

    for box_key, field_key in (
        ("A", "box_A"),
        ("B", "box_B"),
        ("C", "box_C"),
        ("E", "box_E"),
        ("G", "box_G"),
        ("I", "box_I"),
    ):
        _write_textbox(
            page,
            _rect(FIELDS[field_key]),
            _amount(boxes[box_key]),
            fontsize=8,
            align=pymupdf.TEXT_ALIGN_RIGHT,
        )

    _write_textbox(page, _rect(FIELDS["sin_1"]), sin1, fontsize=9, align=pymupdf.TEXT_ALIGN_CENTER)
    _write_textbox(page, _rect(FIELDS["sin_2"]), sin2, fontsize=9, align=pymupdf.TEXT_ALIGN_CENTER)
    _write_textbox(page, _rect(FIELDS["sin_3"]), sin3, fontsize=9, align=pymupdf.TEXT_ALIGN_CENTER)

    _write_textbox(page, _rect(FIELDS["employer"]), _employer_block(slip), fontsize=8)

    employee_lines = [f"{surname}, {given_name}"]
    employee_lines.extend(_format_address(slip.employee.address))
    _write_textbox(page, _rect(FIELDS["employee"]), "\n".join(employee_lines), fontsize=8)


def render_releve1_official_form_pdf(slip: Releve1SlipPreview) -> bytes:
    if not official_releve1_form_available():
        raise FileNotFoundError(f"Official Relevé 1 form not found at {RELEVE1_FORM_PATH}")

    doc = pymupdf.open(RELEVE1_FORM_PATH)
    page = doc[0]
    _fill_form(page, slip)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes
