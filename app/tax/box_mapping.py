"""Map stored YTD totals to CRA T4 and Revenu Québec Relevé 1 box numbers.

These mappings are intentionally simplified for Phase 6 prep. Production slips
require an accountant review for insurable/pensionable earnings caps, Quebec
QPP/QPIP splits, and federal vs provincial income tax separation.
"""

from decimal import Decimal

from app.db_models import YtdRecord

T4_BOX_LABELS: dict[str, str] = {
    "14": "Employment income",
    "16": "Employee's CPP contributions",
    "18": "Employee's EI premiums",
    "22": "Income tax deducted",
    "24": "EI insurable earnings",
    "26": "CPP/QPP pensionable earnings",
}

RELEVE1_BOX_LABELS: dict[str, str] = {
    "A": "Revenus d'emploi et revenus assimilés",
    "B": "Cotisation au RRQ",
    "C": "Cotisation assurance emploi",
    "E": "Impôt du Québec retenu",
    "G": "Salaire admissible au RRQ",
    "I": "Salaire admissible à l'assurance emploi",
}

T4_PREP_DISCLAIMERS: tuple[str, ...] = (
    "Preview mapping only — not a filing-ready T4.",
    "Boxes 24/26 assume all gross pay is pensionable and insurable.",
    "Quebec employers must map CPP to QPP on Relevé 1, not T4 box 16.",
    "Income tax is not split into federal vs provincial amounts yet.",
)

RELEVE1_PREP_DISCLAIMERS: tuple[str, ...] = (
    "Preview mapping only — not a filing-ready Relevé 1.",
    "Box B uses the stored CPP/QPP total from pay stubs.",
    "Box E uses the full income tax total until provincial split exists.",
)


def _money(value: Decimal) -> str:
    return f"{value:.2f}"


def map_ytd_to_t4_boxes(ytd: YtdRecord) -> dict[str, str]:
    """Build CRA T4 box values from year-to-date totals."""
    return {
        "14": _money(ytd.gross_pay),
        "16": _money(ytd.cpp),
        "18": _money(ytd.ei),
        "22": _money(ytd.income_tax),
        "24": _money(ytd.gross_pay),
        "26": _money(ytd.gross_pay),
    }


def map_ytd_to_releve1_boxes(ytd: YtdRecord) -> dict[str, str]:
    """Build Revenu Québec Relevé 1 box values from year-to-date totals."""
    return {
        "A": _money(ytd.gross_pay),
        "B": _money(ytd.cpp),
        "C": _money(ytd.ei),
        "E": _money(ytd.income_tax),
        "G": _money(ytd.gross_pay),
        "I": _money(ytd.gross_pay),
    }
