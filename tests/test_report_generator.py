import pandas as pd

from src import report_generator


def _summary():
    return {
        "total_amount": 150.0,
        "total_quantity": 10.0,
        "order_rows": 3,
        "n_products": 2,
        "start_date": pd.Timestamp("2026-01-01"),
        "end_date": pd.Timestamp("2026-01-03"),
    }


def _top():
    return pd.DataFrame([{"product_name": "商品A", "quantity": 5.0, "amount": 50.0, "avg_price": 10.0}])


def test_build_report_contains_key_sections():
    cats = pd.DataFrame([{"category": "徽章/吧唧", "quantity": 10.0, "amount": 150.0}])
    chans = pd.DataFrame([{"channel": "微店", "quantity": 10.0, "amount": 150.0}])
    md = report_generator.build_report(_summary(), _top(), cats, chans, None, "质量说明", "模拟数据")

    assert md.startswith("# 衍生品经营分析报告")
    assert "数据范围与质量" in md
    assert "核心经营指标" in md
    assert "商品表现 Top 10" in md
    assert "品类表现" in md
    assert "渠道表现" in md
    assert "数据局限与后续验证" in md
    assert "总销售额：¥150" in md


def test_build_report_skips_missing_dimensions():
    md = report_generator.build_report(_summary(), _top(), None, None, None, "质量说明")
    assert "品类表现" not in md
    assert "渠道表现" not in md
    assert "库存风险" not in md
