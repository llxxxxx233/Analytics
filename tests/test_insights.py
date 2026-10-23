import pandas as pd

from src import insights


def test_build_data_context_contains_key_facts():
    summary = {
        "total_amount": 150.0,
        "total_quantity": 10.0,
        "order_rows": 3,
        "n_products": 2,
        "start_date": pd.Timestamp("2026-01-01"),
        "end_date": pd.Timestamp("2026-01-03"),
    }
    top = pd.DataFrame(
        [
            {"product_name": "商品A", "quantity": 5.0, "amount": 50.0, "avg_price": 10.0},
            {"product_name": "商品B", "quantity": 5.0, "amount": 100.0, "avg_price": 20.0},
        ]
    )
    cats = pd.DataFrame([{"category": "徽章/吧唧", "quantity": 10.0, "amount": 150.0}])
    chans = pd.DataFrame([{"channel": "微店", "quantity": 10.0, "amount": 150.0}])

    ctx = insights.build_data_context(summary, top, cats, chans, None, "模拟数据")

    assert "总销售额 ¥150" in ctx
    assert "商品A" in ctx and "商品B" in ctx
    assert "徽章/吧唧" in ctx and "微店" in ctx
    assert "模拟数据" in ctx


def test_build_product_context():
    product = pd.Series({"product_name": "星轨纪元·徽章/吧唧 A款", "quantity": 20.0, "amount": 400.0, "avg_price": 20.0})
    meta = {"ip": "星轨纪元", "category": "徽章/吧唧", "spec": "A款"}
    ctx = insights.build_product_context(product, meta, rank=1)
    assert "星轨纪元·徽章/吧唧 A款" in ctx
    assert "销量：20 件" in ctx
    assert "第 1 名" in ctx
