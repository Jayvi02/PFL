"""PF loan eligibility / renewal calculation.

This reproduces, column by column, the formulas of the "MAIN" sheet of
``PF LOAN Calculation.xlsx`` (row 5 shown):

    G  PF balance          =E5+F5
    J  Existing loan bal.  =H5-I5
    U  SAL*48              =C5*48
    V  SAL_BAL*120         =D5*120
    W  BAL*0.65            =G5*0.65
    X  LOWEST              =MIN(U5:W5)
    Y  LOAN ABILITY        =IF(Q5>(G5*0.1),(X5-(Q5-(G5*0.1))),X5)
    Z  INS                 =INT(Y5/120)
    AA ELIGIBLE            =Z5*120
    AB LOAN_BAL            =J5
    AC PAY LOAN            =AA5-AB5
    AD flag                =IF(D5<=Z5,"< 60%"," ")
    AG LOAN IN HAND        =AC5-(K5+L5+M5+N5+O5+P5)

The multipliers (48, 120, 0.65, 0.1 and the 120 instalments) are configurable
in Settings; their defaults are the workbook's values. The user confirmed the
workbook formulas are the rules, including the absence of interest.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal

from .money import ZERO, excel_int, round_cents


@dataclass(frozen=True)
class LoanRules:
    salary_multiplier: Decimal = Decimal("48")
    salary_balance_multiplier: Decimal = Decimal("120")
    pf_balance_ratio: Decimal = Decimal("0.65")
    surety_allowance_ratio: Decimal = Decimal("0.10")
    instalment_months: int = 120

    def as_dict(self) -> dict[str, str]:
        return {k: str(v) for k, v in asdict(self).items()}

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "LoanRules":
        defaults = cls()
        return cls(
            salary_multiplier=Decimal(str(data.get("salary_multiplier", defaults.salary_multiplier))),
            salary_balance_multiplier=Decimal(
                str(data.get("salary_balance_multiplier", defaults.salary_balance_multiplier))
            ),
            pf_balance_ratio=Decimal(str(data.get("pf_balance_ratio", defaults.pf_balance_ratio))),
            surety_allowance_ratio=Decimal(
                str(data.get("surety_allowance_ratio", defaults.surety_allowance_ratio))
            ),
            instalment_months=int(str(data.get("instalment_months", defaults.instalment_months))),
        )

    def validate(self) -> list[str]:
        errors = []
        if self.salary_multiplier <= 0:
            errors.append("Salary multiplier must be greater than zero.")
        if self.salary_balance_multiplier <= 0:
            errors.append("Salary balance multiplier must be greater than zero.")
        if not (0 < self.pf_balance_ratio <= 1):
            errors.append("PF balance ratio must be between 0 and 1.")
        if not (0 <= self.surety_allowance_ratio <= 1):
            errors.append("Q allowance ratio must be between 0 and 1.")
        if self.instalment_months <= 0:
            errors.append("Number of instalments must be greater than zero.")
        return errors


@dataclass(frozen=True)
class LoanInputs:
    """Values the officer enters (MAIN sheet columns C-Q)."""

    salary: Decimal = ZERO  # C SALARY
    salary_balance: Decimal = ZERO  # D SAL_BAL
    pf_balance: Decimal = ZERO  # E PF balance at last statement
    contributions_since: Decimal = ZERO  # F contributions since then
    loan_balance: Decimal = ZERO  # H PF loan balance at cut-off
    loan_deductions_since: Decimal = ZERO  # I PF loan deductions since cut-off
    distress_loan: Decimal = ZERO  # K AU_DIS
    staff_loan: Decimal = ZERO  # L STAFF LOAN
    vehicle_loan: Decimal = ZERO  # M AU_VEH
    computer_loan: Decimal = ZERO  # N COMPUTER
    other_loan_1: Decimal = ZERO  # O Loan1
    other_loan_2: Decimal = ZERO  # P Loan2
    q_amount: Decimal = ZERO  # Q NTOT_LOBAL/SURETIES

    @property
    def other_loans_total(self) -> Decimal:
        return (
            self.distress_loan
            + self.staff_loan
            + self.vehicle_loan
            + self.computer_loan
            + self.other_loan_1
            + self.other_loan_2
        )


@dataclass(frozen=True)
class LoanResult:
    total_pf_balance: Decimal  # G
    existing_loan_balance: Decimal  # J / AB
    salary_cap: Decimal  # U
    salary_balance_cap: Decimal  # V
    pf_balance_cap: Decimal  # W
    lowest_cap: Decimal  # X
    q_deduction: Decimal  # X - Y
    loan_ability: Decimal  # Y
    instalment: Decimal  # Z / AF
    loan_approved: Decimal  # AA
    balance_payable: Decimal  # AC
    loan_in_hand: Decimal  # AG
    salary_balance_flag: bool  # AD ("< 60%")
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def limiting_cap(self) -> str:
        caps = {
            "salary": self.salary_cap,
            "salary_balance": self.salary_balance_cap,
            "pf_balance": self.pf_balance_cap,
        }
        return min(caps, key=lambda k: caps[k])


def calculate(inputs: LoanInputs, rules: LoanRules | None = None) -> LoanResult:
    rules = rules or LoanRules()
    months = Decimal(rules.instalment_months)

    total_pf_balance = inputs.pf_balance + inputs.contributions_since
    existing_loan_balance = inputs.loan_balance - inputs.loan_deductions_since

    salary_cap = inputs.salary * rules.salary_multiplier
    salary_balance_cap = inputs.salary_balance * rules.salary_balance_multiplier
    pf_balance_cap = total_pf_balance * rules.pf_balance_ratio
    lowest_cap = min(salary_cap, salary_balance_cap, pf_balance_cap)

    allowance = total_pf_balance * rules.surety_allowance_ratio
    if inputs.q_amount > allowance:
        loan_ability = lowest_cap - (inputs.q_amount - allowance)
    else:
        loan_ability = lowest_cap

    instalment = excel_int(loan_ability / months)
    loan_approved = instalment * months
    balance_payable = loan_approved - existing_loan_balance
    loan_in_hand = balance_payable - inputs.other_loans_total
    flag = inputs.salary_balance <= instalment

    warnings: list[str] = []
    if loan_approved <= 0:
        warnings.append("The calculated loan is zero or negative.")
    if balance_payable < 0:
        warnings.append("The existing loan balance is higher than the new loan.")
    if loan_in_hand < 0:
        warnings.append("Other university loans are higher than the balance payable.")
    if flag:
        warnings.append("Salary balance is less than or equal to the instalment (< 60% flag).")

    return LoanResult(
        total_pf_balance=total_pf_balance,
        existing_loan_balance=existing_loan_balance,
        salary_cap=salary_cap,
        salary_balance_cap=salary_balance_cap,
        pf_balance_cap=pf_balance_cap,
        lowest_cap=lowest_cap,
        q_deduction=lowest_cap - loan_ability,
        loan_ability=loan_ability,
        instalment=instalment,
        loan_approved=round_cents(loan_approved),
        balance_payable=round_cents(balance_payable),
        loan_in_hand=round_cents(loan_in_hand),
        salary_balance_flag=flag,
        warnings=tuple(warnings),
    )
