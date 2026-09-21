# -*- coding: utf-8 -*-
"""
Day 3 CLI：混合检索 + Rerank 的验收与调试。

用法：
  python scripts/search_cli.py "哪个任务延期了"    # 单条查询（Top-5 + 引用）
  python scripts/search_cli.py --check             # 跑 data/eval/golden_seed.json 全量验收

验收口径（docs/phase9-demo-plan.md Day 3）：
  检索召回率@20：粗排 Top-20 命中目标 chunk ≥ 9/10
  Top-5 为 Rerank 后质量观察（正式重排准确率指标 Day 6 评估脚本算）。
"""

import argparse
import json
import sys
import time
from pathlib import Path

try:  # Windows 终端统一 UTF-8 输出
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.retriever import HybridRetriever  # noqa: E402

GOLDEN_SEED = Path(__file__).resolve().parent.parent / "data" / "eval" / "golden_seed.json"


def _entries_of(chunk_id: str, inventory: dict) -> set:
    meta = inventory[chunk_id]["metadata"]
    return set(meta["entry_ids"].split("、"))


def show_hits(query: str, hits: list[dict]) -> None:
    print(f"Q: {query}")
    for i, h in enumerate(hits, start=1):
        c = h["citation"]
        print(f"  {i}. [{c['source_file']} | {c['location']} | 部门={c['department'] or '-'} | "
              f"日期={c['date'] or '-'}] score={h['score']}")
        print(f"     {h['text'][:58]}...")


def check_mode() -> None:
    data = json.loads(GOLDEN_SEED.read_text(encoding="utf-8"))
    retriever = HybridRetriever()
    inv = retriever.inventory
    passed, top5_good = 0, 0
    print(f"验收集: {len(data)} 条\n")
    t0 = time.perf_counter()
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

        passed += ok20
        top5_good += ok5
        print(f"  [{'✓' if ok20 else '✗'}] Top20{'✓' if ok20 else '✗'} / Top5{'✓' if ok5 else '✗'}  "
              f"{query}")
        if not ok20:
            print(f"        预期: {sorted(expected)}")

    print(f"\n召回@20: {passed}/{len(data)}（验收线 ≥9/10）  Top-5 含预期: {top5_good}/{len(data)}")
    print(f"耗时 {time.perf_counter() - t0:.1f}s")


def main() -> None:
    ap = argparse.ArgumentParser(description="FilmOps 混合检索 CLI")
    ap.add_argument("query", nargs="?", help="单条查询")
    ap.add_argument("--check", action="store_true", help="跑验收集（golden_seed.json）")
    args = ap.parse_args()

    if args.check:
        check_mode()
    elif args.query:
        retriever = HybridRetriever()
        show_hits(args.query, retriever.retrieve(args.query))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
