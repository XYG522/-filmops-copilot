# -*- coding: utf-8 -*-
"""确定性检查的 pytest 包装：单一事实来源为 scripts/run_eval.py 里的检查函数。

`run_eval.py --regression/--boundary` 在评估管线里调用同一批函数；
本文件让它们在本地/CI 秒级运行（无 LLM、无 API 调用）。
R12 依赖已建索引（data/index 为 gitignore 产物），未建时跳过。
"""
from pathlib import Path

import pytest

from scripts.run_eval import PARSER_CHECKS, REGRESSION_CHECKS

ALL_CHECKS = dict(REGRESSION_CHECKS)
ALL_CHECKS.update(PARSER_CHECKS)
INDEX_GATED = {"R12"}


@pytest.mark.parametrize("rid", sorted(ALL_CHECKS))
def test_deterministic_check(rid, tmp_path):
    fn = ALL_CHECKS[rid]
    ok, detail = fn(tmp_path)
    assert ok, f"{rid} FAIL: {detail}"


def test_r12_index_consistency(tmp_path):
    index_dir = Path(__file__).resolve().parent.parent / "data" / "index"
    if not index_dir.exists():
        pytest.skip("索引未构建（gitignored），跳过 R12")
    ok, detail = REGRESSION_CHECKS["R12"](tmp_path)
    assert ok, f"R12 FAIL: {detail}"
