"""
配置管理模块 — 支持环境变量 & 运行时界面输入
"""

import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()


# ---------- 默认配置 ----------
DEFAULT_CONFIG = {
    "llm_model": "qwen-plus",
    "embedding_model": "text-embedding-v3",
    "temperature": 0.3,
    "max_tokens": 1024,
    "chunk_size": 500,
    "chunk_overlap": 50,
    "retrieve_k": 4,
    "brief_mode": False,
    "kb_mode": "hybrid",  # strict | hybrid | off
}

SUPPORTED_LLM_MODELS = {
    "qwen-turbo": "快速响应，适合简单问答",
    "qwen-plus": "平衡速度与质量（推荐）",
    "qwen-max": "最强推理能力，适合复杂问题",
}


def get_api_key() -> str:
    """获取 API Key：优先 session_state 中用户输入的，其次环境变量"""
    if "runtime_api_key" in st.session_state and st.session_state["runtime_api_key"]:
        return st.session_state["runtime_api_key"]
    return os.getenv("DASHSCOPE_API_KEY", "")


def has_api_key() -> bool:
    key = get_api_key()
    return bool(key) and key != "your_api_key_here"


def get_config(key: str, default=None):
    """获取配置项：优先 session_state 运行时配置，其次环境变量，最后默认值"""
    # 1. session_state 运行时覆盖
    config_key = f"cfg_{key}"
    if config_key in st.session_state:
        return st.session_state[config_key]
    # 2. 环境变量
    env_key = key.upper()
    env_val = os.getenv(env_key)
    if env_val is not None:
        return env_val
    # 3. 默认值
    return DEFAULT_CONFIG.get(key, default)


def set_config(key: str, value):
    """在运行时设置配置项"""
    st.session_state[f"cfg_{key}"] = value
