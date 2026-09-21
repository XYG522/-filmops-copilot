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

- [x] Day 1 脚手架与合成数据（7 个数据文件 + 9 个预埋风险）
- [x] Day 2 导入-清洗-切块-索引（169 条 Entry → 161 个 Chunk，引用元数据完整）
- [x] Day 3 混合检索（向量0.7+BM25 0.3）+ Rerank + 引用链路（召回@20 验收 10/10）
- [x] Day 4 生成层（周报 / 风险 / 行动项 + 引用后校验 + 置信度三档 + 转人工 + 对抗样例 3/3）
- [x] Day 5 Streamlit UI（5 页：导入 / 索引管理 / 检索调试 / 周报生成+人工编辑确认 / 评估；Markdown 导出；反馈 SQLite）
- [x] 周报口径对齐真实流程（对比上周：镜头进度 / 计划达成 / 风险遗留 + 审片销号：待改→已改→复核通过；新增镜头进度表与审片结论表两个数据源）
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
├── app/                         # 应用代码（解析/索引/检索/生成/反馈）
├── app_pages/                   # Streamlit 5 页（st.navigation + st.Page）
├── streamlit_app.py             # UI 入口（合规脚注 + 页面导航）
├── requirements.txt
└── .env.example
```

## 快速开始

```bash
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python scripts\make_synthetic_data.py

# UI（Day 5）
.venv\Scripts\python -m streamlit run streamlit_app.py
```

CLI 链路（索引 → 检索 → 生成）：

```bash
.venv\Scripts\python scripts\build_index.py      # 建索引（Day 2）
.venv\Scripts\python scripts\search_cli.py "哪个任务延期了"   # 检索 + 引用（Day 3）
.venv\Scripts\python scripts\generate_cli.py --report        # 周报草稿（Day 4，存 outputs/）
.venv\Scripts\python scripts\generate_cli.py --risk "特效外包什么时候交付"
.venv\Scripts\python scripts\generate_cli.py --actions
.venv\Scripts\python scripts\generate_cli.py --adversarial   # 对抗样例（注入/越权/批预算）
```

## 功能 / 架构 / 评估 / 边界

见 [docs/phase9-demo-plan.md](docs/phase9-demo-plan.md)。

核心边界：不做全自动决策、预算审批、法律判断、自动分发、自动改排期、跨系统双向同步。
