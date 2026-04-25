# OfferClaw · 数据契约（DATA_CONTRACT）

> 版本：v1.0 · 2026-04-25  
> 用途：明确 OfferClaw 中所有 Markdown / JSON / 目录的边界、写入权限和 Git 提交策略，防止"长期状态层"被误改、误删、误推。

---

## 0. 总原则

OfferClaw 是一个 **长期状态型 Agent 系统**，必须区分两类资产：

| 类别 | 含义 | 写入权限 | 入 Git |
|---|---|---|---|
| **User Layer** | 用户私有的事实状态（画像、日志、投递、故事） | 仅在用户确认后由 Agent 追加；不得静默覆盖 | 仅模板/示例入 Git，真实数据视情况 |
| **System Layer** | 系统规则、Prompt、代码、文档 | 可由开发者直接更新并版本化 | ✅ 全部入 Git |
| **Runtime / Secrets** | 运行时产物、密钥、向量库 | 自动产生 | ❌ 一律 .gitignore |

> 一句话：**用户层负责"我是谁、我做了什么"；系统层负责"OfferClaw 是什么、怎么做"。两者不能互相覆盖。**

---

## 1. User Layer（用户事实状态层）

| 文件 / 目录 | 角色 | 自动写入策略 | Git 策略 |
|---|---|---|---|
| `user_profile.md` | 用户画像（基础信息、技能、方向） | **必须用户确认**；只允许追加 / 更新 §0 元信息 + 已存在字段；不得新增章节 | ⚠️ 当前作为 demo 入库；真实使用时建议改 `user_profile.example.md` |
| `daily_log.md` | 每日学习/求职日志 | Agent 可在用户结束当日操作时追加一行；不得回溯改写 | ✅ 入库（脱敏） |
| `applications.md` | 真实投递追踪表（见 §4.2） | Agent 追加新行；状态变更必须由用户触发 | ⚠️ 模板入库，真实数据按需 |
| `interview_story_bank.md` | 面试 STAR+R 故事库 | 用户主动写入；Agent 可生成草稿但不直接合并 | ✅ 入库 |
| `jd_candidates.md` | JD 测试池（横向对比，不等于投递） | Agent 可追加 JD 摘录 | ✅ 入库 |
| `plans/` | LLM 生成的 N 周学习计划 | Agent 自由写入新文件，不覆盖旧文件 | ❌ .gitignore（产物） |
| `summaries/` | 单日 / 周度复盘 | Agent 自由写入新文件 | ❌ .gitignore |
| `memory.json` | Agent 长期记忆 KV | Agent 读写 | ❌ .gitignore |
| `memory/` | 历史会话 / 长上下文存档 | Agent 写入 | ❌ .gitignore |
| `logs/` | JSON 日志 | 中间件自动写 | ❌ .gitignore |
| `profiles/p*_*.json` | 多 persona 测试样本 | 仅作回归测试，不代表真实用户 | ✅ 入库 |

---

## 2. System Layer（系统规则与代码层）

### 2.1 Prompt 与规则文件
| 文件 | 角色 |
|---|---|
| `SOUL.md` | OfferClaw 的产品宪法 / 不可逾越红线 |
| `target_rules.md` | 目标方向白/黑名单、匹配阈值 |
| `source_policy.md` | 信息源可信度分级（A/B/C） |
| `onboarding_prompt.md` | 首次接入新用户的 Prompt |
| `job_match_prompt.md` | LLM 岗位匹配指令 |
| `plan_prompt.md` | 学习计划生成指令 |
| `summary_prompt.md` | 复盘生成指令 |

### 2.2 代码
| 文件 | 角色 |
|---|---|
| `match_job.py` | 规则版岗位匹配（三档结论） |
| `plan_gen.py` | 4 周计划生成 |
| `summary_tool.py` | 复盘工具 |
| `pipeline.py` | match→plan→log 流水线 |
| `rag_ingest.py` / `rag_query.py` / `rag_graph.py` / `rag_tools.py` / `rag_agent.py` | RAG 全栈 |
| `rag_api.py` | FastAPI 服务层 |
| `logging_utils.py` | 结构化日志中间件 |
| `eval_rag.py` | RAG 召回 / MRR 评估 |
| `tools.py` | Agent 自定义工具 |
| `agent_demo.py` | 最小 Agent demo |
| `doctor.py` | 工程健康检查（见 §4.6） |
| `verify_pipeline.py` | 主链路端到端验证（见 §4.7） |
| `tests/` | pytest 单测与回归 |
| `static/` | 前端控制台 |

### 2.3 文档
| 文件 | 角色 |
|---|---|
| `README.md` | 项目门面 |
| `PROJECT_STATUS.md` | 进度仪表盘（手动维护，每个 Sprint 末更新） |
| `docs/architecture.md` | 4 张 Mermaid 架构图 |
| `docs/demo.md` | 7 步演示流程 |
| `docs/resume_pitch.md` | 简历短/中/JD 对照三档 |
| `docs/interview_qa.md` | 10 题面试卡 |
| `docs/project_one_pager.md` | 一页纸（见 §4.3） |
| `docs/postmortem.md` | 技术复盘（见 §4.9） |
| `docs/ethical_use.md` | 伦理边界（见 §4.5） |
| `DATA_CONTRACT.md` | **本文件** |
| `RAG_QUICKSTART_REPORT.md` | RAG 接入复盘 |
| `AGENT_DEMO.md` | Agent demo 说明 |
| `deployment.md` | JVS 云部署记录 |

---

## 3. Runtime / Secrets（绝不入 Git）

| 文件 / 目录 | 说明 |
|---|---|
| `.env.local` / `.env*` | 智谱 API Key 等密钥 |
| `chroma_db/` | 本地向量库，体积大且与机器相关 |
| `__pycache__/` / `.pytest_cache/` / `.venv/` | Python 产物 |
| `.vscode/` / `.idea/` / `.claude/` | IDE / Agent CLI 配置 |
| `logs/` `summaries/` `plans/` `memory.json` `memory/` | 运行时输出 |
| `1.txt` / `1` / `2` 等临时文件 | 不要加入 |

**任何含真实邮箱、电话、招聘方内部联系方式、未公开 JD 全文的文件，禁止入 Git。**

---

## 4. 写入与变更追踪规则

### 4.1 自动写入边界

| 场景 | 是否允许 Agent 自动写 |
|---|---|
| 在 `daily_log.md` 末尾追加今日复盘 | ✅ |
| 在 `plans/` 新建 4 周计划文件 | ✅ |
| 在 `summaries/` 新建复盘文件 | ✅ |
| 在 `applications.md` 新增一行投递（状态=已评估） | ✅ |
| 修改 `applications.md` 中投递状态（如→已投递、→面试中） | ❌ 必须用户确认 |
| 修改 `user_profile.md` 中"基础信息"姓名/学校 | ❌ 必须用户确认 |
| 在 `user_profile.md` 中追加"§4 项目"新条目 | ⚠️ Agent 给出草稿，用户合并 |
| 修改 `SOUL.md` / `target_rules.md` / `source_policy.md` | ❌ 仅开发者通过 PR |
| 写入 `interview_story_bank.md` 新故事 | ⚠️ Agent 出草稿，用户终审 |

### 4.2 变更追溯
- 所有 System Layer 改动必须经 git commit；commit message 用前缀：`feat:` / `fix:` / `docs:` / `chore:` / `test:` / `refactor:`
- User Layer 改动如果由 Agent 触发，需在 `daily_log.md` 留一行"【系统更新】§X 由 OfferClaw 在 YYYY-MM-DD 追加"
- `PROJECT_STATUS.md` 在每个 Sprint 收尾时更新一次"最近变更"段

### 4.3 信息源可信度（与 `source_policy.md` 对齐）
- A 级：官网 / 公司官方招聘页 / 政府文件 → 可直接进入 `user_profile.md` 与 `applications.md`
- B 级：知名媒体 / LinkedIn / 脉脉 → 进入 `jd_candidates.md` 摘录段，必须标注来源
- C 级：匿名爆料 / 论坛传闻 → 仅供参考，不写入 user/applications 层

---

## 5. 命名约定

- Markdown 文件：小写下划线 `.md`（例外：`README.md`、`SOUL.md`、`PROJECT_STATUS.md`、`DATA_CONTRACT.md` 全大写传统）
- 计划：`plans/plan_YYYYMMDD_<主题>.md`
- 复盘：`summaries/summary_YYYYMMDD.md` / `summary_week_YYYY_WW.md`
- 测试 persona：`profiles/p<编号>_<标签>.json`
- 测试代码：`tests/test_<模块>.py`

---

## 6. 演进策略

随着项目演进，本契约也会改：
1. 真实投递开始后：把 `applications.md` 拆分为 `applications.example.md`（公开）+ `applications.md`（gitignore）。
2. 接入数据库后：`memory.json` / `applications.md` 迁到 SQLite，本契约新增 §7 数据库表设计。
3. 引入多用户：把 `user_profile.md` 改造为 `users/<uid>/profile.md`，本契约更新 User Layer 索引方式。

---

## 7. 不变量（任何时候都不能违反）

1. **不得**把含真实 API Key、密码、未脱敏简历 PDF 的文件入 Git。
2. **不得**让 Agent 在用户未确认时覆盖 `user_profile.md` 已有事实字段。
3. **不得**把 `applications.md` 中"已投递 / 面试中"等敏感状态自动改为"已拒绝"。
4. **不得**绕过 `target_rules.md` 与 `SOUL.md` 强制简历内容（杜绝伪造经历）。
5. **必须**在删除 / 重命名任何 System Layer 文件时同步更新本契约 §2 表格。
