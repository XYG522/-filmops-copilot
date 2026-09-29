# -*- coding: utf-8 -*-
"""
Day 3 CLI：混合检索 + Rerank 的验收与调试。

用法：
  python scripts/search_cli.py "哪个任务延期了"    # 单条查询（Top-5 + 引用）
  python scripts/search_cli.py --check             # 跑 data/eval/golden_seed.json 全量验收

验收口径（Day 3）：
  检索召回率@20：粗排 Top-20 命中目标 chunk ≥ 9/10
  Top-5 为 Rerank 后质量观察（正式重排准确率指标 Day 6 评估脚本算）。
"""

import argparse
import sys
from pathlib import Path

try:  # Windows 终端统一 UTF-8 输出
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.eval_check import run_golden_check  # noqa: E402
from app.retriever import HybridRetriever  # noqa: E402


def show_hits(query: str, hits: list[dict]) -> None:
    print(f"Q: {query}")
    for i, h in enumerate(hits, start=1):
        c = h["citation"]
        print(f"  {i}. [{c['source_file']} | {c['location']} | 部门={c['department'] or '-'} | "
              f"日期={c['date'] or '-'}] score={h['score']}")
        print(f"     {h['text'][:58]}...")


def check_mode() -> None:
    res = run_golden_check()
    print(f"验收集: {res['total']} 条\n")
    for r in res["results"]:
        print(f"  [{'✓' if r['ok20'] else '✗'}] Top20{'✓' if r['ok20'] else '✗'} / "
              f"Top5{'✓' if r['ok5'] else '✗'}  {r['query']}")
        if not r["ok20"]:
            print(f"        预期: {r['expected']}")

    print(f"\n召回@20: {res['recall20']}/{res['total']}（验收线 ≥9/10）  "
          f"Top-5 含预期: {res['top5_good']}/{res['total']}")
    print(f"耗时 {res['seconds']}s")


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
