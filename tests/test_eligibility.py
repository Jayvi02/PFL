"""The calculation must reproduce the workbook's cached results exactly."""

from decimal import Decimal as D

import pytest

from upf_loans.core.eligibility import LoanInputs, LoanRules, calculate

# Rows of '2024 MAIN NOVEMBER' with Excel's own calculated results.
# (salary, sal_bal, E, F, H, I, other loans K..P total as vehicle, Q) -> (Z, AA, AC, AG, Y, AD flag)
CASES = [
    ("row5", "1000", "2000", "80000", "0", "500", "200", "0", "12000", 366, "43920", "43620", "43620", "44000", False),
    ("row7", "72791", "26455", "3622669.53", "105650.79", "1760970", "150500", "30000", "0",
     20195, "2423400", "812930", "782930", "2423408.208", False),
    ("row10", "89140", "163525.76", "6374638.41", "0", "2321160", "0", "0", "0",
     34529, "4143480", "1822320", "1822320", "4143514.9665", False),
    ("row13", "110510", "87237", "6377610.72", "0", "2518120", "0", "0", "250000",
     34545, "4145400", "1627280", "1627280", "4145446.968", False),
    ("row15", "130850", "242189.69", "16027518.62", "0", "5536080", "0", "0", "187510",
     52340, "6280800", "744720", "744720", "6280800", False),
]


@pytest.mark.parametrize("case", CASES, ids=[c[0] for c in CASES])
def test_matches_workbook(case):
    _, sal, salbal, e, f, h, i, veh, q, ins, eligible, pay, in_hand, ability, flag = case
    r = calculate(LoanInputs(salary=D(sal), salary_balance=D(salbal), pf_balance=D(e), contributions_since=D(f),
                             loan_balance=D(h), loan_deductions_since=D(i), vehicle_loan=D(veh), q_amount=D(q)))
    assert r.instalment == ins
    assert r.loan_approved == D(eligible)
    assert r.balance_payable == D(pay)
    assert r.loan_in_hand == D(in_hand)
    assert r.loan_ability == D(ability)
    assert r.salary_balance_flag is flag


def test_q_deduction_applies_above_ten_percent():
    # Row 5: PF balance 80,000; Q 12,000 > 8,000, so 4,000 comes off the 48,000 cap.
    r = calculate(LoanInputs(salary=D(1000), salary_balance=D(2000), pf_balance=D(80000), q_amount=D(12000)))
    assert r.lowest_cap == D(48000)
    assert r.q_deduction == D(4000)
    assert r.loan_ability == D(44000)


def test_q_at_or_below_allowance_has_no_effect():
    base = LoanInputs(salary=D(1000), salary_balance=D(2000), pf_balance=D(80000), q_amount=D(8000))
    assert calculate(base).q_deduction == 0


def test_flag_when_salary_balance_le_instalment():
    r = calculate(LoanInputs(salary=D(100000), salary_balance=D(100), pf_balance=D(10_000_000)))
    assert r.instalment == 100  # capped by 120 x salary balance
    assert r.salary_balance_flag


def test_loan_is_multiple_of_instalment_count():
    r = calculate(LoanInputs(salary=D("12345.67"), salary_balance=D("9999.99"), pf_balance=D("777777.77")))
    assert r.loan_approved % 120 == 0


def test_negative_ability_follows_excel_int():
    # Excel INT rounds towards minus infinity; no floor at zero, but a warning is raised.
    r = calculate(LoanInputs(salary=D(100), salary_balance=D(100), pf_balance=D(1000), q_amount=D(10000)))
    assert r.lowest_cap == D(650)
    assert r.loan_ability == D(650) - (D(10000) - D(100))  # -9250
    assert r.instalment == -78  # INT(-77.08)
    assert r.warnings


def test_rules_are_configurable():
    rules = LoanRules(salary_multiplier=D(24))
    r = calculate(LoanInputs(salary=D(1000), salary_balance=D(2000), pf_balance=D(80000)), rules)
    assert r.salary_cap == D(24000)
    assert r.loan_approved == D(24000)
