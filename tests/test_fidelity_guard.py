# -*- coding: utf-8 -*-
"""断言-证据一致性后校验（_fidelity_guard）单测。

针对修复 T01/T05 幻觉的两道防线之一：引用块不支持的字段/数字表述应整分句移除，
诚实声明（上下文未提供）与真实字段必须保留。chunk 文本取 06_shot_progress.xlsx#行18 同款。
"""
from app.generator import _fidelity_guard

CHUNK = ("镜号=E14-023；集数=第14集；场次=02；镜头类型=特效；剪辑阶段=特效合成；"
         "当前状态=进行中；计划完成=2026-09-24；备注=预告片高潮段所需镜头，外包反馈初版 9-25 才能出")
HITS = [{"text": CHUNK}]


def guard(text: str) -> tuple[str, int]:
    return _fidelity_guard(text, HITS)


def test_fabricated_field_dropped_real_kept():
    out, dropped = guard("- 当前状态：进行中 [1]\n- 部门=后期部 [1]\n")
    assert dropped == 1
    assert "部门=后期部" not in out
    assert "当前状态：进行中" in out


def test_bold_value_not_falsely_dropped():
    # 加粗 **值** 曾把星号沾进捕获值导致真实字段被误删
    out, dropped = guard("- 当前状态：**进行中** [1]\n")
    assert dropped == 0
    assert "进行中" in out


def test_honest_unknown_kept():
    out, dropped = guard("- 实际完成：上下文未提供该字段 [1]\n")
    assert dropped == 0
    assert "上下文未提供" in out


def test_honest_unknown_with_quotes_kept():
    # 字段键后带引号和"和"时值捕获会歪，整分句含"未提供"须保留
    out, dropped = guard("该条目未提供“实际完成”和“负责人”字段 [1]\n")
    assert dropped == 0
    assert "未提供" in out


def test_list_marker_reattached():
    # 删除带列表标记的首分句后，重组句须挂回标记，避免裸行
    out, dropped = guard("- 部门=后期部，日期=2026-09-24 [1]\n")
    assert dropped == 1
    assert out.startswith("- 日期=2026-09-24")


def test_sentence_level_citation_inheritance():
    # 字段列表式输出常只在句尾标一次编号：前段无自带引用也须受校验
    out, dropped = guard("日期=2026-09-24，部门=后期部 [1]\n")
    assert dropped == 1
    assert "日期=2026-09-24" in out
    assert "部门" not in out


def test_digit_not_in_chunk_dropped():
    out, dropped = guard("- 日期=2026-09-20 [1]\n")
    assert dropped == 1
    assert "2026-09-20" not in out


def test_real_digits_kept():
    out, dropped = guard("- 计划完成=2026-09-24 [1]\n")
    assert dropped == 0


def test_uncited_sentence_untouched():
    text = "说明：截至 2026-09-20 的快照记录。\n"
    out, dropped = guard(text)
    assert dropped == 0
    assert out == text


def test_mixed_field_list():
    out, dropped = guard(
        "集数=第14集、场次=02、镜头类型=特效、部门=后期部、计划完成=2026-09-24 [1]\n")
    assert dropped == 1
    assert "集数=第14集" in out and "计划完成=2026-09-24" in out
    assert "部门" not in out


def test_sentence_end_citation_covers_fields_before_semicolon():
    # G11 场景：字段清单后接 ；备注分句，编号只标在整句末尾——编号须覆盖 ；前的字段分句
    chunk = ("任务ID=S-007；任务名称=素材 DIT 备份归档；部门=制片部；负责人=DIT-大刘；"
             "计划开始=2026-09-11；计划完成=2026-09-21；当前进度=80%；状态=进行中；"
             "备注=第 5-8 集素材转码延迟 2 天")
    out, dropped = _fidelity_guard(
        "进行中：S-007 素材 DIT 备份归档，日期=2026-09-21，任务ID=S-007，部门=制片部，"
        "负责人=DIT-大刘，当前进度=80%，状态=进行中；备注=第 5-8 集素材转码延迟 2 天 [1]。\n",
        [{"text": chunk}])
    assert dropped == 0, f"真实字段被误删：{out}"
    assert "当前进度=80%" in out and "部门=制片部" in out and "DIT-大刘" in out


def test_mixed_separator_collapsed():
    # 被删分句留下的混杂分隔符（，、）须折叠，不残留 "，、"
    out, dropped = guard("- 风险：4 项，分别为特效返工、品牌露出、保险续保、器材清点 [1]\n")
    assert "，、" not in out
