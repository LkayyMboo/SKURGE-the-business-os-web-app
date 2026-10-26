"""
formatters.py

Shared display-formatting helpers. Currently just currency.

All money in SKURGE is stored and calculated as INTEGER CENTS
(amount_cents), never as float Rand values — floats cannot represent
amounts like 0.10 exactly, which causes cumulative rounding errors in
totals. This module is the one place that converts cents to a
human-readable Rand string for display.
"""


def format_cents_as_rand(amount_cents: int) -> str:
    """
    Format integer cents as a Rand string, e.g. 350000 -> 'R 3,500.00'.
    Negative amounts (e.g. a negative net cash movement) are shown
    with a leading minus sign: -150000 -> '-R 1,500.00'.
    """
    sign = "-" if amount_cents < 0 else ""
    whole_rand = abs(amount_cents) // 100
    remainder_cents = abs(amount_cents) % 100
    return f"{sign}R {whole_rand:,.0f}.{remainder_cents:02d}"
