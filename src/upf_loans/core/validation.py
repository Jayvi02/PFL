"""Validation of employee identifiers."""

from __future__ import annotations

import re

OLD_NIC = re.compile(r"^\d{9}[VvXx]$")
NEW_NIC = re.compile(r"^\d{12}$")
PF_NUMBER = re.compile(r"^[A-Za-z]\s?\d{5,7}$")


def normalise_pf_number(value: str) -> str:
    return " ".join((value or "").upper().split())


def normalise_nic(value: str) -> str:
    return (value or "").strip().upper()


def validate_nic(nic: str) -> str | None:
    """Return an error message, or None when the NIC is acceptable."""
    if not nic:
        return "NIC is required."
    if OLD_NIC.match(nic) or NEW_NIC.match(nic):
        return None
    return "NIC must be 9 digits followed by V/X, or 12 digits."


def nic_warning(nic: str) -> str | None:
    if NEW_NIC.match(nic or ""):
        return "12-digit NICs do not fit the 10-character UGC text field."
    return None


def validate_pf_number(pf: str) -> str | None:
    if not pf:
        return "PF number is required."
    if len(pf) > 8:
        return "PF number must be at most 8 characters (UGC limit)."
    if not PF_NUMBER.match(pf):
        return "PF number should look like R 001365 or F000425."
    return None
