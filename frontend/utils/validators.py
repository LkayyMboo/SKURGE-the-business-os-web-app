"""
validators.py

Shared input-validation helpers used across screens/services.
"""

from decimal import Decimal, InvalidOperation


def parse_rand_input_to_cents(text: str) -> int:
    """
    Parse a user-typed Rand amount (e.g. "350", "350.00", "R 350.50",
    "3,500.00") into integer cents (e.g. 35000, 35000, 35050, 350000).

    Uses Decimal rather than float, specifically to avoid the classic
    floating-point problem where amounts like 0.10 cannot be
    represented exactly in binary and silently accumulate rounding
    errors across many transactions.

    Raises ValueError with a clear message if the input is not a
    valid positive monetary amount.
    """
    if text is None:
        raise ValueError("Amount is required.")

    cleaned = text.strip().replace("R", "").replace(",", "").strip()
    if not cleaned:
        raise ValueError("Amount is required.")

    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        raise ValueError("Enter a valid amount, e.g. 350.00.")

    if value <= 0:
        raise ValueError("Amount must be greater than zero.")

    cents = int((value * 100).to_integral_value(rounding="ROUND_HALF_UP"))
    return cents


def validate_iso_date(text: str):
    """
    Validate a date string is a real calendar date in YYYY-MM-DD
    format. Returns the parsed datetime.date on success, or raises
    ValueError with a clear message.
    """
    from datetime import date

    if not text or not text.strip():
        raise ValueError("Date is required.")
    try:
        return date.fromisoformat(text.strip())
    except ValueError:
        raise ValueError("Enter a valid date in YYYY-MM-DD format, e.g. 2026-10-11.")
