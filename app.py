"""Streamlit 应用入口：数据上传 → 质量检查 → 经营分析看板。"""
from __future__ import annotations

import io

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import config
from src import analytics, data_loader, data_validator, insights, report_generator

# ---- 调色板（dataviz 参考调色板 · 浅色模式）----
ACCENT = "#2a78d6"
INK = "#0b0b0b"
INK_SEC = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
SURFACE = "#fcfcfb"
STATUS = {"good": "#0ca30c", "warning": "#fab219", "serious": "#ec835a", "critical": "#d03b3b"}
FONT = 'system-ui, "Segoe UI", sans-serif'

st.set_page_config(page_title=config.APP_TITLE, layout="wide", page_icon="📊")


# ---- 数据读取 ----
def _read_upload(uploaded) -> pd.DataFrame:
    name = uploaded.name.lower()
    data = uploaded.getvalue()
    if name.endswith((".xlsx", ".xls")):
        return data_loader.standardize(pd.read_excel(io.BytesIO(data)))
    for enc in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
        try:
            return data_loader.standardize(pd.read_csv(io.BytesIO(data), encoding=enc))
        except UnicodeDecodeError:
            continue
    return data_loader.standardize(pd.read_csv(io.BytesIO(data)))


def _load_sample() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    orders = data_loader.load_orders(config.SAMPLE_DIR / "sample_orders.csv")
    products = data_loader.load_products(config.SAMPLE_DIR / "sample_products.csv")
    inventory = data_loader.load_inventory(config.SAMPLE_DIR / "sample_inventory.csv")
    return orders, products, inventory


# ---- 图表 ----
def _style(fig: go.Figure, height: int = 360) -> go.Figure:
    fig.update_layout(
        height=height,
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(family=FONT, color=INK, size=13),
        margin=dict(l=8, r=16, t=8, b=8),
        showlegend=False,
        hoverlabel=dict(bgcolor=SURFACE, font_color=INK, bordercolor=BASELINE),
    )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=BASELINE, linecolor=BASELINE, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=BASELINE, linecolor=BASELINE, tickfont=dict(color=MUTED))
    return fig


def _metric_info(metric: str) -> tuple[str, str, str]:
    """返回 (数值列, 文本格式, hover 格式)。"""
    if metric == "销售额":
        return "amount", "¥{:,.0f}", "¥%{x:,.0f}"
    return "quantity", "{:,.0f}", "%{x:,.0f} 件"


def trend_fig(df: pd.DataFrame, metric: str) -> go.Figure:
    col, _, hover = _metric_info(metric)
    fig = go.Figure(
        go.Scatter(
            x=df["order_date"],
            y=df[col],
            mode="lines",
            line=dict(color=ACCENT, width=2),
            hovertemplate=f"%{{x|%Y-%m-%d}}<br>{metric}: {hover}<extra></extra>",
        )
    )
    fig.update_layout(hovermode="x unified")
    return _style(fig)


def bar_fig(df: pd.DataFrame, x: str, y: str, text_fmt: str, hover: str, color: str = ACCENT, height: int = 360) -> go.Figure:
    fig = go.Figure(
        go.Bar(
            x=df[x],
            y=df[y],
            orientation="h",
            marker=dict(color=color),
            text=[text_fmt.format(v) for v in df[x]],
            textposition="outside",
            textfont=dict(color=INK_SEC, size=12),
            hovertemplate=f"%{{y}}<br>{hover}<extra></extra>",
            width=0.6,
        )
    )
    fig.update_yaxes(categoryorder="total ascending")
    return _style(fig, height=height)


def coverage_bucket(days: float) -> tuple[str, str, str]:
    """(状态标签, 颜色, 图标)。标签统一由 analytics.classify_coverage 给出。"""
    label = analytics.classify_coverage(days)
    color = {
        "可能缺货": STATUS["critical"],
        "正常": STATUS["good"],
        "积压风险": STATUS["serious"],
    }.get(label, MUTED)
    icon = {"可能缺货": "▲", "正常": "●", "积压风险": "▼"}.get(label, "·")
    return label, color, icon


def coverage_fig(df: pd.DataFrame) -> go.Figure:
    rows = [(r, coverage_bucket(r.coverage_days)) for r in df.itertuples()]
    plotted = [(r, b) for r, b in rows if b[2] != "·"]
    fig = go.Figure(
        go.Bar(
            x=[r.coverage_days for r, _ in plotted],
            y=[r.product_name for r, _ in plotted],
            orientation="h",
            marker=dict(color=[b[1] for _, b in plotted]),
            text=[f"{b[2]} {b[0]}" for _, b in plotted],
            textposition="outside",
            textfont=dict(color=INK_SEC, size=12),
            hovertemplate="%{y}<br>覆盖 %{x:,.0f} 天<extra></extra>",
            width=0.6,
        )
    )
    fig.update_yaxes(categoryorder="total ascending")
    return _style(fig, height=380)


# ---- AI 交互辅助 ----
def _run_ask(question: str, context: str) -> None:
    try:
        with st.spinner("分析中…"):
            st.session_state["ai_answer"] = insights.ask(question, context)
            st.session_state["ai_copy"] = ""
    except Exception as e:  # noqa: BLE001 - 错误信息展示给用户
        st.session_state["ai_answer"] = f"⚠️ 调用失败：{e}"


def _run_copy(product_name: str, product_context: str) -> None:
    try:
        with st.spinner("生成中…"):
            st.session_state["ai_copy"] = insights.marketing_copy(product_name, product_context)
            st.session_state["ai_answer"] = ""
    except Exception as e:  # noqa: BLE001
        st.session_state["ai_copy"] = f"⚠️ 调用失败：{e}"


# ---- 侧边栏：数据来源 ----
st.sidebar.title(config.APP_TITLE)
source = st.sidebar.radio("数据来源", ["示例数据", "上传数据"])

orders_file = products_file = inventory_file = None
if source == "上传数据":
    orders_file = st.sidebar.file_uploader("订单明细（必填，CSV/Excel）", type=["csv", "xlsx"])
    products_file = st.sidebar.file_uploader("商品信息（可选）", type=["csv", "xlsx"])
    inventory_file = st.sidebar.file_uploader("库存记录（可选）", type=["csv", "xlsx"])

if source == "示例数据":
    if (config.SAMPLE_DIR / "sample_orders.csv").exists() and (
        st.session_state.get("source") != "示例数据" or "orders" not in st.session_state
    ):
        st.session_state.orders, st.session_state.products, st.session_state.inventory = _load_sample()
        st.session_state.source = "示例数据"
    st.sidebar.caption("当前使用 data/sample/ 下的模拟数据")
else:
    if orders_file is not None:
        st.session_state.orders = _read_upload(orders_file)
        st.session_state.products = None
        st.session_state.inventory = None
        st.session_state.source = "上传数据"
    if products_file is not None:
        st.session_state.products = _read_upload(products_file)
    if inventory_file is not None:
        st.session_state.inventory = _read_upload(inventory_file)

orders = st.session_state.get("orders")
products = st.session_state.get("products")
inventory = st.session_state.get("inventory")

# ---- 主界面 ----
st.title(config.APP_TITLE)
st.caption(config.APP_SUBTITLE)

if orders is None:
    st.info("请先在左侧选择「示例数据」或上传订单明细文件（CSV/Excel）。")
    st.stop()

if st.session_state.get("source") == "示例数据":
    st.warning("⚠️ 当前展示的是**模拟数据**，仅用于功能演示，不代表真实经营成果。")

source_label = "模拟数据" if st.session_state.get("source") == "示例数据" else "上传数据"

# 合并商品信息（品类 / IP / 规格 / 成本）
merged = data_loader.merge_product_info(orders, products)

# 质量报告
report = data_validator.validate_orders(orders)
with st.expander("数据质量检查", expanded=not report.ok):
    st.text(report.summary())
    if report.missing_fields:
        st.error("缺少必填字段，无法进行经营分析。请补充后重新上传。")
        st.stop()

# 侧边栏：筛选
if "order_date" in merged.columns and pd.notna(merged["order_date"].min()) and pd.notna(merged["order_date"].max()):
    dmin, dmax = merged["order_date"].min(), merged["order_date"].max()
    start, end = st.sidebar.date_input(
        "日期范围",
        value=(dmin.date(), dmax.date()),
        min_value=dmin.date(),
        max_value=dmax.date(),
    )
else:
    start = end = None

categories = sorted(merged["category"].dropna().unique()) if "category" in merged.columns else []
channels = sorted(merged["channel"].dropna().unique()) if "channel" in merged.columns else []
sel_cats = st.sidebar.multiselect("品类", categories) if categories else None
sel_chans = st.sidebar.multiselect("渠道", channels) if channels else None

metric = st.sidebar.radio("主指标", ["销售额", "销量"])
freq = st.sidebar.radio("趋势粒度", ["日", "周", "月"], horizontal=True)

filtered = analytics.filter_orders(merged, start, end, sel_cats or None, sel_chans or None)
if filtered.empty:
    st.warning("当前筛选条件下没有数据。请调整日期范围或品类 / 渠道筛选。")
    st.stop()

summary = analytics.compute_summary(filtered)

# KPI 指标卡
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("总销售额", f"¥{summary['total_amount']:,.0f}")
c2.metric("总销量", f"{summary['total_quantity']:,.0f} 件")
c3.metric("订单行数", f"{summary['order_rows']:,}")
c4.metric("商品数", f"{summary['n_products']:,}")
c5.metric("统计范围", f"{summary['start_date']:%Y-%m-%d} ~ {summary['end_date']:%Y-%m-%d}")
st.caption("统计口径：以上数字由代码直接汇总，未补全缺失值。")

# 销售趋势
st.subheader("销售趋势")
st.plotly_chart(trend_fig(analytics.sales_trend(filtered, freq=freq), metric), width="stretch")

# 品类 & 渠道
col, text_fmt, hover = _metric_info(metric)
left, right = st.columns(2)
with left:
    st.subheader("品类表现")
    cat_df = analytics.sales_by_category(filtered)
    if cat_df.empty:
        st.caption("未提供品类信息，无法分析。")
    else:
        st.plotly_chart(bar_fig(cat_df.sort_values(col), col, "category", text_fmt, hover), width="stretch")
with right:
    st.subheader("渠道表现")
    chan_df = analytics.sales_by_channel(filtered)
    if chan_df.empty:
        st.caption("未提供渠道信息，无法分析。")
    else:
        st.plotly_chart(bar_fig(chan_df.sort_values(col), col, "channel", text_fmt, hover), width="stretch")

# 商品销量 Top N
st.subheader(f"商品表现 Top 10（按{metric}）")
full_prod = analytics.sales_by_product(filtered)
prod_df = full_prod.head(10)
st.plotly_chart(bar_fig(prod_df.sort_values(col), col, "product_name", text_fmt, hover), width="stretch")

# 库存覆盖（仅在有库存数据时）
cov = None
if inventory is not None and not inventory.empty and "stock" in inventory.columns:
    st.subheader("库存风险与覆盖天数")
    cov = analytics.inventory_coverage(filtered, inventory)
    if not cov.empty:
        st.plotly_chart(coverage_fig(cov), width="stretch")
        st.caption("▲ 可能缺货（<14 天）　● 正常（14–90 天）　▼ 积压风险（>90 天）。覆盖天数 = 当前库存 ÷ 日均销量，仅作参考。")
        show = cov[["product_name", "stock", "total_quantity", "avg_daily_sales", "coverage_days", "cost"]].copy()
        show["coverage_days"] = show["coverage_days"].round(1)
        show.columns = ["商品", "当前库存", "总销量", "日均销量", "覆盖天数", "成本"]
        st.dataframe(show, width="stretch", hide_index=True)
else:
    st.caption("未提供库存记录，跳过库存风险分析。")

# ---- AI 数据洞察 ----
st.divider()
st.header("🤖 AI 数据洞察")

context = insights.build_data_context(summary, full_prod, cat_df, chan_df, cov, source_label)

with st.expander("查看 AI 使用的数据上下文（先计算）"):
    st.code(context)

if not config.LLM_API_KEY:
    st.info(
        "未配置大模型 API。请在 `.env` 中填写 `LLM_API_KEY`、`LLM_MODEL`"
        "（使用兼容接口时再填 `LLM_BASE_URL`），重启应用后即可获得 AI 结论与营销话术。"
    )
else:
    st.markdown("**示例问题**（点击即问）")
    ex_cols = st.columns(3)
    for i, ex in enumerate(insights.EXAMPLE_QUESTIONS):
        if ex_cols[i % 3].button(ex, key=f"ex_{i}"):
            _run_ask(ex, context)

    question = st.text_input("或输入你的问题", placeholder="例如：下一期应该优先关注哪些商品？")
    if st.button("提问", type="primary") and question.strip():
        _run_ask(question, context)

    st.divider()
    st.subheader("📣 商品营销话术")
    product_list = full_prod["product_name"].tolist()
    sel = st.selectbox("选择商品", product_list)
    if st.button("生成营销话术", type="primary"):
        row = full_prod[full_prod["product_name"] == sel].iloc[0]
        meta = {}
        for c in ("ip", "category", "spec"):
            if c in filtered.columns:
                vals = filtered.loc[filtered["product_name"] == sel, c].dropna()
                if not vals.empty:
                    meta[c] = vals.iloc[0]
        rank = product_list.index(sel) + 1
        pc = insights.build_product_context(row, meta, rank)
        _run_copy(sel, pc)

    if st.session_state.get("ai_answer"):
        st.markdown(st.session_state["ai_answer"])
    if st.session_state.get("ai_copy"):
        st.markdown(st.session_state["ai_copy"])

# ---- 报告导出 ----
st.divider()
st.subheader("📄 导出分析报告")
report_md = report_generator.build_report(
    summary=summary,
    top_products=full_prod,
    categories=cat_df,
    channels=chan_df,
    coverage=cov,
    quality_text=report.summary(),
    source_label=source_label,
    ai_insight=st.session_state.get("ai_answer") or None,
)
st.download_button(
    "下载 Markdown 报告",
    data=report_md,
    file_name="衍生品经营分析报告.md",
    mime="text/markdown",
)

# 数据预览
with st.expander("查看原始数据"):
    st.dataframe(merged, width="stretch")
