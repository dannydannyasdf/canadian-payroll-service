from decimal import Decimal
from pathlib import Path

import xmlschema
from lxml import etree

from app.models.payroll import Deductions, Earnings, Employee, Employer, PayPeriod, PayrollPayload

XSD_PATH = Path(__file__).resolve().parents[2] / "schemas" / "payroll.xsd"
PAYROLL_NS = "https://payroll.example.ca/schema/v1"


def validate_payroll_xml(xml_text: str) -> PayrollPayload:
    """
    Validate incoming XML against payroll.xsd and return a PayrollPayload.
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

    def optional_money(xpath: str) -> Decimal | None:
        node = root.find(xpath, namespaces=ns)
        if node is None or node.text is None:
            return None
        return Decimal(node.text.strip())

    def optional_text(xpath: str) -> str | None:
        node = root.find(xpath, namespaces=ns)
        if node is None or node.text is None:
            return None
        value = node.text.strip()
        return value or None

    federal_tax = optional_money("p:deductions/p:federalIncomeTax")
    provincial_tax = optional_money("p:deductions/p:provincialIncomeTax")
    total_tax = money("p:deductions/p:incomeTax")

    return PayrollPayload(
        employer=Employer(name=text("p:employer/p:name")),
        employee=Employee(
            name=text("p:employee/p:name"),
            sin=text("p:employee/p:sin"),
        ),
        payPeriod=PayPeriod(
            startDate=text("p:payPeriod/p:startDate"),
            endDate=text("p:payPeriod/p:endDate"),
            payDate=text("p:payPeriod/p:payDate"),
        ),
        earnings=Earnings(grossPay=money("p:earnings/p:grossPay")),
        deductions=Deductions(
            cpp=money("p:deductions/p:cpp"),
            ei=money("p:deductions/p:ei"),
            incomeTax=total_tax,
            federalIncomeTax=federal_tax,
            provincialIncomeTax=provincial_tax,
            qpip=optional_money("p:deductions/p:qpip") or Decimal("0.00"),
        ),
        netPay=money("p:netPay"),
        comments=optional_text("p:comments"),
        comments2=optional_text("p:comments2"),
    )
