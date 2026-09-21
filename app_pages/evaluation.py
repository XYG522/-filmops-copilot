# -*- coding: utf-8 -*-
"""⑤评估结果：黄金集种子验收（召回@20 / Top-5 含预期）+ 反馈审计日志。

Day 6 将扩展为 120 条全量评估（黄金 50 / 边界 30 / 对抗 20 / 回归 20），
本页先跑 Day 3 口径的种子验收，保证链路可复现。
"""

import pandas as pd
import streamlit as st

from app import feedback
from app.eval_check import run_golden_check
from app.ui_resources import get_retriever

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
if result is None:
    st.info("点击上方按钮跑验收（仅检索，不消耗 LLM）。")
    st.stop()

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
st.caption("结论口径：样本内表现（10 条种子），非统计显著结论；Day 6 收口 120 条后给完整指标表。")

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
