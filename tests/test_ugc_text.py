from decimal import Decimal as D

import pytest

from upf_loans.core.ugc_text import LINE_LENGTH, UgcFormatError, UgcRow, build_file, format_row


def row(**kw):
    base = dict(name="A", pf_number="R 001365", nic="680410054V", request_month=11, request_year=2024,
                last_loan_month=10, last_loan_year=2023, loan_approved=D(2423400), existing_balance=D(1610470),
                balance_payable=D(812930), university_code="F")
    base.update(kw)
    return UgcRow(**base)


def test_first_row_of_send_sheet():
    expected = ("A" + " " * 49 + "R 001365" + "680410054V" + "11" + "2024" + "10" + "2023"
                + "000002423400.00" + "000001610470.00" + "000000812930.00" + " F")
    assert format_row(row()) == expected
    assert len(expected) == LINE_LENGTH == 127


def test_short_pf_number_and_month_padding():
    line = format_row(row(pf_number="F000288", request_month=3, last_loan_month=7))
    assert line[50:58] == "F000288 "
    assert line[68:70] == "03"
    assert line[74:76] == "07"


def test_two_character_university_code():
    assert format_row(row(university_code="R"))[-2:] == " R"
    assert format_row(row(university_code="UR"))[-2:] == "UR"


@pytest.mark.parametrize("kw, message", [
    (dict(nic="1972700003754"), "NIC"),
    (dict(nic="197270000375"), "NIC"),
    (dict(name="X" * 51), "name"),
    (dict(balance_payable=D(-1)), "negative"),
    (dict(loan_approved=D("1000000000000")), "too large"),
    (dict(request_month=13), "month"),
])
def test_rejects_values_that_do_not_fit(kw, message):
    with pytest.raises(UgcFormatError, match=message):
        format_row(row(**kw))


def test_build_file_crlf_and_all_errors_reported():
    text, errors = build_file([row(), row(pf_number="F000425")])
    assert errors == []
    assert text.count("\r\n") == 2
    text, errors = build_file([row(nic="1972700003754"), row(name="Y" * 60)])
    assert text == "" and len(errors) == 2


def test_missing_last_loan_is_blank():
    line = format_row(row(last_loan_month=None, last_loan_year=None))
    assert line[74:80] == " " * 6
