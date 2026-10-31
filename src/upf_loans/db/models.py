"""Database models.

Money columns store integer cents through the :class:`Money` type and are read
back as Decimal.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from ..core.eligibility import LoanInputs, LoanResult
from ..core.money import from_cents, to_cents


class Money(TypeDecorator):
    impl = Integer
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return to_cents(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return from_cents(value)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Employee(TimestampMixin, Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    pf_number: Mapped[str] = mapped_column(String(8), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(50), index=True)
    nic: Mapped[str] = mapped_column(String(12), index=True)
    department: Mapped[str] = mapped_column(String(100), default="")
    category: Mapped[str] = mapped_column(String(1), default="N")  # A = academic, N = non-academic
    designation: Mapped[str] = mapped_column(String(100), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    entries: Mapped[list["RenewalEntry"]] = relationship(back_populates="employee")


class RenewalBatch(TimestampMixin, Base):
    """One month's renewal list sent to UGC."""

    __tablename__ = "renewal_batches"
    __table_args__ = (UniqueConstraint("request_year", "request_month", name="uq_batch_month"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    request_month: Mapped[int] = mapped_column(Integer)
    request_year: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(12), default="draft")  # draft | finalized
    letter_date: Mapped[str] = mapped_column(String(10), default="")  # dd.mm.yyyy printed under BURSAR
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finalized_by: Mapped[str] = mapped_column(String(50), default="")
    notes: Mapped[str] = mapped_column(Text, default="")

    entries: Mapped[list["RenewalEntry"]] = relationship(
        back_populates="batch", cascade="all, delete-orphan", order_by="RenewalEntry.position"
    )

    @property
    def is_locked(self) -> bool:
        return self.status == "finalized"


class RenewalEntry(TimestampMixin, Base):
    """One row of the MAIN calculation sheet inside a monthly batch."""

    __tablename__ = "renewal_entries"
    __table_args__ = (UniqueConstraint("batch_id", "employee_id", name="uq_entry_employee"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("renewal_batches.id", ondelete="CASCADE"), index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="RESTRICT"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)

    # Inputs (MAIN sheet C-Q)
    salary: Mapped[Decimal] = mapped_column(Money, default=0)
    salary_balance: Mapped[Decimal] = mapped_column(Money, default=0)
    pf_balance: Mapped[Decimal] = mapped_column(Money, default=0)
    contributions_since: Mapped[Decimal] = mapped_column(Money, default=0)
    loan_balance: Mapped[Decimal] = mapped_column(Money, default=0)
    loan_deductions_since: Mapped[Decimal] = mapped_column(Money, default=0)
    distress_loan: Mapped[Decimal] = mapped_column(Money, default=0)
    staff_loan: Mapped[Decimal] = mapped_column(Money, default=0)
    vehicle_loan: Mapped[Decimal] = mapped_column(Money, default=0)
    computer_loan: Mapped[Decimal] = mapped_column(Money, default=0)
    other_loan_1: Mapped[Decimal] = mapped_column(Money, default=0)
    other_loan_2: Mapped[Decimal] = mapped_column(Money, default=0)
    q_amount: Mapped[Decimal] = mapped_column(Money, default=0)
    last_loan_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_loan_year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Results snapshot (MAIN sheet G, J, U-AG) and the rules used
    total_pf_balance: Mapped[Decimal] = mapped_column(Money, default=0)
    existing_loan_balance: Mapped[Decimal] = mapped_column(Money, default=0)
    salary_cap: Mapped[Decimal] = mapped_column(Money, default=0)
    salary_balance_cap: Mapped[Decimal] = mapped_column(Money, default=0)
    pf_balance_cap: Mapped[Decimal] = mapped_column(Money, default=0)
    lowest_cap: Mapped[Decimal] = mapped_column(Money, default=0)
    loan_ability: Mapped[Decimal] = mapped_column(Money, default=0)
    instalment: Mapped[Decimal] = mapped_column(Money, default=0)
    loan_approved: Mapped[Decimal] = mapped_column(Money, default=0)
    balance_payable: Mapped[Decimal] = mapped_column(Money, default=0)
    loan_in_hand: Mapped[Decimal] = mapped_column(Money, default=0)
    salary_balance_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    rules_json: Mapped[str] = mapped_column(Text, default="{}")

    batch: Mapped[RenewalBatch] = relationship(back_populates="entries")
    employee: Mapped[Employee] = relationship(back_populates="entries")

    INPUT_FIELDS = (
        "salary",
        "salary_balance",
        "pf_balance",
        "contributions_since",
        "loan_balance",
        "loan_deductions_since",
        "distress_loan",
        "staff_loan",
        "vehicle_loan",
        "computer_loan",
        "other_loan_1",
        "other_loan_2",
        "q_amount",
    )

    def to_inputs(self) -> LoanInputs:
        return LoanInputs(**{name: getattr(self, name) or Decimal(0) for name in self.INPUT_FIELDS})

    def apply_inputs(self, inputs: LoanInputs) -> None:
        for name in self.INPUT_FIELDS:
            setattr(self, name, getattr(inputs, name))

    def apply_result(self, result: LoanResult) -> None:
        for name in (
            "total_pf_balance",
            "existing_loan_balance",
            "salary_cap",
            "salary_balance_cap",
            "pf_balance_cap",
            "lowest_cap",
            "loan_ability",
            "instalment",
            "loan_approved",
            "balance_payable",
            "loan_in_hand",
            "salary_balance_flag",
        ):
            setattr(self, name, getattr(result, name))


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    username: Mapped[str] = mapped_column(String(50), default="")
    action: Mapped[str] = mapped_column(String(50))
    entity: Mapped[str] = mapped_column(String(50), default="")
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    details_json: Mapped[str] = mapped_column(Text, default="{}")
