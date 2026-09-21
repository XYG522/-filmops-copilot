# FilmOps Copilot — 影视项目周报与风险推进 Copilot（个人 Demo）

> ⚠️ 合规声明：本项目全部数据为**合成数据**——项目、公司、人物、预算、排期、合同均为虚构，
> 不使用任何真实公司内部文档、合同、艺人信息或未上映内容。
> 所有输出需**人工确认**，不构成自动决策。详见 [docs/data_readme.md](docs/data_readme.md)。

## 项目简介

影视项目进度信息分散在 Excel、群聊、任务看板中：周报靠人工汇总，风险发现滞后，行动项不闭环。
本工具把多源信息导入统一索引，生成**引用可溯源**的周报草稿与风险清单，由人工编辑确认后导出。

- 核心使用者：制片助理 / PMO
- 核心决策者：制片主任（高风险条目人工确认）
- 演示项目：《雾港灯塔》16 集悬疑网剧（纯虚构）

## 当前进度（按 docs/phase9-demo-plan.md 排期）

- [x] Day 1 脚手架与合成数据（5 个数据文件 + 7 个预埋风险）
- [x] Day 2 导入-清洗-切块-索引（60 条 Entry → 52 个 Chunk，引用元数据完整）
- [ ] Day 3 检索与引用链路
- [ ] Day 4 生成层（周报 / 风险 / 行动项）
- [ ] Day 5 Streamlit UI
- [ ] Day 6 评估集与跑分
- [ ] Day 7 收尾（README 补全 / Demo 视频 / 成本实测）

## 目录结构

```
filmops-copilot/
├── data/                        # 合成数据（make_synthetic_data.py 生成，可提交 git）
├── docs/
│   ├── phase9-demo-plan.md      # 开发计划（PRD 审查 / 排期 / 坑清单）
│   └── data_readme.md           # 数据说明 + 预埋风险答案底稿
├── scripts/
│   └── make_synthetic_data.py   # 数据生成脚本（幂等，带预埋风险自检）
├── app/                         # 应用代码（Day 2+）
├── requirements.txt
└── .env.example
```

## 快速开始

（Day 5 完成 UI 后补全完整流程）

```bash
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python scripts\make_synthetic_data.py
```

## 功能 / 架构 / 评估 / 边界

见 [docs/phase9-demo-plan.md](docs/phase9-demo-plan.md)。

核心边界：不做全自动决策、预算审批、法律判断、自动分发、自动改排期、跨系统双向同步。
