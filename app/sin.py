import re

SIN_INPUT_PATTERN = re.compile(r"^(?!0|8)\d{3}[- ]?\d{3}[- ]?\d{3}$")


def validate_canadian_sin(sin_input: str) -> bool:
    """
    Validate a Canadian Social Insurance Number (SIN).

    Checks format (must not start with 0 or 8; optional spaces or hyphens)
    and the Luhn checksum.
    """
    if not SIN_INPUT_PATTERN.match(sin_input):
        return False

    raw_sin = re.sub(r"[- ]", "", sin_input)
    total_sum = 0
    for index, char in enumerate(raw_sin):
        digit = int(char)
        if index % 2 != 0:
            digit *= 2
        total_sum += (digit // 10) + (digit % 10)

    return total_sum % 10 == 0


def normalize_sin(sin_input: str) -> str:
    """Return a validated SIN formatted as XXX-XXX-XXX."""
    if not validate_canadian_sin(sin_input):
        raise ValueError(
            "SIN must be nine digits in the form 123-456-789, "
            "must not start with 0 or 8, and must pass checksum validation"
        )
    digits = re.sub(r"[- ]", "", sin_input)
    return f"{digits[:3]}-{digits[3:6]}-{digits[6:9]}"
