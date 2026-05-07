from utils.helpers import (
    safe_get, normalize_column_name, normalize_column_names,
    ensure_list, format_percentage, format_currency
)

def test_safe_get():
    d = {"a": 1}
    assert safe_get(d, "a") == 1
    assert safe_get(d, "b", 2) == 2
    assert safe_get(None, "b", 2) == 2

def test_normalize_column_name():
    assert normalize_column_name(" First Name ") == "first_name"
    assert normalize_column_name("Email") == "email"

def test_normalize_column_names():
    assert normalize_column_names([" First Name ", "Email"]) == ["first_name", "email"]

def test_ensure_list():
    assert ensure_list(None) == []
    assert ensure_list("a") == ["a"]
    assert ensure_list(["a", "b"]) == ["a", "b"]
    assert ensure_list((1, 2)) == [1, 2]

def test_format_percentage():
    assert format_percentage(0.1234) == "12.34%"
    assert format_percentage(0.1, 1) == "10.0%"

def test_format_currency():
    assert format_currency(1234.56) == "$1234.56"
    assert format_currency(-1234.56) == "-$1234.56"
    assert format_currency(100, "€", 0) == "€100"
