# -*- coding: utf-8 -*-
"""FilmOps Copilot · Streamlit UI（Day 5）。

5 页：①导入 ②索引管理 ③检索调试 ④周报生成+人工编辑确认 ⑤评估结果。
运行：streamlit run streamlit_app.py
"""

import streamlit as st

st.set_page_config(page_title="FilmOps Copilot", page_icon="🎬", layout="wide")

page = st.navigation(
    [
        st.Page("app_pages/import_data.py", title="① 导入", icon=":material/upload_file:"),
        st.Page("app_pages/index_admin.py", title="② 索引管理", icon=":material/database:"),
        st.Page("app_pages/search_debug.py", title="③ 检索调试", icon=":material/search:"),
        st.Page("app_pages/report_editor.py", title="④ 周报生成", icon=":material/edit_note:"),
        st.Page("app_pages/evaluation.py", title="⑤ 评估结果", icon=":material/assessment:"),
    ],
    position="top",
)
page.run()

st.divider()
st.caption(
    "演示环境 · 全部数据为合成数据 · 输出需人工确认，不构成自动决策 · "
    "不做：全自动决策 / 预算审批 / 法律判断 / 自动分发 / 自动改排期 / 跨系统双向同步"
)
