# -*- coding: utf-8 -*-
"""黄金集种子验收（Day 3 口径）：召回@20 命中 + Top-5 含预期。

Day 3 CLI（search_cli --check）与 Day 5 评估页共用；Day 6 扩展为 120 条全量评估脚本。
验收口径（docs/phase9-demo-plan.md Day 3）：
  检索召回率@20：粗排 Top-20 命中目标 chunk ≥ 9/10
  Top-5 为 Rerank 后质量观察（正式重排准确率指标 Day 6 评估脚本算）。
"""

import json
import time
from pathlib import Path

from app.retriever import HybridRetriever

GOLDEN_SEED = Path(__file__).resolve().parent.parent / "data" / "eval" / "golden_seed.json"


def _entries_of(chunk_id: str, inventory: dict) -> set:
    meta = inventory[chunk_id]["metadata"]
    return set(meta["entry_ids"].split("、"))


def run_golden_check(retriever: HybridRetriever | None = None,
                     seed_path: Path = GOLDEN_SEED) -> dict:
    """跑全量验收，返回 {results, total, recall20, top5_good, seconds}。"""
    retriever = retriever or HybridRetriever()
    data = json.loads(seed_path.read_text(encoding="utf-8"))
    inv = retriever.inventory
    t0 = time.perf_counter()

    results = []
    for item in data:
        query, expected = item["query"], set(item["expected_entries"])

        cands = retriever.coarse_rank(query)
        coarse_entries = set()
        for cid, _ in cands:
            coarse_entries |= _entries_of(cid, inv)
        ok20 = bool(coarse_entries & expected)

        top5 = retriever.retrieve(query, cands=cands)
        top5_entries = set()
        for h in top5:
            top5_entries |= _entries_of(h["chunk_id"], inv)
        ok5 = bool(top5_entries & expected)

        results.append({
            "query": query,
            "expected": sorted(expected),
            "ok20": ok20,
            "ok5": ok5,
        })

    passed = sum(r["ok20"] for r in results)
    top5_good = sum(r["ok5"] for r in results)
    return {
        "results": results,
        "total": len(data),
        "recall20": passed,
        "top5_good": top5_good,
        "seconds": round(time.perf_counter() - t0, 1),
    }
