# -*- coding: utf-8 -*-
"""
BGE-M3 Embedding 与 BGE Reranker v2-m3 的 SiliconFlow（硅基流动）API 客户端。

- Embedding 走 OpenAI 兼容接口 /v1/embeddings（用 openai SDK）
- Rerank 走 Jina 风格接口 /v1/rerank（openai SDK 不支持，用 httpx）
- 配置见 .env.example（SILICONFLOW_* 组）

参考文档：
  - Rerank: https://docs.siliconflow.cn/docs/api/rerank-post
  - 模型广场: https://siliconflow.cn/models
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from openai import OpenAI

# 显式加载项目根目录的 .env（不依赖 cwd）
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BASE_URL = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
API_KEY = os.getenv("SILICONFLOW_API_KEY", "")
EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-m3")
RERANK_MODEL = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")

# SiliconFlow 建议 bge-m3 单批 ≤ 25 条
EMBED_BATCH_SIZE = 25


class ConfigError(RuntimeError):
    """缺少 API Key 等配置错误。"""


def _require_key() -> str:
    if not API_KEY:
        raise ConfigError(
            "未找到 SILICONFLOW_API_KEY：请复制 .env.example 为 .env 并填入硅基流动 API Key"
        )
    return API_KEY


def embed_texts(texts: list[str]) -> list[list[float]]:
    """批量向量化，自动按 25 条分批。返回与输入同序的 1024 维向量列表。"""
    key = _require_key()
    client = OpenAI(base_url=BASE_URL, api_key=key)
    vectors: list[list[float]] = []
    for i in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[i : i + EMBED_BATCH_SIZE]
        resp = client.embeddings.create(model=EMBED_MODEL, input=batch)
        ordered = sorted(resp.data, key=lambda d: d.index)  # 按 index 还原输入顺序
        vectors.extend([d.embedding for d in ordered])
    return vectors


def rerank(query: str, documents: list[str], top_n: int = 5) -> list[dict]:
    """重排：返回按相关性分数降序的 [{index, relevance_score, text}, ...]（最多 top_n 条）。"""
    key = _require_key()
    payload = {
        "model": RERANK_MODEL,
        "query": query,
        "documents": documents,
        "top_n": top_n,
        "return_documents": True,
    }
    resp = httpx.post(
        f"{BASE_URL}/rerank",
        json=payload,
        headers={"Authorization": f"Bearer {key}"},
        timeout=30,
    )
    resp.raise_for_status()
    results = resp.json()["results"]
    return [
        {
            "index": r["index"],
            "relevance_score": r["relevance_score"],
            "text": r.get("document", {}).get("text", ""),
        }
        for r in results
    ]
