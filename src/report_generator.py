"""结构化报告生成：将指标计算结果整合为 Markdown 报告。

所有数字来自 analytics 的计算结果，本模块只负责排版，不产出指标。
"""
from __future__ import annotations

import pandas as pd

from src import analytics


def build_report(
    summary: dict,
    top_products: pd.DataFrame,
    categories: pd.DataFrame,
    channels: pd.DataFrame,
    coverage: pd.DataFrame | None,
    quality_text: str,
    source_label: str = "数据",
    ai_insight: str | None = None,
) -> str:
    """按章节组装 Markdown 报告。"""
    scope = [
        f"- 统计范围：{summary['start_date']:%Y-%m-%d} ~ {summary['end_date']:%Y-%m-%d}（{source_label}）",
        f"- 订单 {summary['order_rows']:,} 行；商品 {summary['n_products']} 个",
        "",
        quality_text,
    ]
    metrics = [
        f"- 总销售额：¥{summary['total_amount']:,.0f}",
        f"- 总销量：{summary['total_quantity']:,.0f} 件",
        f"- 平均客单价：¥{summary['total_amount'] / max(summary['order_rows'], 1):,.2f}",
    ]
    products = ["| 商品 | 销量 | 销售额 | 均价 |", "|---|---|---|---|"]
    for r in top_products.head(10).itertuples():
        avg = f"¥{r.avg_price:,.1f}" if pd.notna(r.avg_price) else "—"
        products.append(f"| {r.product_name} | {r.quantity:,.0f} | ¥{r.amount:,.0f} | {avg} |")

    sections: list[tuple[str, list[str]]] = [
        ("数据范围与质量", scope),
        ("核心经营指标", metrics),
        ("商品表现 Top 10", products),
    ]

    if categories is not None and not categories.empty:
        body = ["| 品类 | 销量 | 销售额 |", "|---|---|---|"]
        for r in categories.itertuples():
            body.append(f"| {r.category} | {r.quantity:,.0f} | ¥{r.amount:,.0f} |")
        sections.append(("品类表现", body))

    if channels is not None and not channels.empty:
        body = ["| 渠道 | 销量 | 销售额 |", "|---|---|---|"]
        for r in channels.itertuples():
            body.append(f"| {r.channel} | {r.quantity:,.0f} | ¥{r.amount:,.0f} |")
        sections.append(("渠道表现", body))

    if coverage is not None and not coverage.empty:
        body = ["| 商品 | 当前库存 | 覆盖天数 | 状态 |", "|---|---|---|---|"]
        for r in coverage.itertuples():
            cd = f"{r.coverage_days:,.1f}" if pd.notna(r.coverage_days) else "—"
            body.append(f"| {r.product_name} | {r.stock:,.0f} | {cd} | {analytics.classify_coverage(r.coverage_days)} |")
        sections.append(("库存风险", body))

    if ai_insight:
        sections.append(("AI 洞察", [ai_insight]))

    sections.append(
        (
            "数据局限与后续验证",
            [
                "- 关键指标由代码计算，AI 只负责解释，结论可追溯至统计口径。",
                "- 缺失成本、库存或历史记录时，相关结论不成立，请勿据此直接决策。",
                "- 建议结合真实凭证复核后使用。",
            ],
        )
    )

    lines = ["# 衍生品经营分析报告", "", f"> 生成时间：{pd.Timestamp.now():%Y-%m-%d %H:%M}", ""]
    for i, (title, body) in enumerate(sections, 1):
        lines += [f"## {i}. {title}", ""] + body + [""]
    return "\n".join(lines)
