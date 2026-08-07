"""Fill the official CRA T4 PDF blank (t4-25e.pdf) by overlaying field values."""

from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path

import pymupdf

from app.models.tax_slip import T4SlipPreview, TaxPartyAddress

APP_DIR = Path(__file__).resolve().parents[1]
DEFAULT_FORM_PATH = APP_DIR / "assets" / "forms" / "t4-25e.pdf"
PROJECT_FORM_PATH = APP_DIR.parent / "t4-25e.pdf"
T4_FORM_PATH = Path(os.environ.get("PAYROLL_T4_FORM_PATH", DEFAULT_FORM_PATH))
if not T4_FORM_PATH.exists() and PROJECT_FORM_PATH.exists():
    T4_FORM_PATH = PROJECT_FORM_PATH

from app.services.provider_config import DEFAULT_EMPLOYMENT_PROVINCE, PAYROLL_ACCOUNT_DISPLAY

# Measured from t4-25e.pdf (letter, 612x792). Each entry is (x0, y0, x1, y1).
TOP_COPY_FIELDS: dict[str, tuple[float, float, float, float]] = {
    "employer_name": (49.0, 31.0, 249.8, 91.4),
    "year": (293.4, 36.0, 351.0, 54.0),
    "box_54": (57.6, 106.8, 255.6, 123.7),
    "box_12": (57.6, 145.4, 180.0, 163.4),
    "box_10": (289.8, 121.6, 318.6, 139.6),
    "box_14": (352.4, 74.2, 434.1, 89.3),
    "box_22": (474.8, 74.2, 567.4, 89.4),
    "box_16": (352.4, 108.0, 434.2, 123.1),
    "box_17": (485.5, 108.2, 567.3, 123.3),
    "box_24": (352.6, 177.9, 434.3, 193.0),
    "box_26": (485.6, 177.6, 567.4, 192.7),
    "box_18": (352.4, 209.5, 434.2, 224.6),
    "employee_last": (59.0, 206.2, 195.8, 221.4),
    "employee_first": (198.7, 206.2, 292.3, 221.4),
    "employee_address": (47.5, 243.4, 325.1, 305.4),
}

COPY_Y_OFFSET = 387.7


def official_t4_form_available() -> bool:
    return T4_FORM_PATH.is_file()


def _split_employee_name(full_name: str) -> tuple[str, str]:
    parts = full_name.strip().split()
    if len(parts) == 1:
        return parts[0].upper(), parts[0]
    return parts[-1].upper(), " ".join(parts[:-1])


def _normalize_sin(sin: str) -> str:
    return "".join(ch for ch in sin if ch.isdigit())


def _amount(value: str) -> str:
    return f"{Decimal(value):.2f}"


def _payroll_account(slip: T4SlipPreview) -> str:
    return slip.employer.payrollAccountNumber or PAYROLL_ACCOUNT_DISPLAY


def _employment_province(slip: T4SlipPreview) -> str:
    province = slip.employee.address.province or DEFAULT_EMPLOYMENT_PROVINCE
    return province.upper()


def _format_address(address: TaxPartyAddress) -> str:
    lines: list[str] = []
    if address.line1:
        lines.append(address.line1)
    city_parts = [part for part in (address.city, address.province, address.postalCode) if part]
    if city_parts:
        lines.append(", ".join(city_parts))
    return "\n".join(lines)


def _rect(field: tuple[float, float, float, float], y_offset: float = 0.0) -> pymupdf.Rect:
    x0, y0, x1, y1 = field
    return pymupdf.Rect(x0, y0 + y_offset, x1, y1 + y_offset)


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


def _fill_copy(page: pymupdf.Page, slip: T4SlipPreview, y_offset: float = 0.0) -> None:
    surname, given_name = _split_employee_name(slip.employee.name)
    province = _employment_province(slip)
    boxes = slip.boxes

    _write_textbox(page, _rect(TOP_COPY_FIELDS["employer_name"], y_offset), slip.employer.name, fontsize=10)
    _write_textbox(
        page,
        _rect(TOP_COPY_FIELDS["year"], y_offset),
        str(slip.taxYear),
        align=pymupdf.TEXT_ALIGN_CENTER,
    )
    _write_textbox(page, _rect(TOP_COPY_FIELDS["box_54"], y_offset), _payroll_account(slip), fontsize=10)
    _write_textbox(page, _rect(TOP_COPY_FIELDS["box_12"], y_offset), _normalize_sin(slip.employee.sin))
    _write_textbox(
        page,
        _rect(TOP_COPY_FIELDS["box_10"], y_offset),
        province,
        align=pymupdf.TEXT_ALIGN_CENTER,
    )

    _write_textbox(
        page,
        _rect(TOP_COPY_FIELDS["box_14"], y_offset),
        _amount(boxes["14"]),
        align=pymupdf.TEXT_ALIGN_RIGHT,
    )
    _write_textbox(
        page,
        _rect(TOP_COPY_FIELDS["box_22"], y_offset),
        _amount(boxes["22"]),
        align=pymupdf.TEXT_ALIGN_RIGHT,
    )
    _write_textbox(
        page,
        _rect(TOP_COPY_FIELDS["box_24"], y_offset),
        _amount(boxes["24"]),
        align=pymupdf.TEXT_ALIGN_RIGHT,
    )
    _write_textbox(
        page,
        _rect(TOP_COPY_FIELDS["box_26"], y_offset),
        _amount(boxes["26"]),
        align=pymupdf.TEXT_ALIGN_RIGHT,
    )
    _write_textbox(
        page,
        _rect(TOP_COPY_FIELDS["box_18"], y_offset),
        _amount(boxes["18"]),
        align=pymupdf.TEXT_ALIGN_RIGHT,
    )

    pension_box = "box_17" if province == "QC" else "box_16"
    _write_textbox(
        page,
        _rect(TOP_COPY_FIELDS[pension_box], y_offset),
        _amount(boxes["16"]),
        align=pymupdf.TEXT_ALIGN_RIGHT,
    )

    _write_textbox(page, _rect(TOP_COPY_FIELDS["employee_last"], y_offset), surname, fontsize=9)
    _write_textbox(page, _rect(TOP_COPY_FIELDS["employee_first"], y_offset), given_name, fontsize=9)

    address = _format_address(slip.employee.address)
    if address:
        _write_textbox(page, _rect(TOP_COPY_FIELDS["employee_address"], y_offset), address, fontsize=8)


def render_t4_official_form_pdf(slip: T4SlipPreview) -> bytes:
    if not official_t4_form_available():
        raise FileNotFoundError(f"Official T4 form not found at {T4_FORM_PATH}")

    doc = pymupdf.open(T4_FORM_PATH)
    page = doc[0]
    _fill_copy(page, slip, y_offset=0.0)
    _fill_copy(page, slip, y_offset=COPY_Y_OFFSET)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes
