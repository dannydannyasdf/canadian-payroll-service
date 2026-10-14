"""Gamma Personnel provider settings for proxy payroll filing."""

from __future__ import annotations

import os
import re

from app.models.tax_slip import T4EmployerSummary, TaxPartyAddress

PROVIDER_NAME = os.environ.get("PAYROLL_PROVIDER_NAME", "Gamma Personnel Inc.")
PROVIDER_CONTACT_NAME = os.environ.get("PAYROLL_PROVIDER_CONTACT_NAME", "Danny Majerovich")
PROVIDER_ADDRESS_LINE1 = os.environ.get(
    "PAYROLL_PROVIDER_ADDRESS_LINE1",
    "B301-2001 University, C.P. 71316",
)
PROVIDER_CITY = os.environ.get("PAYROLL_PROVIDER_CITY", "Montréal")
PROVIDER_PROVINCE = os.environ.get("PAYROLL_PROVIDER_PROVINCE", "QC")
PROVIDER_POSTAL_CODE = os.environ.get("PAYROLL_PROVIDER_POSTAL_CODE", "H3A 3S9")
PROVIDER_ADDRESS_LINES = [
    PROVIDER_ADDRESS_LINE1,
    f"{PROVIDER_CITY} ({PROVIDER_PROVINCE}) {PROVIDER_POSTAL_CODE} CANADA",
]

PAYROLL_ACCOUNT_DISPLAY = os.environ.get("PAYROLL_CRA_PAYROLL_ACCOUNT", "10668 8385 RP0001")
DEFAULT_EMPLOYMENT_PROVINCE = os.environ.get("PAYROLL_DEFAULT_EMPLOYMENT_PROVINCE", "ON")

CONTACT_AREA = os.environ.get("PAYROLL_CRA_CONTACT_AREA", "514")
CONTACT_PHONE = os.environ.get("PAYROLL_CRA_CONTACT_PHONE", "392-0015")
CONTACT_EMAIL = os.environ.get("PAYROLL_CRA_CONTACT_EMAIL", "dannym.asdf@gmail.com")


def normalize_payroll_account(raw: str) -> str:
    return raw.replace(" ", "")


def bn9_from_payroll_account(payroll_account: str) -> str:
    match = re.search(r"(\d{9})", payroll_account.replace(" ", ""))
    return match.group(1) if match else ""


PAYROLL_ACCOUNT_EFILE = normalize_payroll_account(PAYROLL_ACCOUNT_DISPLAY)
PROVIDER_BUSINESS_NUMBER = os.environ.get(
    "PAYROLL_PROVIDER_BUSINESS_NUMBER",
    bn9_from_payroll_account(PAYROLL_ACCOUNT_DISPLAY) or "106688385",
)
TRANSMITTER_BN9 = os.environ.get(
    "PAYROLL_CRA_TRANSMITTER_BN9",
    bn9_from_payroll_account(PAYROLL_ACCOUNT_DISPLAY) or "106688385",
)
RQ_EMPLOYER_ID = os.environ.get("PAYROLL_RQ_EMPLOYER_ID", "1003372801")
RQ_PARTNER_REGISTRATION = os.environ.get("PAYROLL_RQ_PARTNER_REGISTRATION", "I1000625")
RQ_NEQ = os.environ.get("PAYROLL_RQ_NEQ", "1142427765")
RQ_PARTNER_ID = os.environ.get("PAYROLL_RQ_PARTNER_ID", "0000000000000271")
RQ_PRODUCT_ID = os.environ.get("PAYROLL_RQ_PRODUCT_ID", RQ_PARTNER_ID)
RQ_SCHEMA_VERSION = os.environ.get("PAYROLL_RQ_SCHEMA_VERSION", "2025.1")
RQ_PREPARATEUR_NO = os.environ.get("PAYROLL_RQ_PREPARATEUR_NO", "NP100625")
RQ_CERTIFICATION_NO = os.environ.get("PAYROLL_RQ_CERTIFICATION_NO", "RQ-26-01-010")
RQ_DOSSIER_NO = os.environ.get("PAYROLL_RQ_DOSSIER_NO", "0271")
RQ_RELEVE_SEQ_BASE = int(os.environ.get("PAYROLL_RQ_RELEVE_SEQ_BASE", "71997012"))
RQ_SOFTWARE_NAME = os.environ.get("PAYROLL_RQ_SOFTWARE_NAME", "Canadian Payroll Service")
RQ_SOFTWARE_VERSION = os.environ.get("PAYROLL_RQ_SOFTWARE_VERSION", "2026-01")


def provider_address() -> TaxPartyAddress:
    return TaxPartyAddress(
        line1=PROVIDER_ADDRESS_LINE1,
        city=PROVIDER_CITY,
        province=PROVIDER_PROVINCE,
        postalCode=PROVIDER_POSTAL_CODE,
    )


def filing_employer_display_name(client_name: str) -> str:
    return f"{client_name}@{PROVIDER_NAME}"


def build_filing_employer_summary(client_name: str) -> T4EmployerSummary:
    """Employer block for T4/Relevé-1: client@provider name with GP BN and address."""
    return T4EmployerSummary(
        name=filing_employer_display_name(client_name),
        businessNumber=PROVIDER_BUSINESS_NUMBER,
        payrollAccountNumber=PAYROLL_ACCOUNT_DISPLAY,
        address=provider_address(),
    )
