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
| 修幻觉三层防线 + pytest 单测 36 条 | ✅ | 2a3265d |
| 修 G11：重试 3 次/32k + 上下文 Top-12 + 守卫句边界去「；」 | ✅ | b041c5f |
| 周报生成数据驱动化（清点→规划→章节按数据源制定；范围默认仅上传） | ✅ | 2026-09-24（未提交） |

Day 6 最终成绩（`docs/eval_report.md`，黄金集 50/50 完整口径）：回归 20/20、对抗 20/20（硬门槛）、
边界 30/30、检索召回@20 94.9% / Top5 81%、风险召回 14/15=93%、引用准确 100%/97%、要点覆盖 87%。
**两项未达标**：①必备引用覆盖率 74.4%（目标 90%，三桶归因：Top-20 未命中 4 / 排序低于 Top-8 9 / 已给上下文未标注 7）
②幻觉率 judge 轨 5.7%（目标 ≤5%；**混合口径快照**——三层修复已实施并在 11 条新口径缓存上验证编造归零，
完整重验待跑，口径说明见报告 §6.4/§8）。

## 2. 如何运行（环境已就绪）

```bash
cd C:\Users\ASUS\02cc\filmops-copilot
.venv\Scripts\python -m streamlit run streamlit_app.py   # UI：http://localhost:8501
```

- `.env` 已配置（勿提交）、索引已建（`data/index/`，gitignore）、最新周报在 `outputs/weekly_report_*.md`
- CLI：`search_cli.py`（检索）、`generate_cli.py --report [--scope uploads|all] --risk --actions --adversarial`
  （生成；`--report` 走数据驱动周报，`--scope` 默认 all、uploads=仅 manifest 注册源；范围空/检索空退出码 1）、
  `run_eval.py --all/--golden/--missing/--report`（评估，带逐条缓存，重跑自动跳过已过条目；
  `--missing` 只补跑无缓存条目，已失败条目沿用缓存不扰动报告）
- 单条重跑：`run_eval.py --golden --force --item G11`（可多次 --item；只写缓存不重生成报告，
  保护 eval_report.md §3.3/§6.4/§8 的手工段落）
- 单测：`.venv\Scripts\python -m pytest tests/`（58 条，秒级、无 API 调用；单一事实来源
  `scripts/run_eval.py` 的 REGRESSION_CHECKS/PARSER_CHECKS；本机低内存下合并跑 tests/ 可能
  segfault 139，按文件分开跑即可）
- 换机器：`pip install -r requirements.txt` → 复制 `.env` → `make_synthetic_data.py` → `build_index.py`

## 3. 架构速览

数据流：多源文件 → 解析清洗（统一 Entry）→ 切块（表格行/聊天窗口/递归 512+80）→
Chroma 向量 + BM25（jieba）→ 混合检索（向量 0.7 + BM25 0.3）→ BGE Reranker Top-20→5/8 →
DeepSeek 生成（周报/风险/行动项）→ 引用后校验 + 置信度三档 + 越权守卫 + 转人工路由 →
人工编辑确认 → Markdown 导出 + SQLite 反馈审计。

关键文件职责：
- `app/ingest.py` 导入清洗 · `app/parsers.py` 3 类解析器 · `app/retriever.py` 混合检索+Rerank
- `app/generator.py` 生成层（系统提示词/引用校验/置信度/守卫/周报 15 查询 MAX 40 块；
  数据驱动周报 `generate_report_from_data`：清点 → `plan_report` 规划查询/章节 → 检索 → 生成；
  旧 `generate_report` 保留但不再被调用；`make_system_prompt(project_name, snapshot_date)` 参数化，
  默认渲染逐字节等于历史 SYSTEM_PROMPT——改模板必须同步 tests/test_report_planner.py 的冻结文本）
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
- **检索 Top-12 上下文**是现行统一口径（2026-09-22 由 Top-8 扩窗，b041c5f；汇总类问题跨文件多证据）
- **数据驱动周报口径（2026-09-24）**：周报 = 先清点数据源（_inventory_desc）→ LLM 规划检索查询(8–15)
  与章节(4–8)（plan_report，PLAN_SYSTEM_PROMPT）→ 按计划检索生成。日期（标题/快照）由
  `_inventory_dates` 按块元数据确定性计算，**LLM 不输出日期**。规划失败（JSON 重试耗尽/API 异常）
  走确定性 FALLBACK_QUERIES/FALLBACK_SECTIONS，永不抛异常。风险/行动项/草稿用动态渲染的系统提示词，
  10 条硬性规则不变
- **周报数据范围**：UI 默认「仅上传数据」（manifest 注册源），可切「全部数据源」；CLI `--scope` 默认 all
  （新机器无上传时 CLI 仍可用）。白名单按 `metadata.source_file` 精确匹配，过滤插在粗排后、rerank 前
  （rerank 后过滤会让域外块挤占 top_n 饿死域内证据）；`gather_report_hits` 只在 whitelist 非 None 时
  转发 kwarg（R19 假 retriever 签名兼容，勿"简化"成无条件转发）

## 5. 已知问题与局限（诚实清单，不掩盖）

1. **必备引用覆盖率 74.4% 未达 90%**：三桶归因=Top-20 未命中 4 处 + 排序低于 Top-8 9 处 + 已给上下文未标注 7 处。
   改进方向：查询改写扩展召回、上下文窗口扩大、引用完整性后校验器
2. **幻觉率 judge 轨 5.7% 未达 ≤5%（混合口径快照）**：三层修复已实施（commit 2a3265d）——
   ①断言-证据一致性后校验 v2（带引用分句字段值/数字回查块文本；无引用分句按引用契约移除
   字段键值/部门裸词/「若干、均为」概括；加粗剥离/未提供白名单/列表标记重挂/句级引用继承）
   ②chat 截断检测（句末无标点或表格列数不齐 → 翻倍预算重生成）③judge 口径修正（snippets 带
   ref_id 头，来源归属与"未提供"声明不计编造）。第二轮重跑 11 条（G01–G11）编造归零已验证方向，
   完整 50 条重验待跑（`--golden --force`）
3. **R15 真漏检**：送审冲突只归"延期"未归"合规"——影响转人工路由（合规→法务），值得后续修
4. **R03/R06 类型分歧**：模型归"延期"，注册表是"依赖/合规"——judge 按实质口径判检出，但路由同样受影响
5. judge 自身有偏差，报告结论是"样本内表现"，需人工抽查
6. 已知崩溃类坑（已修）：BM25 零命中、合并单元格只读、judge 误报编造、空输出重试
7. 黄金集 9 条补跑已于 2026-09-22 完成（8/9 过），评估到 50/50 完整口径
8. **评估缓存当前为混合口径**（2026-09-22 第二轮重跑中途停止）：黄金集 G01–G10 为新口径
   （fidelity_dropped 字段在即新口径），G11 为 b041c5f 修复前第 4 次验证缓存（覆盖 0.667，
   守卫去「；」前的误删口径），G12–T05 为第一轮；边界/对抗集仍是 Day 6 原始缓存，
   提示词/守卫变更后未重验。`--report` 按当前缓存重算，报告 §6.4/§8 已注明
9. 第二轮部分重跑观察：G11 空回答（chat 空输出重试两次仍为空——推理模型思考吃满预算的偶发形态）；
   G03/G09/G10 覆盖回退（0.667–0.75，LLM 非确定+新提示词偶发效应，未及排查）——这些都以
   「待办」记着，不掩盖
10. **G11 已修（2026-09-22，b041c5f）**：①chat 空输出/截断重试最多 3 次调用、预算上限 32k
    ②生成上下文 Top-8→12（黄金集/风险问答；周报每路 5→12 且 40 块上限不变）③守卫 v2 句边界
    去「；」——修复系统性误删缺陷（模型「字段清单；备注 [N]。」式输出时，编号被「；」切到
    后一句，前段字段分句落入无引用分支被删；现编号继承整句，字段值回查块文本后保留）。
    验证：4 次正式评估重跑空输出零复现、必备引用 3/3，覆盖 2×1.0/2×0.667（0.667 均为③修复
    前误删所致，修复后原文对比调试确认三要点字段全部保留）；守卫修复后的评估重跑被本机
    内存压力回收，待再跑 2 次确认稳定 1.0。③对全部问答条目生效，G03/G09/G10 类覆盖回退
    可能一并受益
11. **数据驱动周报的已知取舍（2026-09-24）**：①白名单按 source_file 精确匹配——上传与标准源
    同名的文件会把标准数据纳入「仅上传数据」范围（Demo 接受，产品化应按 manifest 注册来源过滤）
    ②周报正文不接 _fidelity_guard（与旧路径一致，靠引用后校验 + 人工编辑兜底）
    ③快照=范围内数据最新日期（含未来计划日，如补拍 9-27），与演示快照 9-20 口径并存
    ④plan_report 失败路径不计 LLM 用量（_chat_json 失败时 usage 已丢，Demo 接受）
    ⑤规划器输出经 _clean_plan 清洗（去 #/换行、限长、截断），但 LLM 规划的查询质量未纳入评估集

## 6. 待办（按优先级）

- [ ] G11 收尾验证：`--golden --force --item G11` 再跑 2 次确认覆盖稳定 1.0（本机低内存，
      后台任务曾被回收——一次跑一条、别并行）
- [ ] 完整重验（`--golden --force` → `--boundary --force` → `--adversarial --force`，各约 15-45 分钟；
      窗口 Top-12 + 守卫去「；」对全体条目生效，重验后指标可能变化，报告手工段落需同步校对）
- [ ] 重验后排查 G03/G09/G10 覆盖回退是否被守卫修复连带改善
- [ ] Demo 视频录制（脚本 `docs/demo_script.md`；或投递 3 张截图：检索溯源/周报草稿/指标表）
- [ ] 公开仓库前把 LICENSE 署名从 ASUS 改成真实姓名/GitHub 用户名；最后核一遍 secrets
      （已查：tracked 零密钥、`.env` 已 ignore、`.env.example` 仅占位符）
- [ ] 可选优化（对应报告改进计划 P0-P2）：引用完整性后校验器、风险类型路由对齐（R15/R03/R06）、
      查询改写扩展召回
- [ ] 可选：把 `data/eval/golden_seed.json` 的开发期自测 query 正式化（附预期答案）
- [x] 已办：断言-证据一致性后校验 + 提示词规则 9/10 + 截断重试 + judge 口径修正（2a3265d）、
      pytest 单测 36 条、LICENSE（MIT）、day1-day7 里程碑标签、G11 三层修复 + `--item`
      单条重跑标志 + 守卫单测 38 条（b041c5f）、周报数据驱动化（清点→规划→检索→生成 +
      `--scope` + UI 范围切换 + 单测 58 条，2026-09-24 未提交）

## 7. 环境坑（Windows 特供）

- **Python 3.14.4**，venv 在 `.venv`；控制台中文加 `PYTHONIOENCODING=utf-8`
- **segfault 139 偶发**（jieba/onnxruntime 启动期）：进程可能静默死掉——不要链式命令掩盖退出码，
  靠缓存文件时间戳验证是否真的执行了
- **内存压力**：本机 15.6 GB 常吃紧，后台长任务可能被系统回收——评估靠逐条缓存落盘，断了不丢
- 价格参考（2026-09 公开价，以官方为准）：Flash ¥1/2 每百万输入输出、Pro ¥3/6；
  硅基流动 BGE-M3/reranker 免费档。周报端到端实测 ≈ ¥0.05/期，月度 < ¥0.5

## 8. 资产清单

- 评估集：`data/eval/golden.json`(50) / `boundary.json`(30) / `adversarial.json`(20) / `regression.json`(20)
- 报告：`docs/eval_report.md`（8 段结构：评估集/指标表/Badcase/归因/改进计划/复现方式/成本/局限，由 `run_eval.py --report` 按缓存数据驱动生成；§6.4/§8 的混合口径说明与 §3.3 G11 归因为手工补充，重生成会覆盖，注意保留）· `docs/cost_latency.md`（成本延迟实测）· `docs/demo_script.md`（视频脚本）
- 单测：`tests/`（38 条，包装 `run_eval.py` 的确定性检查函数，单一事实来源）· `conftest.py` · `LICENSE`（MIT）
- 数据底稿：`docs/data_readme.md`（预埋风险答案）· `docs/phase9-demo-plan.md`（PRD/排期/坑清单）
- 评估缓存：`outputs/eval_cache/`（gitignore，逐条 JSON，重跑复用；当前为两轮混合口径，见 §5.8）
