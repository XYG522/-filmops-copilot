# -*- coding: utf-8 -*-
"""导入管线（Day 2 版从 scripts/build_index.py 抽出，供 CLI 与 Day 5 UI 共用）。

数据源 = 5 个标准合成数据文件 + data/uploaded/manifest.json 里注册的追加源。
UI 导入页注册新源后，必须重建索引才生效（见 app/indexer.build_index）。
"""

import json
from collections import Counter
from pathlib import Path

from app.chunker import chunk_entries
from app.indexer import build_index
from app.parsers import dedup, parse_chat, parse_excel, parse_meeting, parse_text

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
UPLOAD_DIR = DATA_DIR / "uploaded"
MANIFEST = UPLOAD_DIR / "manifest.json"

# 标准合成数据：文件名 → (解析方式, doc_type, 默认部门)
STANDARD_SOURCES = [
    ("01_schedule.xlsx", "excel", "schedule", ""),
    ("02_budget.xlsx", "excel", "budget", ""),
    ("03_promo_materials.xlsx", "excel", "promo", "宣发部"),
    ("04_chat_log.txt", "chat", "", ""),
    ("05_meeting_notes.txt", "meeting", "", ""),
    ("06_shot_progress.xlsx", "excel", "shot_progress", "后期部"),
    ("07_review_conclusions.xlsx", "excel", "review", "制片部"),
]


def load_manifest() -> list[dict]:
    if not MANIFEST.exists():
        return []
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def register_source(file_name: str, kind: str, doc_type: str = "",
                    default_dept: str = "") -> dict:
    """注册追加数据源（同名覆盖）。文件须已保存到 UPLOAD_DIR。"""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    item = {"file": file_name, "kind": kind, "doc_type": doc_type, "default_dept": default_dept}
    manifest = [m for m in load_manifest() if m["file"] != file_name] + [item]
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return item


def read_text_smart(path: Path) -> str:
    """读文本文件：UTF-8 优先，失败回退 GBK（中文 Excel 另存 CSV/文本常见编码，坑清单 #表格解析）。"""
    raw = path.read_bytes()
    for enc in ("utf-8", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"无法识别编码（utf-8/gbk 均失败）：{path.name}")


def parse_source(item: dict, upload_dir: Path = UPLOAD_DIR) -> list:
    """按 manifest 条目解析追加数据源 → Entry 列表。"""
    path = upload_dir / item["file"]
    kind = item["kind"]
    if kind == "excel":
        return parse_excel(path, item["doc_type"], item.get("default_dept", ""))
    if kind == "chat":
        return parse_chat(path)
    if kind == "meeting":
        return parse_meeting(path)
    return parse_text(read_text_smart(path), path.name, item.get("doc_type", "text"))


def ingest_all(data_dir: Path = DATA_DIR) -> dict:
    """全量重建索引：5 个标准文件 + 已注册追加源 → 解析 → 去重 → 切块 → 建索引。

    返回统计（导入页与索引管理页展示用）。
    """
    entries = []
    for name, kind, doc_type, dept in STANDARD_SOURCES:
        path = data_dir / name
        if not path.exists():
            continue
        if kind == "excel":
            entries += parse_excel(path, doc_type, dept)
        elif kind == "chat":
            entries += parse_chat(path)
        else:
            entries += parse_meeting(path)
    for item in load_manifest():
        entries += parse_source(item)

    raw = len(entries)
    entries = dedup(entries)
    chunks = chunk_entries(entries)
    collection = build_index(chunks)
    return {
        "raw": raw,
        "entries": len(entries),
        "chunks": len(chunks),
        "chunk_types": dict(Counter(c.chunk_type for c in chunks)),
        "embedding_model": collection.metadata.get("embedding_model", ""),
    }
