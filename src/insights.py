"""AI 洞察编排：把计算结果整理成事实上下文，再交给大模型解释。

关键原则（先计算、后解释）：本模块只负责拼装事实，不产出关键指标；
大模型只负责解释、给结论与建议，数字一律来自 analytics。
"""
from __future__ import annotations

import pandas as pd

from src import llm_service

EXAMPLE_QUESTIONS = [
    "哪些商品卖得最好？",
    "不同品类/渠道的表现有什么差异？",
    "哪些商品可能存在库存风险或值得补货？",
    "当前数据还缺什么，会影响哪些结论？",
    "下一期企划应该优先关注哪些商品？",
]


def build_data_context(
    summary: dict,
    top_products: pd.DataFrame,
    categories: pd.DataFrame,
    channels: pd.DataFrame,
    coverage: pd.DataFrame | None = None,
    source_label: str = "数据",
) -> str:
    """把当前筛选范围下的计算结果整理成给 LLM 的事实文本。"""
    lines = [
        f"数据范围：{summary['start_date']:%Y-%m-%d} ~ {summary['end_date']:%Y-%m-%d}（{source_label}）",
        f"总销售额 ¥{summary['total_amount']:,.0f}；总销量 {summary['total_quantity']:,.0f} 件；"
        f"订单 {summary['order_rows']:,} 行；商品 {summary['n_products']} 个。",
        "",
        "商品销量 Top 10（销量 / 销售额 / 均价）：",
    ]
    for r in top_products.head(10).itertuples():
        avg = f"¥{r.avg_price:,.1f}" if pd.notna(r.avg_price) else "—"
        lines.append(f"- {r.product_name}：{r.quantity:,.0f} 件 / ¥{r.amount:,.0f} / 均价 {avg}")

    if categories is not None and not categories.empty:
        lines += ["", "品类表现（销量 / 销售额）："]
        for r in categories.itertuples():
            if pd.isna(r.category):
                continue
            lines.append(f"- {r.category}：{r.quantity:,.0f} 件 / ¥{r.amount:,.0f}")

    if channels is not None and not channels.empty:
        lines += ["", "渠道表现（销量 / 销售额）："]
        for r in channels.itertuples():
            if pd.isna(r.channel):
                continue
            lines.append(f"- {r.channel}：{r.quantity:,.0f} 件 / ¥{r.amount:,.0f}")

    if coverage is not None and not coverage.empty:
        lines += ["", "库存覆盖天数（当前库存 / 日均销量，仅作参考）："]
        for r in coverage.itertuples():
            cd = f"{r.coverage_days:,.1f} 天" if pd.notna(r.coverage_days) else "无销量，无法估算"
            lines.append(f"- {r.product_name}：库存 {r.stock:,.0f}，覆盖 {cd}")

    return "\n".join(lines)


def build_product_context(product: pd.Series, meta: dict | None = None, rank: int | None = None) -> str:
    """把单个商品的指标整理成给 LLM 的事实文本。"""
    lines = [f"商品：{product['product_name']}"]
    if meta:
        if meta.get("ip"):
            lines.append(f"IP/系列：{meta['ip']}")
        if meta.get("category"):
            lines.append(f"品类：{meta['category']}")
        if meta.get("spec"):
            lines.append(f"规格：{meta['spec']}")
    lines.append(f"销量：{product['quantity']:,.0f} 件；销售额：¥{product['amount']:,.0f}")
    if pd.notna(product.get("avg_price")):
        lines.append(f"均价：¥{product['avg_price']:,.1f}")
    if rank is not None:
        lines.append(f"销量排名：第 {rank} 名")
    return "\n".join(lines)


def ask(question: str, context: str) -> str:
    return llm_service.answer_question(question, context)


def marketing_copy(product_name: str, product_context: str) -> str:
    return llm_service.generate_marketing_copy(product_name, product_context)
