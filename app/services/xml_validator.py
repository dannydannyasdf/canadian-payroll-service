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
            incomeTax=money("p:deductions/p:incomeTax"),
        ),
        netPay=money("p:netPay"),
    )
