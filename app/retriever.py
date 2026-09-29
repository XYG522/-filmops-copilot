# -*- coding: utf-8 -*-
"""Day 3 检索：混合检索（向量 0.7 + BM25 0.3）→ BGE Reranker → Top-K，带引用构造。

PRD 口径：粗排 Top-20 → Rerank → Top-5 送 LLM（本模块只到 Top-K 检索，LLM 在 Day 4）。
BM25 用 jieba 分词（中文必需，见坑清单）。
"""

from pathlib import Path

import jieba
from rank_bm25 import BM25Okapi

from app.bge_client import embed_texts, rerank
from app.indexer import INDEX_DIR, load_collection, load_inventory

VEC_WEIGHT = 0.7
BM25_WEIGHT = 0.3
COARSE_K = 20
FINAL_K = 5


def _minmax(scores: dict[str, float]) -> dict[str, float]:
    """min-max 归一化；空输入返回空（无命中信号）；值全相等时归 0（无信息）。"""
    if not scores:
        return {}
    vals = list(scores.values())
    lo, hi = min(vals), max(vals)
    if hi == lo:
        return {k: 0.0 for k in scores}
    return {k: (v - lo) / (hi - lo) for k, v in scores.items()}


class HybridRetriever:
    """向量 + BM25 融合粗排，BGE Reranker 精排，命中附引用。"""

    def __init__(self, collection=None, inventory: list[dict] | None = None,
                 index_dir: Path = INDEX_DIR):
        self.collection = collection or load_collection(index_dir)
        inventory = inventory if inventory is not None else load_inventory(index_dir)
        self.inventory = {c["chunk_id"]: c for c in inventory}
        self._id_order = [c["chunk_id"] for c in inventory]
        self._bm25 = BM25Okapi([jieba.lcut_for_search(c["text"]) for c in inventory])

    # ---- 粗排 ----
    def coarse_rank(self, query: str, k: int = COARSE_K) -> list[tuple[str, float]]:
        """融合粗排，返回 [(chunk_id, fused_score)] 降序。"""
        # 1. 向量
        q_emb = embed_texts([query])[0]
        res = self.collection.query(
            query_embeddings=[q_emb],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )
        vec = {cid: 1.0 - dist for cid, dist in zip(res["ids"][0], res["distances"][0])}

        # 2. BM25（jieba 分词，去掉零分噪声）
        bm = self._bm25.get_scores(jieba.lcut_for_search(query))
        top_idx = sorted(range(len(bm)), key=lambda i: -bm[i])[:k]
        bm25 = {self._id_order[i]: bm[i] for i in top_idx if bm[i] > 0}

        # 3. 融合 0.7/0.3（各自 min-max 归一后加权）
        nv, nb = _minmax(vec), _minmax(bm25)
        fused = {
            cid: VEC_WEIGHT * nv.get(cid, 0.0) + BM25_WEIGHT * nb.get(cid, 0.0)
            for cid in set(nv) | set(nb)
        }
        return sorted(fused.items(), key=lambda kv: -kv[1])[:k]

    # ---- 精排 + 引用 ----
    def retrieve(self, query: str, final_k: int = FINAL_K,
                 cands: list[tuple[str, float]] | None = None,
                 source_whitelist: set[str] | None = None) -> list[dict]:
        cands = cands if cands is not None else self.coarse_rank(query)
        # 数据范围过滤：插在粗排之后、rerank 之前——若在 rerank 后过滤，域外块会挤占
        # top_n 名额，饿死域内证据（周报「仅上传数据」范围依赖此位置）
        if source_whitelist is not None:
            cands = [c for c in cands
                     if self.inventory[c[0]]["metadata"]["source_file"] in source_whitelist]
        if len(cands) <= final_k:
            top = cands
        else:
            texts = [self.inventory[cid]["text"] for cid, _ in cands]
            rr = rerank(query, texts, top_n=final_k)
            top = [(cands[r["index"]][0], r["relevance_score"]) for r in rr]
        return [self._hit(cid, score) for cid, score in top]

    def _hit(self, chunk_id: str, score: float) -> dict:
        chunk = self.inventory[chunk_id]
        meta = chunk["metadata"]
        return {
            "chunk_id": chunk_id,
            "score": round(score, 4),
            "text": chunk["text"],
            "citation": {
                "ref_id": f"{meta['source_file']}#{meta['location']}",
                "source_file": meta["source_file"],
                "location": meta["location"],
                "date": meta["date"],
                "department": meta["department"],
                "entry_ids": meta["entry_ids"],
                "snippet": chunk["text"][:120],
            },
        }
