# -*- coding: utf-8 -*-
"""统一中间 Schema：所有来源解析后都变成 Entry；检索单位是 Chunk。

引用溯源约定（PRD：文件、行号、日期、部门）：
  - Entry.location 在解析时确定：Excel=行号、群聊=第N条消息、纪要=议题号
  - Chunk 的 metadata() 直接进 Chroma，检索命中即可回查原文
"""

from dataclasses import dataclass


@dataclass
class Entry:
    entry_id: str            # 全局唯一，如 "01_schedule.xlsx#行6"
    text: str                # 规范化后的文本
    source_file: str         # 来源文件名
    location: str            # 行号 / 消息序号 / 议题号 / 段号
    date: str                # YYYY-MM-DD，缺失为 ""
    department: str          # 部门，缺失为 ""
    doc_type: str            # schedule / budget / promo / chat / meeting / text


@dataclass
class Chunk:
    chunk_id: str
    text: str
    entry_ids: list[str]
    source_file: str
    location: str            # 单条目=行号；合并块=多个位置
    date: str
    department: str
    doc_type: str
    chunk_type: str          # table_row / chat_window / text_window

    def metadata(self) -> dict:
        return {
            "source_file": self.source_file,
            "location": self.location,
            "date": self.date,
            "department": self.department,
            "doc_type": self.doc_type,
            "chunk_type": self.chunk_type,
            "entry_ids": "、".join(self.entry_ids),
        }
