"""大语言模型服务（OpenAI 兼容接口）。

关键原则：AI 只解释 analytics 已经算好的数字，不自行产出关键指标。
"""
from __future__ import annotations

import httpx
from openai import OpenAI

import config

INSIGHT_SYSTEM_PROMPT = (
    "你是二次元 IP 衍生品经营分析助手。你只能依据用户消息中提供的经营数据回答。\n"
    "要求：\n"
    "1. 所有数字必须来自给定数据，不得编造、不得估计出数据里没有的数字；\n"
    "2. 先给出结论，再给出依据（引用具体数字）；\n"
    "3. 数据不足时明确说明缺什么、会影响哪个结论，而不是硬给答案；\n"
    "4. 避免因果过度推断：销量差异只说明可观测表现不同，不证明某种设计或渠道必然导致销量变化；\n"
    "5. 建议要具体、可执行，并说明依据。"
)

MARKETING_SYSTEM_PROMPT = (
    "你是二次元 IP 衍生品运营的文案策划。根据给定商品数据撰写营销话术。\n"
    "要求：\n"
    "1. 只使用数据中已有的事实（商品名、IP、品类、销量、价格等），不虚构工艺、材质、库存、优惠等信息；\n"
    "2. 给出 2~3 种风格的短文案（如朋友圈种草、商品详情、社群推广），并标注适用场景；\n"
    "3. 语气贴合二次元同人周边受众，自然不生硬。"
)


def get_client() -> OpenAI | None:
    if not config.LLM_API_KEY:
        return None
    kwargs = {"api_key": config.LLM_API_KEY}
    if config.LLM_BASE_URL:
        kwargs["base_url"] = config.LLM_BASE_URL
    # 国内服务（如 DeepSeek）直连，绕过系统代理，避免 Clash 等代理导致 TLS 握手失败
    kwargs["http_client"] = httpx.Client(trust_env=False)
    return OpenAI(**kwargs)


def _chat(system: str, user: str, temperature: float = 0.3) -> str:
    client = get_client()
    if client is None:
        raise RuntimeError("未配置 LLM_API_KEY，请先在 .env 中配置")
    if not config.LLM_MODEL:
        raise RuntimeError("未配置 LLM_MODEL，请在 .env 中填写模型名称")
    resp = client.chat.completions.create(
        model=config.LLM_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
    )
    return resp.choices[0].message.content or ""


def answer_question(question: str, context: str) -> str:
    """基于计算结果回答经营问题（结论 + 依据 + 建议）。"""
    return _chat(INSIGHT_SYSTEM_PROMPT, f"经营数据：\n{context}\n\n问题：{question}", temperature=0.2)


def generate_marketing_copy(product_name: str, product_context: str) -> str:
    """为指定商品生成营销话术。"""
    return _chat(
        MARKETING_SYSTEM_PROMPT,
        f"商品数据：\n{product_context}\n\n请为商品「{product_name}」撰写营销话术。",
        temperature=0.6,
    )
