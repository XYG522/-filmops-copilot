# -*- coding: utf-8 -*-
"""
Day 2 CLI：解析 → 清洗去重 → 切块 → 建索引 → 冒烟检索。

验收标准（Day 2）：
  "哪个任务延期了" 能命中 P-005 所在 chunk，且元数据含 文件/行号/日期/部门。

用法：
  python scripts/build_index.py
"""

import sys
import time
from pathlib import Path

try:  # Windows 终端统一 UTF-8 输出
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ingest import ingest_all  # noqa: E402
from app.indexer import query_top  # noqa: E402

SMOKE_QUERIES = [
    "哪个任务延期了",
    "预告片什么时候交片",
    "品牌 A 的露出情况",
]


def main() -> None:
    t0 = time.perf_counter()

    # [1-3/4] 解析 → 去重 → 切块 → 建索引（app/ingest.py 与 Day 5 UI 共用）
    stats = ingest_all()
    print(f"[1/4] 解析 {stats['raw']} 条 → 去重后 {stats['entries']} 条")
    print(f"[2/4] 切块 {stats['chunks']} 个: {stats['chunk_types']}")
    print(f"[3/4] 索引完成: {stats['chunks']} chunks, embedding={stats['embedding_model']}")

    # [4/4] 冒烟检索
    print("[4/4] 冒烟检索:")
    collection = None
    from app.indexer import load_collection  # noqa: E402
    collection = load_collection()
    for q in SMOKE_QUERIES:
        hits = query_top(collection, q, top_k=3)
        print(f"\n  Q: {q}")
        for h in hits:
            m = h["meta"]
            print(f"    - [{m['source_file']} | {m['location']} | "
                  f"部门={m['department'] or '-'} | 日期={m['date'] or '-'}] dist={h['distance']:.3f}")
            print(f"      {h['text'][:66]}...")

    print(f"\n总耗时 {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()
