# -*- coding: utf-8 -*-
"""①导入：Excel 模板 / 群聊·会议·文本粘贴 → 注册数据源（统一中间 Schema）。

注册后需到 ②索引管理 重建索引才可检索。支持 3 类格式，格式异常报错并提示。
"""

import re
from pathlib import Path

import streamlit as st

from app import feedback, ingest
from app.parsers import dedup

EXCEL_KINDS = {"排期表": "schedule", "预算表": "budget", "宣发物料": "promo"}
EXCEL_DEPT = {"排期表": "", "预算表": "", "宣发物料": "宣发部"}
TEXT_KINDS = {"群聊片段": "chat", "会议纪要": "meeting", "纯文本": "text"}


def _safe_name(name: str) -> str:
    return re.sub(r"[^\w\-.（）()]", "_", Path(name).name)


def _register(kind: str, doc_type: str, default_dept: str, file_name: str,
              preview_entries: list) -> None:
    item = ingest.register_source(file_name, kind, doc_type, default_dept)
    feedback.log_event(
        "import",
        query=file_name,
        result_summary=f"注册 {file_name}（{kind}）：{len(preview_entries)} 条",
        meta=item,
    )
    st.success(f"已注册数据源 {file_name}：解析出 {len(preview_entries)} 条。"
               "去 ②索引管理 重建索引后生效。")
    with st.expander("解析预览（前 3 条）"):
        for e in preview_entries[:3]:
            st.markdown(f"- `{e.location}` `{e.department or '-'}` {e.text[:80]}")


st.title("① 导入数据源")

st.caption(
    "支持 3 类格式：Excel 模板 / 群聊片段 / 文本粘贴。"
    "注册后统一转为中间 Schema（条目=事件/任务/风险线索），到 ②索引管理 重建索引生效。"
)

tab_excel, tab_text = st.tabs(["Excel 模板", "文本 / 群聊粘贴"], on_change="rerun")

if tab_excel.open:
    with tab_excel:
        with st.form("import_excel"):
            up = st.file_uploader("上传 .xlsx（列名与模板一致）", type=["xlsx"])
            kind = st.segmented_control(
                "表格类型", list(EXCEL_KINDS), default="排期表",
                help="排期/预算/宣发物料对应不同 doc_type，引用与检索时区分",
            )
            submitted = st.form_submit_button("注册数据源", icon=":material/library_add:")
        if submitted:
            if up is None:
                st.error("请先选择 .xlsx 文件")
            else:
                ingest.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
                path = ingest.UPLOAD_DIR / _safe_name(up.name)
                path.write_bytes(up.getbuffer())
                try:
                    preview = dedup(ingest.parse_source({
                        "file": path.name, "kind": "excel",
                        "doc_type": EXCEL_KINDS[kind], "default_dept": EXCEL_DEPT[kind],
                    }))
                except Exception as e:
                    path.unlink(missing_ok=True)
                    st.error(f"格式异常，未注册：{e}")
                else:
                    _register("excel", EXCEL_KINDS[kind], EXCEL_DEPT[kind], path.name, preview)

if tab_text.open:
    with tab_text:
        with st.form("import_text"):
            name = st.text_input("来源名", placeholder="如 06_周例会记录（用于引用溯源）")
            kind = st.segmented_control("文本类型", list(TEXT_KINDS), default="会议纪要")
            content = st.text_area("粘贴内容", height=240,
                                   placeholder="群聊片段需含 [YYYY-MM-DD HH:MM] 说话人：内容 格式")
            submitted = st.form_submit_button("注册数据源", icon=":material/library_add:")
        if submitted:
            if not content.strip():
                st.error("内容为空，未注册")
            else:
                file_name = _safe_name(name or f"pasted_{kind}.txt")
                if not file_name.endswith(".txt"):
                    file_name += ".txt"
                ingest.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
                path = ingest.UPLOAD_DIR / file_name
                path.write_text(content, encoding="utf-8")
                try:
                    preview = dedup(ingest.parse_source({
                        "file": path.name, "kind": TEXT_KINDS[kind], "doc_type": TEXT_KINDS[kind],
                    }))
                except Exception as e:
                    path.unlink(missing_ok=True)
                    st.error(f"格式异常，未注册：{e}")
                else:
                    if not preview:
                        path.unlink(missing_ok=True)
                        st.error("解析出 0 条：请检查格式（群聊需消息格式，纪要需编号议题），未注册")
                    else:
                        _register(TEXT_KINDS[kind], TEXT_KINDS[kind], "", path.name, preview)

with st.expander("已注册数据源"):
    manifest = ingest.load_manifest()
    if manifest:
        for m in manifest:
            st.markdown(f"- `{m['file']}`（{m['kind']} / {m['doc_type'] or '-'}）")
    else:
        st.markdown("暂无追加数据源（标准 5 个合成文件始终参与索引）")
