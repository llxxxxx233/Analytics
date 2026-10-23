"""数据质量检查。

生成结构化的质量报告：必填字段是否缺失、重复记录、字段缺失量、
异常值（负数量 / 负金额 / 未来日期），以及未能映射到标准字段的列。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

from src.data_loader import STANDARD_COLUMNS

# 订单表必须包含的字段；商品 / 库存表至少需要商品名称
REQUIRED_ORDER_FIELDS = ["order_date", "product_name", "quantity", "amount"]
REQUIRED_PRODUCT_FIELDS = ["product_name"]
REQUIRED_INVENTORY_FIELDS = ["product_name", "stock"]


@dataclass
class QualityReport:
    table_name: str
    n_rows: int = 0
    n_columns: int = 0
    missing_fields: list[str] = field(default_factory=list)  # 完全缺失的必填字段
    duplicate_rows: int = 0
    missing_counts: dict[str, int] = field(default_factory=dict)  # 各标准字段缺失数量
    negative_quantity: int = 0
    negative_amount: int = 0
    future_dates: int = 0
    unknown_columns: list[str] = field(default_factory=list)  # 未映射到标准字段的列

    @property
    def ok(self) -> bool:
        return not self.missing_fields and self.duplicate_rows == 0

    def summary(self) -> str:
        lines = [
            f"数据表：{self.table_name}",
            f"- 行数：{self.n_rows}，列数：{self.n_columns}",
        ]
        if self.missing_fields:
            lines.append(f"- 缺少必填字段：{', '.join(self.missing_fields)}")
        else:
            lines.append("- 必填字段齐全")
        if self.duplicate_rows:
            lines.append(f"- 完全重复的行：{self.duplicate_rows}")
        if self.missing_counts:
            detail = "；".join(f"{k} 缺失 {v}" for k, v in self.missing_counts.items())
            lines.append(f"- 字段缺失：{detail}")
        if self.negative_quantity:
            lines.append(f"- 数量为负的记录：{self.negative_quantity}")
        if self.negative_amount:
            lines.append(f"- 金额为负的记录：{self.negative_amount}")
        if self.future_dates:
            lines.append(f"- 日期晚于今天的记录：{self.future_dates}")
        if self.unknown_columns:
            lines.append(f"- 未识别的列（保留但未参与计算）：{', '.join(self.unknown_columns)}")
        return "\n".join(lines)


def _base_report(df: pd.DataFrame, required_fields: list[str], table_name: str) -> QualityReport:
    columns = [str(c) for c in df.columns]
    missing_fields = [f for f in required_fields if f not in columns]
    unknown = [c for c in columns if c not in STANDARD_COLUMNS]
    std_present = [c for c in STANDARD_COLUMNS if c in columns]
    missing_counts = {c: int(df[c].isna().sum()) for c in std_present if df[c].isna().any()}
    return QualityReport(
        table_name=table_name,
        n_rows=int(len(df)),
        n_columns=len(columns),
        missing_fields=missing_fields,
        duplicate_rows=int(df.duplicated().sum()),
        missing_counts=missing_counts,
        unknown_columns=unknown,
    )


def validate_orders(df: pd.DataFrame) -> QualityReport:
    report = _base_report(df, REQUIRED_ORDER_FIELDS, "订单明细")
    if "quantity" in df.columns:
        report.negative_quantity = int((df["quantity"] < 0).sum())
    if "amount" in df.columns:
        report.negative_amount = int((df["amount"] < 0).sum())
    if "order_date" in df.columns:
        dates = pd.to_datetime(df["order_date"], errors="coerce")
        report.future_dates = int((dates > pd.Timestamp(datetime.now())).sum())
    return report


def validate_products(df: pd.DataFrame) -> QualityReport:
    return _base_report(df, REQUIRED_PRODUCT_FIELDS, "商品信息")


def validate_inventory(df: pd.DataFrame) -> QualityReport:
    return _base_report(df, REQUIRED_INVENTORY_FIELDS, "库存记录")
