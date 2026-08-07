from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

ACTIVE_STATUS = "active"
INACTIVE_STATUS = "inactive"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EmployerRecord(Base):
    __tablename__ = "employers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    business_number: Mapped[str | None] = mapped_column(String(15), nullable=True)
    payroll_account_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address_line1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    province: Mapped[str | None] = mapped_column(String(2), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(7), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=ACTIVE_STATUS)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        server_default=text("(CURRENT_TIMESTAMP)"),
        nullable=False,
    )

    employees: Mapped[list["EmployeeRecord"]] = relationship(back_populates="employer")


class EmployeeRecord(Base):
    __tablename__ = "employees"
    __table_args__ = (UniqueConstraint("employer_id", "sin", name="uq_employee_employer_sin"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employer_id: Mapped[int] = mapped_column(ForeignKey("employers.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sin: Mapped[str] = mapped_column(String(11), nullable=False)
    address_line1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    province: Mapped[str | None] = mapped_column(String(2), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(7), nullable=True)
    employment_province: Mapped[str | None] = mapped_column(String(2), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=ACTIVE_STATUS)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        server_default=text("(CURRENT_TIMESTAMP)"),
        nullable=False,
    )

    employer: Mapped["EmployerRecord"] = relationship(back_populates="employees")
    ytd_records: Mapped[list["YtdRecord"]] = relationship(back_populates="employee")
    pay_periods: Mapped[list["PayPeriodRecord"]] = relationship(back_populates="employee")


class PayPeriodRecord(Base):
    __tablename__ = "pay_periods"
    __table_args__ = (
        UniqueConstraint(
            "employee_id",
            "period_start",
            "period_end",
            name="uq_pay_period_employee_dates",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    tax_year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    pay_date: Mapped[date] = mapped_column(Date, nullable=False)
    gross_pay: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    cpp: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    ei: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    income_tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    net_pay: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("(CURRENT_TIMESTAMP)"),
        nullable=False,
    )

    employee: Mapped["EmployeeRecord"] = relationship(back_populates="pay_periods")


class YtdRecord(Base):
    __tablename__ = "ytd_totals"
    __table_args__ = (UniqueConstraint("employee_id", "tax_year", name="uq_ytd_employee_year"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    tax_year: Mapped[int] = mapped_column(Integer, nullable=False)
    gross_pay: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    cpp: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    ei: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    income_tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    net_pay: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    last_period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_pay_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("(CURRENT_TIMESTAMP)"),
        onupdate=func.now(),
        nullable=False,
    )

    employee: Mapped["EmployeeRecord"] = relationship(back_populates="ytd_records")


class BillingEvent(Base):
    """Usage log for pay-per-use billing (% of gross pay)."""

    __tablename__ = "billing_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    consumer_username: Mapped[str] = mapped_column(String(128), nullable=False)
    gross_pay: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    billing_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("(CURRENT_TIMESTAMP)"),
        nullable=False,
    )
