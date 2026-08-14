from app.demo_defaults import (
    DEMO_EMPLOYMENT_PROVINCE,
    DEMO_SAMPLE_SIN,
    default_employment_province_for_sin,
    is_demo_sample_sin,
)
from app.sin import normalize_sin, validate_canadian_sin


def test_validate_canadian_sin_accepts_sample_sin() -> None:
    assert validate_canadian_sin(DEMO_SAMPLE_SIN)


def test_normalize_sin_formats_sample_sin() -> None:
    assert normalize_sin("130692544") == DEMO_SAMPLE_SIN


def test_validate_canadian_sin_rejects_leading_zero() -> None:
    assert not validate_canadian_sin("030-692-544")


def test_is_demo_sample_sin() -> None:
    assert is_demo_sample_sin(DEMO_SAMPLE_SIN)
    assert is_demo_sample_sin("130692544")
    assert not is_demo_sample_sin("123-456-782")


def test_default_employment_province_for_demo_sin() -> None:
    assert default_employment_province_for_sin(DEMO_SAMPLE_SIN) == DEMO_EMPLOYMENT_PROVINCE
    assert default_employment_province_for_sin("123-456-782") is None
