# -*- coding: utf-8 -*-
"""切块策略（PRD 口径）：
  - 表格：按行/任务独立成块，text 自带「列名=值」前缀（保留表头语义）
  - 群聊：按日期 + 时间窗合并为 300–500 字符，不切断单条消息
  - 叙述文本（纪要/粘贴）：递归切分，512 字符，80 重叠，句子边界优先

关键点：Chunk 的 location/date/department 元数据在切块时写入（引用溯源地基）。
"""

import itertools
import re

from app.schema import Chunk, Entry

CHUNK_SIZE = 512
CHUNK_OVERLAP = 80
CHAT_WINDOW_MAX = 500

_counter = itertools.count(1)
_SENT_SPLIT = re.compile(r"(?<=[。！？；])[ \t]*|\n+")


def split_long_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """句子边界优先的窗口切分。"""
    text = text.strip()
    if len(text) <= size:
        return [text]
    sentences = [s for s in _SENT_SPLIT.split(text) if s.strip()]
    windows: list[str] = []
    cur = ""
    for s in sentences:
        if cur and len(cur) + len(s) > size:
            windows.append(cur)
            cur = (cur[-overlap:] + s).lstrip("；;")
        else:
            cur += s
    if cur:
        windows.append(cur)
    return windows


def _new_chunk(text, entry_ids, source_file, location, date, department, doc_type, chunk_type) -> Chunk:
    return Chunk(
        chunk_id=f"chunk-{next(_counter):04d}",
        text=text,
        entry_ids=entry_ids,
        source_file=source_file,
        location=location,
        date=date,
        department=department,
        doc_type=doc_type,
        chunk_type=chunk_type,
    )


def _table_chunks(entries: list[Entry]) -> list[Chunk]:
    """表格行 → 独立块（行内自含表头语义）。"""
    return [
        _new_chunk(e.text, [e.entry_id], e.source_file, e.location, e.date, e.department, e.doc_type, "table_row")
        for e in entries
    ]


def _chat_chunks(entries: list[Entry]) -> list[Chunk]:
    """群聊 → 按日期分组，组内按 ≤500 字符窗口合并，不切断单条消息。"""
    days: dict[str, list[Entry]] = {}
    order: list[str] = []
    for e in entries:
        key = e.date or "(无日期)"
        if key not in days:
            days[key] = []
            order.append(key)
        days[key].append(e)

    out: list[Chunk] = []
    for day in order:
        day_entries = days[day]
        dept = "、".join(dict.fromkeys(e.department for e in day_entries if e.department))
        cur_lines, cur_ids, cur_locs, cur_len = [], [], [], 0

        def flush():
            out.append(_new_chunk(
                "\n".join(cur_lines), cur_ids, day_entries[0].source_file,
                "；".join(cur_locs), day, dept, "chat", "chat_window",
            ))

        for e in day_entries:
            if cur_lines and cur_len + len(e.text) > CHAT_WINDOW_MAX:
                flush()
                cur_lines, cur_ids, cur_locs, cur_len = [], [], [], 0
            cur_lines.append(e.text)
            cur_ids.append(e.entry_id)
            cur_locs.append(e.location)
            cur_len += len(e.text)
        if cur_lines:
            flush()
    return out


def _text_chunks(entries: list[Entry]) -> list[Chunk]:
    """叙述文本 → 递归切分；被切分的块在 location 上加 (i/n) 标记。"""
    out = []
    for e in entries:
        windows = split_long_text(e.text)
        if len(windows) == 1:
            out.append(_new_chunk(e.text, [e.entry_id], e.source_file, e.location,
                                  e.date, e.department, e.doc_type, "text_window"))
        else:
            for i, w in enumerate(windows, start=1):
                out.append(_new_chunk(w, [e.entry_id], e.source_file, f"{e.location}({i}/{len(windows)})",
                                      e.date, e.department, e.doc_type, "text_window"))
    return out


def chunk_entries(entries: list[Entry]) -> list[Chunk]:
    table_types = {"schedule", "budget", "promo", "shot_progress", "review", "talent", "callsheet"}
    return (
        _table_chunks([e for e in entries if e.doc_type in table_types])
        + _chat_chunks([e for e in entries if e.doc_type == "chat"])
        + _text_chunks([e for e in entries if e.doc_type not in table_types and e.doc_type != "chat"])
    )
