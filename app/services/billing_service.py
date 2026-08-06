from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.db_models import BillingEvent

# Service fee = 1/3 of gross, recorded for metering (payor + payee remittance model).
BILLING_RATE = Decimal("0.333333")


def record_billing_event(
    db: Session,
    *,
    consumer_username: str | None,
    gross_pay: Decimal,
) -> BillingEvent | None:
    if not consumer_username:
        return None

    billing_fee = (gross_pay * BILLING_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    event = BillingEvent(
        consumer_username=consumer_username,
        gross_pay=gross_pay,
        billing_fee=billing_fee,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
