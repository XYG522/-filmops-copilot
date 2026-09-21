# -*- coding: utf-8 -*-
"""Chroma 索引：建库 / 加载 / 向量检索（Day 2 版；混合检索 + Rerank 在 Day 3）。

约定：
  - 每次重建先删旧集合，保证索引与数据版本一致（评估可复现）
  - embedding 模型名写入集合 metadata，防「查询与索引不同模型」事故
  - 持久化目录 data/index/（已在 .gitignore 中）
"""

from pathlib import Path

import chromadb

from app.bge_client import EMBED_MODEL, embed_texts
from app.schema import Chunk

COLLECTION_NAME = "filmops_demo"
INDEX_DIR = Path(__file__).resolve().parent.parent / "data" / "index"


def _client(index_dir: Path = INDEX_DIR) -> chromadb.PersistentClient:
    index_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(index_dir))


def build_index(chunks: list[Chunk], index_dir: Path = INDEX_DIR) -> chromadb.Collection:
    client = _client(index_dir)
    try:  # 重建：删除旧集合
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine", "embedding_model": EMBED_MODEL},
    )
    embeddings = embed_texts([c.text for c in chunks])
    collection.add(
        ids=[c.chunk_id for c in chunks],
        documents=[c.text for c in chunks],
        embeddings=embeddings,
        metadatas=[c.metadata() for c in chunks],
    )
    return collection


def load_collection(index_dir: Path = INDEX_DIR) -> chromadb.Collection:
    return _client(index_dir).get_collection(COLLECTION_NAME)


def query_top(collection: chromadb.Collection, query: str, top_k: int = 5) -> list[dict]:
    """向量检索：返回 [{text, distance, meta}]（distance 越小越相关）。"""
    q_emb = embed_texts([query])[0]
    res = collection.query(
        query_embeddings=[q_emb],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    docs = res["documents"][0]
    metas = res["metadatas"][0]
    dists = res["distances"][0]
    return [
        {"text": d, "distance": dist, "meta": m}
        for d, m, dist in zip(docs, metas, dists)
    ]
