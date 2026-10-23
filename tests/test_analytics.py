import pandas as pd

from src.analytics import compute_summary, sales_by_product, sales_trend


def make_orders() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "order_date": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]),
            "product_name": ["商品A", "商品A", "商品B"],
            "quantity": [2.0, 3.0, 5.0],
            "amount": [20.0, 30.0, 100.0],
            "channel": ["微店", "淘宝", "微店"],
        }
    )


def test_sales_by_product_sums_match_manual():
    df = sales_by_product(make_orders())
    a = df[df["product_name"] == "商品A"].iloc[0]
    assert a["quantity"] == 5.0
    assert a["amount"] == 50.0
    assert a["order_rows"] == 2
    assert a["avg_price"] == 10.0


def test_compute_summary():
    s = compute_summary(make_orders())
    assert s["total_amount"] == 150.0
    assert s["total_quantity"] == 10.0
    assert s["order_rows"] == 3
    assert s["n_products"] == 2


def test_sales_trend_daily():
    t = sales_trend(make_orders(), freq="D")
    assert len(t) == 3
    assert t["quantity"].sum() == 10.0
