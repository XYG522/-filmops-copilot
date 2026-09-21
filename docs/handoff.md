# 项目交接存档（2026-09-22）

> 给未来任何一位继续这个项目的协作者（人或 AI）读的完整上下文。
> 一行总结：**7 天排期全部完成**——合成数据 → 索引检索 → 生成层 → Streamlit UI → 120 条评估，
> 当前处于"可公开/可投递作品集"状态，剩余视频录制与少量补跑。

## 1. 状态总览

| 里程碑 | 状态 | commit |
| --- | --- | --- |
| Day 1-2 数据 + 导入-切块-索引 | ✅ | aaa6bb7 |
| Day 3 混合检索 + Rerank + 引用链路 | ✅ | 224a10e |
| Day 4 生成层 + 对抗拦截 | ✅ | 04c2150 |
| Day 5 Streamlit UI（5 页）+ 反馈审计 | ✅ | ba2044f / 4532eed |
| 周报口径对齐真实流程（4 个澄清答案落地） | ✅ | d72880e |
| Day 6 评估集 120 条 + 跑分 + 指标表 | ✅ | 5524969 |
| Day 7 收尾（README/架构图/成本实测/合规/Demo 脚本） | ✅ | a897fa2 |

Day 6 最终成绩（`docs/eval_report.md`）：回归 20/20、对抗 20/20（硬门槛）、边界 30/30、
检索召回@20 95% / Top5 81%、风险召回 14/15=93%、引用准确 100%/100%、幻觉 0/0%、要点覆盖 88%。
**唯一未达标**：必备引用覆盖率 74%（目标 90%，结构性归因见报告）。

## 2. 如何运行（环境已就绪）

```bash
cd C:\Users\ASUS\02cc\filmops-copilot
.venv\Scripts\python -m streamlit run streamlit_app.py   # UI：http://localhost:8501
```

- `.env` 已配置（勿提交）、索引已建（`data/index/`，gitignore）、最新周报在 `outputs/weekly_report_*.md`
- CLI：`search_cli.py`（检索）、`generate_cli.py --report/--risk/--actions/--adversarial`（生成）、
  `run_eval.py --all/--golden/--report`（评估，带逐条缓存，重跑自动跳过已过条目）
- 换机器：`pip install -r requirements.txt` → 复制 `.env` → `make_synthetic_data.py` → `build_index.py`

## 3. 架构速览

数据流：多源文件 → 解析清洗（统一 Entry）→ 切块（表格行/聊天窗口/递归 512+80）→
Chroma 向量 + BM25（jieba）→ 混合检索（向量 0.7 + BM25 0.3）→ BGE Reranker Top-20→5/8 →
DeepSeek 生成（周报/风险/行动项）→ 引用后校验 + 置信度三档 + 越权守卫 + 转人工路由 →
人工编辑确认 → Markdown 导出 + SQLite 反馈审计。

关键文件职责：
- `app/ingest.py` 导入清洗 · `app/parsers.py` 3 类解析器 · `app/retriever.py` 混合检索+Rerank
- `app/generator.py` 生成层（系统提示词/引用校验/置信度/守卫/周报 15 查询 MAX 40 块）
- `app/llm.py` DeepSeek 客户端（空输出翻倍预算重试）· `app/eval_judge.py` V4-Pro 判卷
- `scripts/run_eval.py` 评估 runner · `app_pages/` 5 页 UI · `app/feedback.py` SQLite 审计
- `data/eval/*.json` 120 条评估集 · `data/eval/golden_seed.json` 开发期种子（自测 query 当场追加）

## 4. 必须遵守的口径与决策（改动前先读）

- **周报口径**（用户 4 个澄清答案）：①镜头数据=剪辑审片口径 ②对比上周=镜头进度+计划达成+风险遗留
  ③审片标注只记结论（镜号+通过/返修/重拍）④修改落实=意见销号制（每镜 待改→已改→复核通过，复核通过才算落实）
- **汇总数以会议纪要议题1为准**（0607 明细表是节选），别让 LLM 数 chunk
- **数据快照截至 2026-09-20**："当前/现在"一律按快照口径，不得预测未来状态；只写"上下文未提供"，不得断言"全台账不存在"
- **模型错开**：生成用 deepseek-flash，判卷用 deepseek-v4-pro（自我偏好风险）
- **安全红线**：越权/写操作按句拦截（否定语境豁免）；"已执行"是预算表合法字段**不能禁**；
  禁止声称执行过工具（"已通过 list_entries 核对"是编造）；预算/合规/依赖风险强制转人工
- **评估条目 ok 口径**：必备引用完整性单列指标（must_cite_coverage），不再计入条目 ok（避免双重计分）
- **检索 Top-8 上下文**是 Day 6 修问题后的统一口径（汇总类问题跨文件多证据）

## 5. 已知问题与局限（诚实清单，不掩盖）

1. **必备引用覆盖率 74% 未达 90%**：归因=Top-8 检索上限 + 模型偶发不标注已有编号。
   改进方向：查询改写扩展召回、上下文窗口扩大、引用完整性后校验器
2. **黄金集 9 条未跑分**（A07-A10、T01-T05）：后台跑分被系统内存回收杀掉后按用户决定跳过。
   补跑：`run_eval.py --golden`（约 8 分钟，缓存自动跳过已过条目）
3. **R15 真漏检**：送审冲突只归"延期"未归"合规"——影响转人工路由（合规→法务），值得后续修
4. **R03/R06 类型分歧**：模型归"延期"，注册表是"依赖/合规"——judge 按实质口径判检出，但路由同样受影响
5. judge 自身有偏差，报告结论是"样本内表现"，需人工抽查
6. 已知崩溃类坑（已修）：BM25 零命中、合并单元格只读、judge 误报编造、空输出重试

## 6. 待办（按优先级）

- [ ] Demo 视频录制（脚本 `docs/demo_script.md`；或投递 3 张截图：检索溯源/周报草稿/指标表）
- [ ] 补跑黄金集 9 条 → `run_eval.py --report` 刷新指标表
- [ ] 公开仓库前最后核一遍 secrets（已查：.env 零历史、无真实密钥）
- [ ] 可选优化：风险类型判定的路由对齐（R15/R03/R06）、引用完整性后校验器、周报增量生成
- [ ] 可选：把 `data/eval/golden_seed.json` 的开发期自测 query 正式化（附预期答案）

## 7. 环境坑（Windows 特供）

- **Python 3.14.4**，venv 在 `.venv`；控制台中文加 `PYTHONIOENCODING=utf-8`
- **segfault 139 偶发**（jieba/onnxruntime 启动期）：进程可能静默死掉——不要链式命令掩盖退出码，
  靠缓存文件时间戳验证是否真的执行了
- **内存压力**：本机 15.6 GB 常吃紧，后台长任务可能被系统回收——评估靠逐条缓存落盘，断了不丢
- 价格参考（2026-09 公开价，以官方为准）：Flash ¥1/2 每百万输入输出、Pro ¥3/6；
  硅基流动 BGE-M3/reranker 免费档。周报端到端实测 ≈ ¥0.05/期，月度 < ¥0.5

## 8. 资产清单

- 评估集：`data/eval/golden.json`(50) / `boundary.json`(30) / `adversarial.json`(20) / `regression.json`(20)
- 报告：`docs/eval_report.md`（指标表）· `docs/cost_latency.md`（成本延迟实测）· `docs/demo_script.md`（视频脚本）
- 数据底稿：`docs/data_readme.md`（预埋风险答案）· `docs/phase9-demo-plan.md`（PRD/排期/坑清单）
- 评估缓存：`outputs/eval_cache/`（gitignore，逐条 JSON，重跑复用）
