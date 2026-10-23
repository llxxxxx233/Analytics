"""核心指标计算。

所有销量、销售额、比率等关键数字由本模块用确定性代码计算，
供看板与（后续阶段的）AI 层复用。AI 不参与指标数值的产出。
"""
from __future__ import annotations

import pandas as pd

REQUIRED_ORDER_COLUMNS = {"order_date", "product_name", "quantity", "amount"}


def ensure_columns(df: pd.DataFrame, required: set[str]) -> None:
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"缺少必要字段: {', '.join(sorted(missing))}")


def filter_orders(
    orders: pd.DataFrame,
    start: pd.Timestamp | None = None,
    end: pd.Timestamp | None = None,
    categories: list[str] | None = None,
    channels: list[str] | None = None,
) -> pd.DataFrame:
    """按日期范围、品类、渠道筛选订单。"""
    df = orders.copy()
    if "order_date" in df.columns:
        if start is not None:
            df = df[df["order_date"] >= pd.Timestamp(start)]
        if end is not None:
            df = df[df["order_date"] <= pd.Timestamp(end)]
    if categories and "category" in df.columns:
        df = df[df["category"].isin(categories)]
    if channels and "channel" in df.columns:
        df = df[df["channel"].isin(channels)]
    return df


def compute_summary(orders: pd.DataFrame) -> dict:
    """总览指标：总销售额、总销量、订单行数、商品数、时间范围。"""
    ensure_columns(orders, {"order_date", "product_name", "quantity", "amount"})
    return {
        "total_amount": float(orders["amount"].sum()),
        "total_quantity": float(orders["quantity"].sum()),
        "order_rows": int(len(orders)),
        "n_products": int(orders["product_name"].nunique()),
        "start_date": orders["order_date"].min(),
        "end_date": orders["order_date"].max(),
    }


def sales_by_product(orders: pd.DataFrame) -> pd.DataFrame:
    """按商品汇总：销量、销售额、订单行数、均价。"""
    ensure_columns(orders, {"product_name", "quantity", "amount"})
    g = (
        orders.groupby("product_name", dropna=False)
        .agg(quantity=("quantity", "sum"), amount=("amount", "sum"), order_rows=("quantity", "size"))
        .reset_index()
    )
    g["avg_price"] = g["amount"] / g["quantity"].replace(0, pd.NA)
    return g.sort_values("amount", ascending=False).reset_index(drop=True)


def sales_by_category(orders: pd.DataFrame) -> pd.DataFrame:
    """按品类汇总（依赖商品信息已合并进订单表）。"""
    if "category" not in orders.columns:
        return pd.DataFrame(columns=["category", "quantity", "amount", "order_rows"])
    g = (
        orders.groupby("category", dropna=False)
        .agg(quantity=("quantity", "sum"), amount=("amount", "sum"), order_rows=("quantity", "size"))
        .reset_index()
    )
    return g.sort_values("amount", ascending=False).reset_index(drop=True)


def sales_by_channel(orders: pd.DataFrame) -> pd.DataFrame:
    """按销售渠道汇总。"""
    if "channel" not in orders.columns:
        return pd.DataFrame(columns=["channel", "quantity", "amount", "order_rows"])
    g = (
        orders.groupby("channel", dropna=False)
        .agg(quantity=("quantity", "sum"), amount=("amount", "sum"), order_rows=("quantity", "size"))
        .reset_index()
    )
    return g.sort_values("amount", ascending=False).reset_index(drop=True)


def sales_trend(orders: pd.DataFrame, freq: str = "D") -> pd.DataFrame:
    """按日 / 周 / 月聚合销售趋势。"""
    ensure_columns(orders, {"order_date", "quantity", "amount"})
    df = orders.copy()
    df["order_date"] = pd.to_datetime(df["order_date"])
    df = df.set_index("order_date")
    freq_map = {"D": "D", "W": "W-MON", "M": "ME"}
    agg = (
        df.resample(freq_map.get(freq, "D"))
        .agg(quantity=("quantity", "sum"), amount=("amount", "sum"), order_rows=("quantity", "size"))
        .reset_index()
    )
    # 无销售的日期不展示
    return agg.dropna(subset=["quantity"]).reset_index(drop=True)


def inventory_coverage(orders: pd.DataFrame, inventory: pd.DataFrame) -> pd.DataFrame:
    """库存覆盖天数 = 当前库存 / 日均销量（按订单覆盖的天数估算）。"""
    ensure_columns(orders, {"order_date", "product_name", "quantity"})
    if inventory is None or inventory.empty or "stock" not in inventory.columns:
        return pd.DataFrame(columns=["product_name", "stock", "total_quantity", "avg_daily_sales", "coverage_days"])

    sales = orders.groupby("product_name")["quantity"].sum().rename("total_quantity")
    days = (orders["order_date"].max() - orders["order_date"].min()).days + 1
    avg_daily = sales / max(days, 1)

    inv = inventory.drop_duplicates(subset="product_name", keep="first").copy()
    out = inv.merge(avg_daily.rename("avg_daily_sales"), on="product_name", how="left")
    out = out.merge(sales, on="product_name", how="left")
    out["total_quantity"] = out["total_quantity"].fillna(0)
    out["coverage_days"] = out["stock"] / out["avg_daily_sales"].replace(0, pd.NA)
    return out.sort_values("coverage_days", na_position="last").reset_index(drop=True)
