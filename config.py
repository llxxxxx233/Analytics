"""应用配置：路径与运行参数。"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SAMPLE_DIR = DATA_DIR / "sample"
OUTPUT_DIR = BASE_DIR / "outputs"

for _d in (DATA_DIR, SAMPLE_DIR, OUTPUT_DIR):
    _d.mkdir(parents=True, exist_ok=True)

load_dotenv(BASE_DIR / ".env")

APP_TITLE = "衍生品经营分析 Agent"
APP_SUBTITLE = "AI-Powered Merchandise Analytics & Planning Assistant"


def _secret(key: str, default: str = "") -> str:
    """读取密钥：优先环境变量（本地 .env / 部署平台），其次 Streamlit Secrets。"""
    val = os.getenv(key)
    if val:
        return val
    try:
        import streamlit as st

        return st.secrets.get(key, default) or default
    except Exception:
        return default


# 大语言模型（阶段三接入，OpenAI 兼容接口）
LLM_API_KEY = _secret("LLM_API_KEY")
LLM_BASE_URL = _secret("LLM_BASE_URL")
LLM_MODEL = _secret("LLM_MODEL")
