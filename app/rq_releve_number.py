"""Revenu Québec RL-slip sequential number helpers (IN-800-V modulus-7 check digit)."""

from __future__ import annotations


def mod7_check_digit(base8: int) -> int:
    """Compute the 9th check digit for an 8-digit RL-slip sequence base (IN-800 Schedule 1)."""
    if base8 < 0 or base8 > 99_999_999:
        raise ValueError("RL-slip sequence base must be an 8-digit number.")

    quotient = base8 / 7
    truncated_quotient = int(quotient * 100) / 100
    fractional = truncated_quotient - int(truncated_quotient)
    scaled = fractional * 7
    check = int(round(scaled))

    if quotient == int(quotient):
        return 0
    return check


def format_releve_number(base8: int) -> str:
    """Return a 9-digit NoReleve value from an 8-digit sequence base."""
    check = mod7_check_digit(base8)
    return f"{base8:08d}{check}"
