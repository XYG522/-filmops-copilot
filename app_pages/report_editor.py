# -*- coding: utf-8 -*-
"""④周报生成 + 人工编辑确认（MVP 功能表 #8，PM 能力展示重点）。

流程：数据清点 → LLM 规划检索查询与章节 → 混合检索 → 风险/行动项 JSON → Markdown
→ 文本框编辑 → 采纳（原样）/ 采纳（修改后）/ 忽略 → 导出 Markdown → 全部事件写 SQLite。

数据范围默认「仅上传数据」（manifest 注册源），可切「全部数据源」（含内置合成数据）。
"""

import time
from datetime import date

import pandas as pd
import streamlit as st

from app import feedback
from app.generator import generate_report_from_data
from app.ingest import load_manifest
from app.ui_resources import get_retriever

st.title("④ 周报生成 · 人工编辑确认")

st.caption(
    "草稿由数据驱动生成：先清点数据源，再由 LLM 制定检索查询与章节结构；"
    "低置信度/高风险条目已路由转人工。编辑确认后的事件（采纳/修改/忽略）写入 SQLite，"
    "作为评估数据源与审计日志。"
)

if "report" not in st.session_state:
    st.session_state.report = None

with st.form("gen_form"):
    scope = st.radio(
        "数据范围",
        options=("仅上传数据", "全部数据源"),
        index=0,
        help="仅上传数据 = manifest 注册的上传源；全部数据源 = 含内置合成数据",
        horizontal=True,
    )
    st.markdown("生成数据驱动周报草稿（约 1–2 分钟：数据清点 + 检索规划 + 3 次 LLM 调用）")
    go = st.form_submit_button("生成周报草稿", icon=":material/auto_awesome:")

if go:
    whitelist = {m["file"] for m in load_manifest()} if scope == "仅上传数据" else None
    with st.status("生成中…", expanded=True) as status:
        st.write("清点数据源 → LLM 规划检索计划 → 混合检索 + Rerank → 生成…")
        t0 = time.perf_counter()
        res = generate_report_from_data(get_retriever(), source_whitelist=whitelist)
        status.update(label=f"完成（{time.perf_counter() - t0:.0f}s）", state="complete")
    if res.get("error"):
        # 范围空/检索空：保留上一次草稿，不覆盖 session_state
        st.error(f"{res['error']}\n\n（已保留上一次草稿；可切换数据范围，"
                 f"或先到 ①导入页上传数据后重建索引。）")
    else:
        st.session_state.report = res
        st.session_state.draft_editor = res["markdown"]
        feedback.log_event(
            "generate",
            result_summary=f"{len(res['risks'])} 风险 / {len(res['actions'])} 行动项",
            meta={
                "usage": res["usage"],
                "citation_ok": res["citation_check"]["ok"],
                "invalid_refs": res["citation_check"]["invalid"],
                "scope": scope,
                "planner": res["plan"]["source"],
                "project_name": res["plan"]["project_name"],
            },
        )

res = st.session_state.report
if res is None:
    st.info("点击上方按钮生成周报草稿。")
    st.stop()

m1, m2, m3 = st.columns(3)
m1.metric("风险", len(res["risks"]))
m2.metric("行动项", len(res["actions"]))
m3.metric("引用后校验", "通过" if res["citation_check"]["ok"] else "未通过")

with st.expander("检索计划（LLM 按数据源制定）"):
    plan = res.get("plan", {})
    st.markdown(
        f"- 项目名：**{plan.get('project_name', '-')}** · 计划来源："
        f"{'LLM 规划' if plan.get('source') == 'llm' else '确定性兜底'}"
    )
    st.markdown("**检索查询**")
    for q in plan.get("queries", []):
        st.markdown(f"- {q}")
    st.markdown("**章节结构**")
    for s in plan.get("sections", []):
        st.markdown(f"- **{s['title']}** — {s['description']}")


def _reset_draft() -> None:
    """恢复原稿（on_click 在脚本体之前执行，允许写 widget 状态）。"""
    st.session_state.draft_editor = st.session_state.report["markdown"]


def _decision(original: str) -> str:
    return "adopt" if st.session_state.draft_editor.strip() == original.strip() else "modify"


st.subheader("草稿编辑")
draft = st.text_area(
    "草稿（可直接编辑；采纳时会记录「原样采纳 / 修改后采纳」）",
    key="draft_editor",
    height=480,
)

with st.container(horizontal=True):
    adopt = st.button("采纳并记录", type="primary", icon=":material/check:")
    ignore = st.button("忽略本次草稿", icon=":material/close:")
    st.button("恢复原稿", icon=":material/undo:", on_click=_reset_draft)
    dl = st.download_button(
        "导出 Markdown",
        data=st.session_state.draft_editor,
        file_name=f"weekly_report_{date.today():%Y-%m-%d}.md",
        mime="text/markdown",
        icon=":material/download:",
    )

if adopt:
    decision = _decision(res["markdown"])
    feedback.log_event(
        "edit_decision", decision=decision,
        result_summary=f"采纳周报草稿（{len(st.session_state.draft_editor)} 字）",
        meta={"risks": len(res["risks"]), "actions": len(res["actions"])},
    )
    st.toast(f"已记录：{'原样采纳' if decision == 'adopt' else '修改后采纳'}")
if ignore:
    feedback.log_event(
        "edit_decision", decision="ignore",
        result_summary="忽略本次草稿",
        meta={"risks": len(res["risks"]), "actions": len(res["actions"])},
    )
    st.toast("已记录：忽略本次草稿")
if dl:
    feedback.log_event("export", result_summary="导出 Markdown")

st.caption("PDF 导出走浏览器打印（Ctrl+P），不单独投入排版（demo 口径）。")

with st.expander("风险清单（引用后校验 + 转人工路由）"):
    st.dataframe(pd.DataFrame([{
        "类型": r["type"], "风险": r["title"], "置信度": r["confidence"],
        "引用": "、".join(r["citations"]) or "无",
        "转人工": f"是 → {r['routing']}" if r["needs_human"] else "否",
        "标记": r.get("flag", ""),
    } for r in res["risks"]]))

with st.expander("行动项（提取 + 置信度）"):
    st.dataframe(pd.DataFrame([{
        "行动": a["action"], "负责人": a["owner"], "截止": a["due_date"],
        "置信度": a["confidence"], "引用": "、".join(a["citations"]) or "无",
    } for a in res["actions"]]))

with st.expander("引用后校验明细"):
    cc = res["citation_check"]
    st.markdown(
        f"- 上下文 {cc['context_chunks']} 块 · 使用编号 {cc['used']} · "
        f"无效编号 {cc['invalid'] or '无'} → {'通过' if cc['ok'] else '未通过'}"
    )
    st.markdown(f"- LLM 消耗：{res['usage']}")
