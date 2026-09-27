# -*- coding: utf-8 -*-
r"""
FilmOps Copilot — 上传测试数据生成脚本（只生成文件，不碰索引/manifest）

用途：生成一组 Excel 文件到 test_uploads/，由你通过 UI ①导入页手动上传，
      测试产品的导入-解析-注册-检索链路（含正常与异常用例）。

合规声明：全部为虚构内容，不包含任何真实公司、项目、艺人或个人信息。

用法：
  .venv\Scripts\python scripts\make_upload_test_data.py

测试流程（照做即可）：
  1. 运行本脚本 → test_uploads/ 下生成 6 个文件
  2. 启动 UI（http://localhost:8501）→ ①导入页 → 按下方矩阵逐个上传
  3. ②索引管理 → 重建索引
  4. ③检索调试 → 查「演员补拍档期」「品牌A道具未到场」验证新数据已入库

测试矩阵（文件 → 上传时「表格类型」→ 预期产品表现）：
  01_演员档期表.xlsx          排期表   | 解析出 12 条；预览可见补拍行；部门=制片部
  02_拍摄通告单.xlsx          排期表   | 解析出 24 条；引用日期=计划完成列
  03_预算表_合并单元格.xlsx    预算表   | 解析出 4 条；合并单元格的值已填充到整片区域
  04_宣发物料_缺列空表头.xlsx  宣发物料 | 解析出 3 条：空白行跳过、短行自动补齐、空表头忽略
  05_只有表头_空表.xlsx       排期表   | 解析出 0 条但仍注册（当前产品行为，无报错——已知小缺口）
  06_损坏表格.xlsx            任意     | 报错「格式异常，未注册」，文件被清理
"""

import sys
from pathlib import Path

try:  # Windows 终端统一 UTF-8 输出
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openpyxl import Workbook  # noqa: E402
from openpyxl.styles import Font, PatternFill  # noqa: E402

from industry_tables import (  # noqa: E402
    CALLSHEET_HEADERS, CALLSHEET_ROWS,
    TALENT_HEADERS, TALENT_ROWS,
)

TEST_DIR = Path(__file__).resolve().parent.parent / "test_uploads"

# ---------------------------------------------------------------------------
# 异常用例数据（正常用例复用 industry_tables 的演员档期表/拍摄通告单）
# ---------------------------------------------------------------------------
# 03 预算表：合并单元格（科目名称/负责人纵向合并 2 行，真实工作簿常见形态）
BUDGET_MERGED_HEADERS = ["科目代码", "科目名称", "预算金额（万元）", "已执行（万元）", "执行率", "负责人", "备注"]
BUDGET_MERGED_ROWS = [
    ["B-11", "衍生品开发费", 80, 45, "56.3%", "商务-老郑", "手办/立牌打样中"],
    ["B-12", "衍生品开发费", 80, 45, "56.3%", "商务-老郑", "第二批打样 9-25 验收"],
    ["B-13", "商务合作对接费", 20, 8, "40.0%", "宣发-阿澜", ""],
    ["B-14", "物料仓储物流", 10, 10, "100%", "制片-小陈", "已结清"],
]
BUDGET_MERGES = ["B2:B3", "F2:F3"]

# 04 宣发物料：第 4 列表头为空 + 一行缺列 + 一行全空 + 备注空值
PROMO_RAGGED_HEADERS = ["物料ID", "物料名称", "物料类型", "", "状态", "投放渠道", "备注"]
PROMO_RAGGED_ROWS = [
    ["Y-001", "角色立牌", "平面", "", "制作中", "线下门店", ""],
    ["Y-002", "花絮合集", "视频"],
    ["", "", "", "", "", "", ""],
    ["Y-003", "直播脚本", "文案", "", "已完成", "直播平台", "9-18 已上线"],
    ["Y-004", "衍生品宣传片", "视频", "", "未开始", "抖音", ""],
]


def write_xlsx(filename, title, headers, rows, widths, merges=None):
    """通用写表（样式与项目主数据一致：加粗表头 + 浅蓝填充 + 列宽）。"""
    wb = Workbook()
    ws = wb.active
    ws.title = title
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="DDEBF7")
    for row in rows:
        ws.append(row)
    for rng in merges or []:
        ws.merge_cells(rng)
    for idx, width in enumerate(widths, start=1):
        ws.column_dimensions[ws.cell(row=1, column=idx).column_letter].width = width
    path = TEST_DIR / filename
    wb.save(path)
    return path


def main():
    TEST_DIR.mkdir(exist_ok=True)
    files = [
        write_xlsx("01_演员档期表.xlsx", "演员档期表", TALENT_HEADERS, TALENT_ROWS,
                   [12, 16, 8, 20, 12, 12, 12, 10, 10, 40]),
        write_xlsx("02_拍摄通告单.xlsx", "拍摄通告单", CALLSHEET_HEADERS, CALLSHEET_ROWS,
                   [12, 14, 8, 6, 10, 24, 18, 8, 12, 12, 30]),
        write_xlsx("03_预算表_合并单元格.xlsx", "预算执行表", BUDGET_MERGED_HEADERS, BUDGET_MERGED_ROWS,
                   [10, 20, 16, 16, 10, 14, 40], merges=BUDGET_MERGES),
        write_xlsx("04_宣发物料_缺列空表头.xlsx", "宣发素材清单", PROMO_RAGGED_HEADERS, PROMO_RAGGED_ROWS,
                   [10, 20, 10, 6, 10, 12, 30]),
        write_xlsx("05_只有表头_空表.xlsx", "全项目排期", TALENT_HEADERS[:9], [],
                   [12, 16, 8, 20, 12, 12, 12, 10, 10]),
        # 06 损坏表格：文本内容冒充 xlsx（上传应报「格式异常，未注册」）
        TEST_DIR / "06_损坏表格.xlsx",
    ]
    files[-1].write_bytes("这不是 Excel 文件，只是重命名成 .xlsx 的文本。".encode("utf-8"))

    print(f"已生成 {len(files)} 个测试文件到 {TEST_DIR}")
    print("""
测试矩阵（UI ①导入页 → 选择表格类型 → 对照预期表现）：
  01_演员档期表.xlsx          排期表   | 解析出 12 条；预览可见补拍行；部门=制片部
  02_拍摄通告单.xlsx          排期表   | 解析出 24 条；引用日期=计划完成列
  03_预算表_合并单元格.xlsx    预算表   | 解析出 4 条；合并单元格的值已填充到整片区域
  04_宣发物料_缺列空表头.xlsx  宣发物料 | 解析出 3 条：空白行跳过、短行自动补齐、空表头忽略
  05_只有表头_空表.xlsx       排期表   | 解析出 0 条但仍注册（当前产品行为，无报错——已知小缺口）
  06_损坏表格.xlsx            任意     | 报错「格式异常，未注册」，文件被清理
上传完成后：②索引管理 → 重建索引 → ③检索调试查「演员补拍档期」「品牌A道具未到场」""")


if __name__ == "__main__":
    main()
