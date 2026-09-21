# -*- coding: utf-8 -*-
"""②索引管理：索引统计 / 重建索引 / 只读筛选工具 list_entries（Day 4 工具的 UI 入口）。"""

import time
from collections import Counter

import pandas as pd
import streamlit as st

from app import feedback, ingest
from app.generator import list_entries
from app.ui_resources import get_retriever, invalidate_retriever

st.title("② 索引管理")

retriever = get_retriever()
inv = retriever.inventory  # {chunk_id: chunk_dict}
chunks = list(inv.values())
depts = Counter(c["metadata"]["department"] for c in chunks)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Chunk 数", len(chunks))
c2.metric("来源文件数", len({c["metadata"]["source_file"] for c in chunks}))
c3.metric("部门数", sum(1 for k, v in depts.items() if k))
c4.metric("无部门 chunk", depts.get("", 0))

with st.expander("分布明细"):
    st.markdown(f"- 部门：{dict(depts)}")
    st.markdown(f"- 文档类型：{dict(Counter(c['metadata']['doc_type'] for c in chunks))}")
    st.markdown(f"- 切块类型：{dict(Counter(c['metadata']['chunk_type'] for c in chunks))}")

st.divider()

# ---- 重建索引 ----
if st.button("重建索引（解析全部数据源 → 切块 → Embedding → 建索引）",
             icon=":material/build:"):
    try:
        t0 = time.perf_counter()
        with st.status("重建索引中…", expanded=True) as status:
            st.write("解析标准 5 文件 + 已注册数据源…")
            stats = ingest.ingest_all()
            status.update(
                label=f"完成：{stats['chunks']} chunks / {stats['entries']} 条 "
                      f"（embedding={stats['embedding_model']}，{time.perf_counter() - t0:.0f}s）",
                state="complete",
            )
        invalidate_retriever()
        feedback.log_event("rebuild", result_summary=f"{stats['chunks']} chunks", meta=stats)
        st.success("索引已重建，检索器缓存已刷新")
        st.rerun()
    except Exception as e:
        st.error(f"重建失败：{e}")
        feedback.log_event("rebuild", result_summary=f"失败: {e}")

st.divider()

# ---- 只读筛选工具 list_entries（越权对抗的靶子：这里只有只读，没有写通道） ----
st.subheader("只读筛选工具 list_entries")
st.caption("按部门/日期过滤台账条目（唯一工具；本 Demo 无任何写操作入口）")

with st.form("filter_entries"):
    dept = st.selectbox("部门", [""] + sorted(k for k in depts if k))
    date_from = st.date_input("开始日期（含）", value=None)
    date_to = st.date_input("结束日期（含）", value=None)
    submitted = st.form_submit_button("筛选", icon=":material/filter_alt:")
if submitted:
    rows = list_entries(
        chunks,
        dept=dept,
        date_from=date_from.isoformat() if date_from else "",
        date_to=date_to.isoformat() if date_to else "",
    )
    if rows:
        st.dataframe(
            pd.DataFrame([{
                "引用": r["ref_id"], "日期": r["date"] or "-",
                "部门": r["department"] or "-", "内容": r["text"][:60],
            } for r in rows]),
        )
    else:
        st.info("无匹配条目")

st.divider()
st.subheader("Chunk 台账")
with st.expander("查看全部 chunk（引用溯源的底账）"):
    st.dataframe(pd.DataFrame([{
        "chunk_id": c["chunk_id"],
        "来源": c["metadata"]["source_file"],
        "位置": c["metadata"]["location"],
        "日期": c["metadata"]["date"] or "-",
        "部门": c["metadata"]["department"] or "-",
        "内容": c["text"][:80],
    } for c in chunks]))
