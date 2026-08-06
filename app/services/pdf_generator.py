import os
from decimal import Decimal
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

APP_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = APP_DIR.parent
TEMPLATES_DIR = APP_DIR / "templates"
DEFAULT_CLIENT_LOGO = APP_DIR / "assets" / "company_logo.jpg"
DEFAULT_PROVIDER_LOGO = PROJECT_DIR / "Images" / "Gamma_heads_Logo_Black.jpg"
CLIENT_LOGO_PATH = Path(os.environ.get("PAYROLL_CLIENT_LOGO_PATH", DEFAULT_CLIENT_LOGO))
PROVIDER_LOGO_PATH = Path(os.environ.get("PAYROLL_PROVIDER_LOGO_PATH", DEFAULT_PROVIDER_LOGO))
PROVIDER_NAME = os.environ.get("PAYROLL_PROVIDER_NAME", "Gamma Personnel Inc.")
PROVIDER_CONTACT_NAME = os.environ.get("PAYROLL_PROVIDER_CONTACT_NAME", "Danny Majerovich")
PROVIDER_ADDRESS_LINES = [
    "B301-2001 University, C.P. 71316",
    "Montréal (Québec) H3A 3S9 CANADA",
]


def _logo_uri(path: Path) -> str | None:
    return path.resolve().as_uri() if path.exists() else None


def _format_money(value: Decimal) -> str:
    return f"${value:,.2f}"


def _template_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters["money"] = _format_money
    return env


def _brand_context() -> dict:
    return {
        "client_logo_url": _logo_uri(CLIENT_LOGO_PATH),
        "provider_logo_url": _logo_uri(PROVIDER_LOGO_PATH),
        "provider_name": PROVIDER_NAME,
        "provider_contact_name": PROVIDER_CONTACT_NAME,
        "provider_address_lines": PROVIDER_ADDRESS_LINES,
    }


def render_pay_stub_pdf(payroll_data: dict) -> bytes:
    template = _template_env().get_template("pay_stub.html")
    html = template.render(**_brand_context(), **payroll_data)
    return HTML(string=html, base_url=str(TEMPLATES_DIR)).write_pdf()


def render_pay_stub_archive_pdf(stubs: list[dict]) -> bytes:
    template = _template_env().get_template("pay_stub_archive.html")
    html = template.render(stubs=stubs, tax_year=stubs[-1]["tax_year"], **_brand_context())
    return HTML(string=html, base_url=str(TEMPLATES_DIR)).write_pdf()
