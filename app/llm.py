# -*- coding: utf-8 -*-
"""DeepSeek 生成客户端（OpenAI 兼容接口）。

- 主模型 deepseek-flash 跑周报/风险/行动项生成；deepseek-v4-pro 留给 Day 6 LLM-as-judge
- chat() 返回 (content, usage)，usage 累积用于 Day 7 成本实测
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# 显式加载项目根目录的 .env（不依赖 cwd）
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
MAIN_MODEL = os.getenv("DEEPSEEK_MAIN_MODEL", "deepseek-flash")
PRO_MODEL = os.getenv("DEEPSEEK_PRO_MODEL", "deepseek-v4-pro")


class ConfigError(RuntimeError):
    """缺少 API Key 等配置错误。"""


def _require_key() -> str:
    if not API_KEY:
        raise ConfigError(
            "未找到 DEEPSEEK_API_KEY：请复制 .env.example 为 .env 并填入 DeepSeek API Key"
        )
    return API_KEY


def _looks_truncated(content: str) -> bool:
    """回答疑似被 max_tokens 截断：非句末标点收尾，或末行表格列数少于表头。"""
    s = content.strip()
    if not s:
        return False
    if s[-1] in "。！？；…":
        return False
    lines = s.split("\n")
    if "|" in lines[-1]:  # 以表格行收尾：列数不足表头视为截断（完整行与表头列数相同）
        header = next((ln for ln in lines if ln.lstrip().startswith("|")), "")
        if header:
            return len(lines[-1].split("|")) < len(header.split("|"))
    return True


def chat(messages: list[dict], model: str = MAIN_MODEL,
         temperature: float = 0.2, max_tokens: int = 4096) -> tuple[str, dict]:
    """单轮对话，返回 (content, usage)。失败抛 RuntimeError（附 API 错误）。

    deepseek-flash 是推理模型，思考也消耗 max_tokens 预算；content 为空或
    疑似被截断（句末无标点/表格缺列）时视为预算吃满，翻倍预算重试，
    最多 3 次调用、上限 32768 tok（G11 曾翻倍一次仍为空——偶发形态）。
    usage 累计所有尝试（成本实测口径）。
    """
    client = OpenAI(base_url=BASE_URL, api_key=_require_key())

    def _call(mt: int):
        return client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=mt,
        )

    resp = _call(max_tokens)
    content = resp.choices[0].message.content or ""
    usage = {
        "prompt_tokens": resp.usage.prompt_tokens,
        "completion_tokens": resp.usage.completion_tokens,
        "calls": 1,
    }
    while (not content or _looks_truncated(content)) \
            and max_tokens < 32768 and usage["calls"] < 3:
        max_tokens *= 2
        resp = _call(max_tokens)
        content = resp.choices[0].message.content or ""
        usage["prompt_tokens"] += resp.usage.prompt_tokens
        usage["completion_tokens"] += resp.usage.completion_tokens
        usage["calls"] += 1
    return content, usage
