from decimal import Decimal
from pathlib import Path

import xmlschema
from lxml import etree

XSD_PATH = Path(__file__).resolve().parents[2] / "schemas" / "payroll.xsd"
PAYROLL_NS = "https://payroll.example.ca/schema/v1"


def validate_payroll_xml(xml_text: str) -> dict:
    """
    Validate incoming XML against payroll.xsd and return a plain dict
    the PDF renderer can consume.
    """
    schema = xmlschema.XMLSchema(str(XSD_PATH))

    try:
        schema.validate(xml_text)
    except xmlschema.XMLSchemaValidationError as exc:
        raise ValueError(f"Invalid payroll XML: {exc.reason}") from exc

    root = etree.fromstring(xml_text.encode("utf-8"))
    ns = {"p": PAYROLL_NS}

    def text(xpath: str) -> str:
        node = root.find(xpath, namespaces=ns)
        if node is None or node.text is None:
            raise ValueError(f"Missing required field: {xpath}")
        return node.text.strip()

    def money(xpath: str) -> Decimal:
        return Decimal(text(xpath))

    return {
        "employer_name": text("p:employer/p:name"),
        "employee_name": text("p:employee/p:name"),
        "employee_sin": text("p:employee/p:sin"),
        "period_start": text("p:payPeriod/p:startDate"),
        "period_end": text("p:payPeriod/p:endDate"),
        "pay_date": text("p:payPeriod/p:payDate"),
        "gross_pay": money("p:earnings/p:grossPay"),
        "cpp": money("p:deductions/p:cpp"),
        "ei": money("p:deductions/p:ei"),
        "income_tax": money("p:deductions/p:incomeTax"),
        "net_pay": money("p:netPay"),
    }
