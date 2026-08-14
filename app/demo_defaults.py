"""Defaults for demo and sample payroll data."""

from __future__ import annotations

from app.sin import normalize_sin

DEMO_SAMPLE_SIN = "130-692-544"
DEMO_EMPLOYMENT_PROVINCE = "QC"


def is_demo_sample_sin(sin: str) -> bool:
    try:
        return normalize_sin(sin) == DEMO_SAMPLE_SIN
    except ValueError:
        return False


def default_employment_province_for_sin(sin: str) -> str | None:
    if is_demo_sample_sin(sin):
        return DEMO_EMPLOYMENT_PROVINCE
    return None
