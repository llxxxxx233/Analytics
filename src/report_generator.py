"""报告生成（阶段五接入）。

整合数据范围说明、指标、图表与分析文本为结构化 Markdown 报告。
MVP 阶段预留接口，后续阶段实现导出。
"""
from __future__ import annotations


def build_markdown_report(title: str, data_scope: str, sections: list[tuple[str, str]]) -> str:
    """按标题 + 各章节组装 Markdown 报告。sections 为 (章节标题, 正文) 列表。"""
    lines = [f"# {title}", "", f"> 数据范围说明：{data_scope}", ""]
    for heading, body in sections:
        lines += [f"## {heading}", "", body, ""]
    return "\n".join(lines).strip() + "\n"
