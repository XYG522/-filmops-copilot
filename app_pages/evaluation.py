# -*- coding: utf-8 -*-
"""⑤评估结果：黄金集种子快速验收 + Day 6 全量评估（120 条）结果展示。

全量评估在 CLI 跑（scripts/run_eval.py --all，约 20 分钟），本页读取
outputs/eval_result_YYYY-MM-DD.json 展示指标表与未达标明细，并可在后台触发重跑。
"""

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from app import feedback
from app.eval_check import run_golden_check
from app.ui_resources import get_retriever

ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = ROOT / "outputs"

METRIC_LABELS = {
    "retrieval_recall20": ("检索召回@20（黄金 50 必备引用）", "≥90%"),
    "retrieval_top5": ("检索 Top5（黄金 50 必备引用）", "≥80%"),
    "risk_recall": ("风险召回率", "≥90%"),
    "citation_auto": ("引用准确率（自动轨：引用后校验）", "100%"),
    "citation_judge": ("引用准确率（judge 轨：引用支持性）", "≥80%"),
    "hallucination_auto_items": ("编造引用条目数（自动轨）", "0 条"),
    "hallucination_judge": ("编造断言条目占比（judge 轨）", "≤10%"),
    "adversarial_passed": ("对抗通过率（硬门槛）", "20/20"),
    "boundary_passed": ("边界通过率", "≥27/30"),
    "regression_passed": ("回归通过率", "20/20"),
    "point_coverage": ("要点覆盖率（judge 轨）", "≥70%"),
    "must_cite_coverage": ("必备引用覆盖率", "≥90%"),
}


def _fmt(key: str, m: dict) -> str:
    v = m[key]
    if key in ("adversarial_passed", "boundary_passed", "regression_passed"):
        total_key = {"adversarial_passed": "adversarial_total",
                     "boundary_passed": "boundary_total",
                     "regression_passed": "regression_total"}[key]
        return f"{v}/{m[total_key]}"
    if key == "hallucination_auto_items":
        return f"{v} 条"
    if key == "risk_recall":
        return f"{v:.0%}（{m['risk_total']} 条）"
    return f"{v:.0%}"


def _hit(key: str, m: dict) -> bool:
    if key == "adversarial_passed":
        return m[key] >= m["adversarial_total"]
    if key == "boundary_passed":
        return m[key] >= 0.9 * m["boundary_total"]
    if key == "regression_passed":
        return m[key] >= m["regression_total"]
    if key == "hallucination_auto_items":
        return m[key] <= 0
    if key == "hallucination_judge":
        return m[key] <= 0.10
    return m[key] >= m.get("targets", {}).get(key, 0)


def _latest_result() -> dict | None:
    files = sorted(OUTPUTS.glob("eval_result_*.json"))
    if not files:
        return None
    return json.loads(files[-1].read_text(encoding="utf-8"))


st.title("⑤ 评估结果")

st.caption(
    "黄金集种子验收（Day 3 口径）：粗排 Top-20 命中目标 chunk ≥9/10 为过；"
    "Top-5 为 Rerank 质量观察。评估用固定快照，结果可复现。"
)

if "eval_result" not in st.session_state:
    st.session_state.eval_result = None

if st.button("跑黄金集种子验收", icon=":material/play_arrow:"):
    with st.spinner("10 条 × 粗排+重排…"):
        result = run_golden_check(get_retriever())
    st.session_state.eval_result = result
    feedback.log_event(
        "eval_run",
        result_summary=f"召回@20 {result['recall20']}/{result['total']}，"
                       f"Top5 含预期 {result['top5_good']}/{result['total']}",
        meta={"recall20": result["recall20"], "seconds": result["seconds"]},
    )

result = st.session_state.eval_result
if result is not None:
    m1, m2, m3 = st.columns(3)
    m1.metric("召回@20", f"{result['recall20']}/{result['total']}",
              delta="达标" if result["recall20"] >= result["total"] * 0.9 else "未达标")
    m2.metric("Top-5 含预期", f"{result['top5_good']}/{result['total']}")
    m3.metric("耗时", f"{result['seconds']}s")

    st.dataframe(pd.DataFrame([{
        "查询": r["query"],
        "预期条目": "、".join(r["expected"]),
        "Top-20 命中": "✓" if r["ok20"] else "✗",
        "Top-5 含预期": "✓" if r["ok5"] else "✗",
    } for r in result["results"]]))
else:
    st.info("点击上方按钮跑种子验收（仅检索，不消耗 LLM）。")

# ---- Day 6 全量评估 ----

st.divider()
st.subheader("Day 6 全量评估（120 条：黄金 50 / 边界 30 / 对抗 20 / 回归 20）")
st.caption("全量跑分在 CLI 执行：`scripts/run_eval.py --all`；judge 为 deepseek-v4-pro 判 "
           "deepseek-flash（模型错开），结论为样本内表现，需人工抽查。")

c1, c2 = st.columns(2)
if c1.button("后台重跑全量评估（约 20 分钟）", icon=":material/play_arrow:"):
    log = OUTPUTS / "eval_full.log"
    subprocess.Popen(
        [sys.executable, str(ROOT / "scripts" / "run_eval.py"), "--all"],
        cwd=ROOT,
        stdout=log.open("w", encoding="utf-8"),
        stderr=subprocess.STDOUT,
    )
    st.success(f"已在后台启动（日志：{log}）。完成后点右侧「刷新结果」。")
if c2.button("刷新结果", icon=":material/refresh:"):
    st.rerun()

data = _latest_result()
if data is None:
    st.info("暂无全量评估结果：可点击上方按钮后台重跑，或跑种子验收先看检索质量。")
else:
    m = data["metrics"]
    u = data["usage_total"]
    st.dataframe(pd.DataFrame([{
        "指标": label,
        "结果": _fmt(key, m),
        "目标": target,
        "达标": "✓" if _hit(key, m) else "✗ 未达标",
    } for key, (label, target) in METRIC_LABELS.items()]))
    st.caption(f"评估日期 {data['date']} | LLM 调用 {u['calls']} 次 | "
               f"输入 {u['prompt_tokens']} tok | 输出 {u['completion_tokens']} tok")

    fails = data.get("failed_items", {})
    if any(fails.values()):
        st.subheader("未达标明细")
        for name, items in fails.items():
            if not items:
                continue
            with st.expander(f"{name}（{len(items)} 条未过）"):
                for it in items:
                    st.markdown(f"- **{it['id']}**：{str(it.get('detail') or '')[:300]}")
    else:
        st.success("全部指标达标。")

st.divider()
st.subheader("反馈 / 审计日志（SQLite）")
st.caption("每次查询、生成、编辑采纳、导出都落库；既是评估数据源，也是审计日志。")

if st.button("刷新日志", icon=":material/refresh:"):
    st.rerun()

rows = feedback.recent(50)
if rows:
    st.dataframe(pd.DataFrame([{
        "时间": r["ts"], "类型": r["kind"], "查询": r["query"][:40],
        "摘要": r["result_summary"][:60], "采纳状态": r["decision"] or "-",
    } for r in rows]))
else:
    st.info("暂无事件记录")
st.caption(f"事件类型计数：{feedback.stats()}")
