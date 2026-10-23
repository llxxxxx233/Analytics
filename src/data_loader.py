"""数据读取与字段映射。

将不同来源的订单、商品、库存文件统一为标准字段结构。
关键设计：字段别名映射 —— 兼容中文 / 英文列名；未识别的列保留原名，
由 data_validator 在质量报告中提示，而不是静默丢弃。
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

# 标准字段 -> 可能出现的源列名（别名），按优先级匹配
FIELD_ALIASES: dict[str, list[str]] = {
    "order_id": ["订单号", "订单编号", "订单id", "单号", "order_id", "order number"],
    "order_date": ["订单日期", "下单日期", "下单时间", "日期", "时间", "创建时间", "order_date", "date"],
    "product_name": ["商品名称", "商品", "品名", "产品名称", "商品名", "product_name", "product", "name", "item"],
    "product_id": ["商品id", "商品编号", "货号", "sku", "SKU", "product_id"],
    "category": ["品类", "类别", "分类", "商品类型", "category", "type"],
    "ip": ["ip", "IP", "所属ip", "所属IP", "作品", "系列", "ip_name"],
    "spec": ["规格", "型号", "款式", "尺寸", "spec", "specification"],
    "quantity": ["数量", "销量", "件数", "销售数量", "数量(件)", "quantity", "qty"],
    "amount": ["成交金额", "金额", "销售额", "实付金额", "应付金额", "总价", "amount", "sales", "revenue", "price"],
    "channel": ["渠道", "销售渠道", "平台", "来源", "channel", "source", "platform"],
    "cost": ["成本", "成本价", "进货价", "单位成本", "cost", "unit_cost"],
    "stock": ["库存", "当前库存", "现有库存", "库存数量", "库存量", "stock", "inventory"],
}

STANDARD_COLUMNS: list[str] = list(FIELD_ALIASES.keys())

# 需要转成数字 / 日期的标准字段。非法值转为 NaN（不自动当作 0）。
NUMERIC_FIELDS = {"quantity", "amount", "cost", "stock"}
DATE_FIELDS = {"order_date"}


def read_file(path: str | Path) -> pd.DataFrame:
    """读取 CSV / Excel 文件为 DataFrame。"""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if suffix == ".csv":
        for enc in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
            try:
                return pd.read_csv(path, encoding=enc)
            except UnicodeDecodeError:
                continue
        return pd.read_csv(path)  # 兜底，仍失败则抛出原始异常
    raise ValueError(f"不支持的文件类型: {suffix}（支持 .csv / .xlsx）")


def _match_column(columns: list[str], target: str) -> str | None:
    """在源列名中查找与标准字段 target 匹配的列（忽略大小写与首尾空白）。"""
    aliases = FIELD_ALIASES.get(target, [])
    normalized = {str(c).strip().lower(): c for c in columns}
    for alias in aliases:
        hit = normalized.get(alias.strip().lower())
        if hit is not None:
            return hit
    return None


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """将源列名映射为标准字段名；未识别的列保留原名。"""
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]
    rename: dict[str, str] = {}
    used: set[str] = set()
    for target in STANDARD_COLUMNS:
        src = _match_column(list(out.columns), target)
        if src is not None and src not in used:
            rename[src] = target
            used.add(src)
    return out.rename(columns=rename) if rename else out


def standardize(df: pd.DataFrame) -> pd.DataFrame:
    """对标准字段做类型转换：日期转 datetime，数字转 float。"""
    out = normalize_columns(df)
    for col in out.columns:
        if col in DATE_FIELDS:
            out[col] = pd.to_datetime(out[col], errors="coerce")
        elif col in NUMERIC_FIELDS:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def load_orders(path: str | Path) -> pd.DataFrame:
    return standardize(read_file(path))


def load_products(path: str | Path) -> pd.DataFrame:
    return standardize(read_file(path))


def load_inventory(path: str | Path) -> pd.DataFrame:
    return standardize(read_file(path))


def merge_product_info(orders: pd.DataFrame, products: pd.DataFrame | None) -> pd.DataFrame:
    """按商品名把商品信息（品类 / IP / 规格 / 成本）左连接到订单表。"""
    if products is None or products.empty:
        return orders
    if "product_name" not in orders.columns or "product_name" not in products.columns:
        return orders

    # 商品表去重，避免一对多导致订单行翻倍
    products_dedup = products.drop_duplicates(subset="product_name", keep="first")
    extra_cols = [c for c in products_dedup.columns if c not in orders.columns]
    if not extra_cols:
        return orders
    keep = ["product_name"] + extra_cols
    return orders.merge(products_dedup[keep], on="product_name", how="left")
