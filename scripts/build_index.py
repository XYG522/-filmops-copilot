# -*- coding: utf-8 -*-
"""
Day 2 CLI：解析 → 清洗去重 → 切块 → 建索引 → 冒烟检索。

验收标准（docs/phase9-demo-plan.md Day 2）：
  "哪个任务延期了" 能命中 P-005 所在 chunk，且元数据含 文件/行号/日期/部门。

用法：
  python scripts/build_index.py
"""

import sys
import time
from collections import Counter
from pathlib import Path

try:  # Windows 终端统一 UTF-8 输出
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.chunker import chunk_entries  # noqa: E402
from app.indexer import build_index, query_top  # noqa: E402
from app.parsers import dedup, parse_chat, parse_excel, parse_meeting  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

SMOKE_QUERIES = [
    "哪个任务延期了",
    "预告片什么时候交片",
    "品牌 A 的露出情况",
]


def main() -> None:
    t0 = time.perf_counter()

    # [1/4] 解析
    entries = []
    entries += parse_excel(DATA_DIR / "01_schedule.xlsx", "schedule")
    entries += parse_excel(DATA_DIR / "02_budget.xlsx", "budget")
    entries += parse_excel(DATA_DIR / "03_promo_materials.xlsx", "promo", default_dept="宣发部")
    entries += parse_chat(DATA_DIR / "04_chat_log.txt")
    entries += parse_meeting(DATA_DIR / "05_meeting_notes.txt")
    n_raw = len(entries)
    entries = dedup(entries)
    print(f"[1/4] 解析 {n_raw} 条 → 去重后 {len(entries)} 条")

    # [2/4] 切块
    chunks = chunk_entries(entries)
    stat = Counter(c.chunk_type for c in chunks)
    print(f"[2/4] 切块 {len(chunks)} 个: " + ", ".join(f"{k}={v}" for k, v in stat.items()))

    # [3/4] 建索引
    collection = build_index(chunks)
    print(f"[3/4] 索引完成: {len(chunks)} chunks, "
          f"embedding={collection.metadata.get('embedding_model')}")

    # [4/4] 冒烟检索
    print("[4/4] 冒烟检索:")
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
