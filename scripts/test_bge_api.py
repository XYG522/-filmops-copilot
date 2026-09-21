# -*- coding: utf-8 -*-
"""
BGE API 连通性自检：验证 .env 配置正确、测 embedding 维度与 rerank 排序效果。

用法：
  python scripts/test_bge_api.py
"""

import sys
import time
from pathlib import Path

try:  # Windows 终端统一 UTF-8 输出
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.bge_client import ConfigError, embed_texts, rerank  # noqa: E402

DEMO_QUERY = "哪个任务延期了"
DEMO_DOCS = [
    "第 13-16 集特效合成：外包方反馈初版提交延迟一周，预计 10-05 交付",
    "拍摄杀青：已完成",
    "官方微博内容日历：进行中",
    "预告片剪辑：需使用第 14 集特效镜头，9-24 交片",
    "杀青宴：未开始",
]


def main() -> None:
    try:
        # 1. Embedding：5 条文档向量化
        t0 = time.perf_counter()
        vectors = embed_texts(DEMO_DOCS)
        t_embed = time.perf_counter() - t0
        print(f"[1/2] embedding OK: {len(vectors)} 条 × {len(vectors[0])} 维, 耗时 {t_embed:.1f}s")

        # 2. Rerank：query 对 5 条文档重排，取 top-3
        t0 = time.perf_counter()
        top = rerank(DEMO_QUERY, DEMO_DOCS, top_n=3)
        t_rerank = time.perf_counter() - t0
        print(f"[2/2] rerank OK: 耗时 {t_rerank:.1f}s")
        for r in top:
            print(f"  score={r['relevance_score']:.4f}  #{r['index']}  {r['text'][:40]}")

        # 预期：#0（特效延期）应排第一
        print("\n[预期] #0 特效延期文档应得分最高")
    except ConfigError as e:
        print(f"[SKIP] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
