# -*- coding: utf-8 -*-
"""③检索调试：混合检索 + Rerank 命中与引用展示；可选单主题风险识别（消耗 LLM）。"""

import streamlit as st

from app import feedback
from app.generator import detect_risks
from app.ui_resources import get_retriever

st.title("③ 检索调试")

with st.form("search"):
    query = st.text_input("查询", placeholder="例如：哪个任务延期了 / 特效外包什么时候交付")
    final_k = st.slider("Top-K（Rerank 后送 LLM 的条数）", 1, 20, 5)
    do_risk = st.checkbox("同时做单主题风险识别（调用 LLM，慢）")
    submitted = st.form_submit_button("检索", icon=":material/search:")
if submitted and query.strip():
    retriever = get_retriever()
    with st.spinner("混合检索 + Rerank…"):
        cands = retriever.coarse_rank(query)
        hits = retriever.retrieve(query, final_k=final_k, cands=cands)
    feedback.log_event(
        "query", query=query,
        result_summary=f"Top{final_k} 命中 {len(hits)}",
        meta={"top_ref": hits[0]["citation"]["ref_id"] if hits else ""},
    )

    st.subheader(f"命中 Top-{final_k}（Rerank 后）")
    if not hits:
        st.warning("无命中 → 生成层将走「信息不足」兜底，禁止裸答")
    for h in hits:
        c = h["citation"]
        with st.container(border=True):
            st.markdown(
                f"**{c['source_file']} #{c['location']}** · 部门 `{c['department'] or '-'}` · "
                f"日期 `{c['date'] or '-'}` · score `{h['score']}` · ref `{c['ref_id']}`"
            )
            st.markdown(h["text"])

    with st.expander("粗排 Top-20（融合分，Rerank 前）"):
        for cid, score in cands[:20]:
            meta = retriever.inventory[cid]["metadata"]
            st.markdown(
                f"- `{score:.4f}` {meta['source_file']}#{meta['location']} "
                f"（{meta['department'] or '-'}）"
            )

    if do_risk:
        with st.status("单主题风险识别…"):
            res = detect_risks(hits, extra_query=query)
        feedback.log_event(
            "risk_query", query=query,
            result_summary=f"{len(res['risks'])} 条风险",
            meta={"risks": [r["title"] for r in res["risks"]]},
        )
        st.subheader("风险识别（引用后校验 + 置信度规则 + 转人工路由）")
        if not res["risks"]:
            st.info("未识别出风险")
        for r in res["risks"]:
            with st.container(border=True):
                route = f"转人工：**是** → `{r['routing']}`" if r["needs_human"] else "转人工：否"
                st.markdown(
                    f"**[{r['type']}] {r['title']}** · 置信度 `{r['confidence']}` · {route}"
                )
                st.markdown(r["detail"])
                st.caption(
                    f"引用：{', '.join(r['citations']) or '无'}"
                    + (f" · 无效编号：{r['invalid_citations']}" if r["invalid_citations"] else "")
                    + (f" · {r['flag']}" if r.get("flag") else "")
                )
