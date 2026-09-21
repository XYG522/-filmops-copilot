# -*- coding: utf-8 -*-
"""反馈回流 / 审计日志（SQLite）：查询、生成、人工修改、采纳状态、导入、导出。

MVP 口径（docs/phase9-demo-plan.md §1 #10）：
  同时充当评估数据源和审计日志；Day 6 评估集建设从这里取真实交互样本。
库文件 data/feedback.db（已在 .gitignore，不入库）。
"""

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "feedback.db"

KINDS = ("query", "risk_query", "generate", "edit_decision", "export", "import", "rebuild", "eval_run")


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT DEFAULT (datetime('now', 'localtime')),
            kind TEXT NOT NULL,
            query TEXT DEFAULT '',
            result_summary TEXT DEFAULT '',
            decision TEXT DEFAULT '',
            meta TEXT DEFAULT '{}'
        )"""
    )
    return conn


def log_event(kind: str, query: str = "", result_summary: str = "",
              decision: str = "", meta: dict | None = None) -> None:
    """写一条事件。kind 见 KINDS；decision 用于采纳状态（adopt/modify/ignore）。"""
    assert kind in KINDS, f"未知事件类型: {kind}"
    with _conn() as conn:
        conn.execute(
            "INSERT INTO feedback (kind, query, result_summary, decision, meta) "
            "VALUES (?, ?, ?, ?, ?)",
            (kind, query, result_summary, decision, json.dumps(meta or {}, ensure_ascii=False)),
        )


def recent(limit: int = 50) -> list[dict]:
    """最近事件（倒序），审计日志展示用。"""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT ts, kind, query, result_summary, decision, meta "
            "FROM feedback ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(zip(("ts", "kind", "query", "result_summary", "decision", "meta"), r)) for r in rows]


def stats() -> dict[str, int]:
    """各事件类型计数（评估页展示用）。"""
    with _conn() as conn:
        rows = conn.execute("SELECT kind, COUNT(*) FROM feedback GROUP BY kind").fetchall()
    return dict(rows)
