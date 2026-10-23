import pandas as pd

from src.data_validator import validate_orders


def test_detect_missing_required_field():
    df = pd.DataFrame({"order_date": ["2026-01-01"], "product_name": ["A"], "quantity": [1.0]})
    report = validate_orders(df)
    assert "amount" in report.missing_fields


def test_detect_duplicate_rows():
    df = pd.DataFrame(
        {
            "order_date": pd.to_datetime(["2026-01-01", "2026-01-01"]),
            "product_name": ["A", "A"],
            "quantity": [1.0, 1.0],
            "amount": [10.0, 10.0],
        }
    )
    report = validate_orders(df)
    assert report.duplicate_rows == 1
    assert report.ok is False


def test_detect_negative_and_future():
    df = pd.DataFrame(
        {
            "order_date": pd.to_datetime(["2099-01-01", "2026-01-01"]),
            "product_name": ["A", "B"],
            "quantity": [-1.0, 1.0],
            "amount": [10.0, -5.0],
        }
    )
    report = validate_orders(df)
    assert report.negative_quantity == 1
    assert report.negative_amount == 1
    assert report.future_dates == 1
