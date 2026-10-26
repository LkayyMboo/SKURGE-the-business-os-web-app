import pytest

from utils.formatters import format_cents_as_rand
from utils.validators import parse_rand_input_to_cents, validate_iso_date


def test_format_basic_amount():
    assert format_cents_as_rand(350000) == "R 3,500.00"


def test_format_small_amount():
    assert format_cents_as_rand(50) == "R 0.50"


def test_format_zero():
    assert format_cents_as_rand(0) == "R 0.00"


def test_format_negative_amount():
    assert format_cents_as_rand(-150000) == "-R 1,500.00"


def test_parse_plain_number():
    assert parse_rand_input_to_cents("350") == 35000


def test_parse_decimal_number():
    assert parse_rand_input_to_cents("350.50") == 35050


def test_parse_with_rand_symbol_and_commas():
    assert parse_rand_input_to_cents("R 3,500.00") == 350000


def test_parse_rejects_zero():
    with pytest.raises(ValueError):
        parse_rand_input_to_cents("0")


def test_parse_rejects_negative():
    with pytest.raises(ValueError):
        parse_rand_input_to_cents("-50")


def test_parse_rejects_garbage():
    with pytest.raises(ValueError):
        parse_rand_input_to_cents("not a number")


def test_parse_rejects_empty():
    with pytest.raises(ValueError):
        parse_rand_input_to_cents("")


def test_validate_iso_date_accepts_valid_date():
    result = validate_iso_date("2026-10-11")
    assert result.year == 2026 and result.month == 10 and result.day == 11


def test_validate_iso_date_rejects_invalid_date():
    with pytest.raises(ValueError):
        validate_iso_date("2026-13-40")


def test_validate_iso_date_rejects_wrong_format():
    with pytest.raises(ValueError):
        validate_iso_date("11/10/2026")


def test_validate_iso_date_rejects_empty():
    with pytest.raises(ValueError):
        validate_iso_date("")
