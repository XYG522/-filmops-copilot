# -*- coding: utf-8 -*-
"""多源解析器：Excel / 群聊 / 文本粘贴 → 统一中间 Schema（Entry）。

清洗规则（Demo 版，不做语义级操作）：
  - 行级去空白、压缩空行
  - 规则去重：同 (来源文件, 位置) 只保留一条
"""

import re
from pathlib import Path

from openpyxl import load_workbook

from app.schema import Entry

# 负责人/角色前缀 → 部门（无「部门」列的文件用）
OWNER_DEPT = {
    "制片": "制片部",
    "后期": "后期部",
    "宣发": "宣发部",
    "运营": "宣发部",
    "财务": "财务部",
    "DIT": "制片部",
}

_CHAT_LINE_RE = re.compile(r"^\[(\d{4}-\d{2}-\d{2}) \d{2}:\d{2}\] (.+?)：(.+)$")
_TOPIC_RE = re.compile(r"(?m)^(\d+)\.\s")


def clean_text(s: str) -> str:
    lines = [ln.strip() for ln in (s or "").splitlines()]
    return "\n".join(ln for ln in lines if ln)


def _dept_from_owner(owner: str) -> str:
    for prefix, dept in OWNER_DEPT.items():
        if owner.startswith(prefix):
            return dept
    return ""


def _expand_merged(ws) -> None:
    """合并单元格展开：锚点值填充到整片区域（坑清单 #表格解析：合并单元格行错位）。

    MergedCell 只读，且 values_only 读合并区非锚点恒为 None：
    解合并 → 填值（读时预处理，不还原合并）。
    """
    for rng in list(ws.merged_cells.ranges):
        anchor = ws.cell(rng.min_row, rng.min_col).value
        ws.unmerge_cells(str(rng))
        for row in ws.iter_rows(min_row=rng.min_row, max_row=rng.max_row,
                                min_col=rng.min_col, max_col=rng.max_col):
            for cell in row:
                if cell.value is None:
                    cell.value = anchor


def parse_excel(path: Path, doc_type: str, default_dept: str = "") -> list[Entry]:
    """Excel 表格 → 每行一个 Entry，text 为「列名=值；列名=值」串（保留表头语义）。"""
    wb = load_workbook(path, data_only=True)
    ws = wb.active
    _expand_merged(ws)
    rows = list(ws.iter_rows(values_only=True))
    headers = [str(h) if h is not None else "" for h in rows[0]]

    entries = []
    for i, row in enumerate(rows[1:], start=2):  # 数据从 Excel 第 2 行开始
        cells = ["" if v is None else str(v) for v in row]
        cells += [""] * (len(headers) - len(cells))
        pairs = [f"{h}={v}" for h, v in zip(headers, cells) if h and v]
        if not pairs:
            continue

        dept = default_dept
        if "部门" in headers and cells[headers.index("部门")]:
            dept = cells[headers.index("部门")]
        if not dept and "负责人" in headers:
            dept = _dept_from_owner(cells[headers.index("负责人")])

        date = ""
        for col in ("审片日期", "计划完成", "实际完成"):  # 首个出现的日期列（缺省依次回退）
            if col in headers:
                date = cells[headers.index(col)]
                break

        entries.append(Entry(
            entry_id=f"{path.name}#行{i}",
            text="；".join(pairs),
            source_file=path.name,
            location=f"行{i}",
            date=date,
            department=dept,
            doc_type=doc_type,
        ))
    return entries


def parse_chat(path: Path) -> list[Entry]:
    """群聊片段 → 每条消息一个 Entry（群名行存为「群信息」条目，随同日消息合并）。"""
    entries = []
    n = 0
    title_lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        m = _CHAT_LINE_RE.match(line)
        if m:
            n += 1
            date, speaker, msg = m.groups()
            dept_m = re.search(r"\((.+?)\)$", speaker)
            role = dept_m.group(1) if dept_m else ""
            entries.append(Entry(
                entry_id=f"{path.name}#第{n}条",
                text=f"{speaker}：{msg}",
                source_file=path.name,
                location=f"第{n}条消息",
                date=date,
                department=_dept_from_owner(role),
                doc_type="chat",
            ))
        else:
            title_lines.append(line)

    if title_lines:
        entries.insert(0, Entry(
            entry_id=f"{path.name}#群信息",
            text="\n".join(title_lines),
            source_file=path.name,
            location="群信息",
            date="",
            department="",
            doc_type="chat",
        ))
    # 群信息条目补上第一条消息的日期，使其与同日消息合并
    if entries and not entries[0].date and len(entries) > 1:
        entries[0].date = entries[1].date
    return entries


def parse_meeting(path: Path) -> list[Entry]:
    """会议纪要 → 头部（时间/参会）+ 每个编号议题一个 Entry。"""
    content = clean_text(path.read_text(encoding="utf-8"))
    parts = _TOPIC_RE.split(content)  # [头部, "1", 议题1, "2", 议题2, ...]
    date = ""
    m = re.search(r"会议时间：(\d{4}-\d{2}-\d{2})", parts[0])
    if m:
        date = m.group(1)

    entries = []
    if parts[0].strip():
        entries.append(Entry(
            entry_id=f"{path.name}#头部",
            text=parts[0].strip(),
            source_file=path.name,
            location="会议头部",
            date=date,
            department="",
            doc_type="meeting",
        ))
    for i in range(1, len(parts), 2):
        num, body = parts[i], parts[i + 1].strip()
        entries.append(Entry(
            entry_id=f"{path.name}#议题{num}",
            text=f"议题{num}：{body}",
            source_file=path.name,
            location=f"议题{num}",
            date=date,
            department="",
            doc_type="meeting",
        ))
    return entries


def parse_text(text: str, source_name: str, doc_type: str = "text") -> list[Entry]:
    """任意粘贴文本 → 按空行分段。"""
    blocks = re.split(r"\n\s*\n", clean_text(text))
    entries = []
    for i, block in enumerate(blocks, start=1):
        if not block.strip():
            continue
        entries.append(Entry(
            entry_id=f"{source_name}#段{i}",
            text=block.strip(),
            source_file=source_name,
            location=f"段{i}",
            date="",
            department="",
            doc_type=doc_type,
        ))
    return entries


def dedup(entries: list[Entry]) -> list[Entry]:
    """规则去重：同 (来源文件, 位置) 只保留第一条。语义去重不做（PRD 审查 #5）。"""
    seen = set()
    out = []
    for e in entries:
        key = (e.source_file, e.location)
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out
