# -*- coding: utf-8 -*-
"""FilmOps Copilot · Streamlit UI（Day 5）。

5 页：①导入 ②索引管理 ③检索调试 ④周报生成+人工编辑确认 ⑤评估结果。
运行：streamlit run streamlit_app.py
"""

import os

import streamlit as st

st.set_page_config(page_title="FilmOps Copilot", page_icon="🎬", layout="wide")

# --- 云端部署兼容层（Streamlit Community Cloud 等无 .env 的环境）---
# app/llm.py 与 app/bge_client.py 用 os.getenv 读配置：
# 本地走 .env（load_dotenv），云端把 Secrets 面板的值同步进环境变量。
_ENV_KEYS = (
    "DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MAIN_MODEL",
    "DEEPSEEK_PRO_MODEL", "SILICONFLOW_API_KEY", "SILICONFLOW_BASE_URL",
    "EMBED_MODEL", "RERANK_MODEL",
)
for _k in _ENV_KEYS:
    if _k in os.environ:
        continue
    try:  # 本地无 secrets.toml 时 st.secrets 会抛 StreamlitSecretNotFoundError
        os.environ[_k] = str(st.secrets[_k])
    except Exception:
        pass


@st.cache_resource(show_spinner=False)
def _ensure_index() -> tuple[str, str]:
    """冷启动确保索引存在（云上磁盘是临时的，容器重启后从 data/ 源文件重建）。

    返回 (status, message)：status ∈ {"ok", "rebuilt", "failed"}。
    """
    from app.indexer import INDEX_DIR
    if (INDEX_DIR / "chunk_inventory.json").exists():
        return "ok", ""
    try:
        from app.ingest import ingest_all
        stats = ingest_all()
        return "rebuilt", (
            f"检测到容器冷启动，已自动重建索引：{stats['raw']} 条 → "
            f"{stats['chunks']} chunks（{stats['embedding_model']}）"
        )
    except Exception as exc:  # 密钥缺失/API 不可用：不崩页面，给出可读提示
        return "failed", f"索引不存在且自动重建失败：{exc}"


_index_status, _index_msg = _ensure_index()
if _index_status == "rebuilt":
    st.toast(_index_msg)
elif _index_status == "failed":
    st.warning("⚠️ " + _index_msg + "。请在 Secrets（云端）或 .env（本地）配置 API 密钥后刷新。")
    st.stop()

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
