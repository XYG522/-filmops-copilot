# -*- coding: utf-8 -*-
"""UI 共享资源：检索器缓存。

坑（docs/phase9-demo-plan.md §8）：Streamlit rerun 会重复加载索引/模型，每次点击卡几秒；
检索器必须 st.cache_resource 缓存，重建索引后调用 invalidate_retriever() 清缓存。
"""

import streamlit as st

from app.retriever import HybridRetriever


@st.cache_resource
def get_retriever() -> HybridRetriever:
    return HybridRetriever()


def invalidate_retriever() -> None:
    get_retriever.clear()
