<h1 align="center">OfferClaw</h1>

<p align="center">
  <strong>一个长期运行、带状态的个人求职 AI Agent</strong><br>
  <em>A stateful, long-running personal AI agent for job hunting.</em>
</p>

<p align="center">
  画像 → 匹配 → 规划 → 执行 → 复盘 → 回到画像<br>
  <sub>Profile · Match · Plan · Execute · Reflect · Loop</sub>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.110%2B-009688?style=flat&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/LangGraph-0.2%2B-1C3C3C?style=flat" alt="LangGraph">
  <img src="https://img.shields.io/badge/ChromaDB-0.4%2B-FF6B35?style=flat" alt="ChromaDB">
  <img src="https://img.shields.io/badge/Playwright-Chromium-2EAD33?style=flat&logo=playwright&logoColor=white" alt="Playwright">
  <img src="https://img.shields.io/badge/智谱-GLM--4--Flash-0066FF?style=flat" alt="ZhipuAI">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/pytest-130%20passed-success?style=flat&logo=pytest&logoColor=white" alt="Tests">
  <img src="https://img.shields.io/badge/RAG_Recall%405-0.96-brightgreen?style=flat" alt="RAG">
  <img src="https://img.shields.io/badge/routes-28-blue?style=flat" alt="Routes">
  <img src="https://img.shields.io/badge/version-V4-purple?style=flat" alt="Version">
  <img src="https://img.shields.io/badge/status-portfolio--ready-orange?style=flat" alt="Status">
</p>

<p align="center">
  <strong>把"找工作"当成持续运行的工程项目。</strong><br>
  <sub>个人作品集 · 不自动投递 · 不伪造经历 · 不预测录用概率</sub>
</p>

---

## 项目数据

<table align="center">
<tr>
  <td align="center"><strong>130</strong><br><sub>pytest 通过</sub></td>
  <td align="center"><strong>28</strong><br><sub>FastAPI 路由</sub></td>
  <td align="center"><strong>0.96</strong><br><sub>RAG Recall@5</sub></td>
  <td align="center"><strong>160</strong><br><sub>RAG chunks</sub></td>
  <td align="center"><strong>13</strong><br><sub>LangGraph 节点</sub></td>
  <td align="center"><strong>3</strong><br><sub>多 Persona 回归</sub></td>
</tr>
</table>

---

## Why OfferClaw

> 求职过程通常被拆成"刷岗位 → 改简历 → 投 → 等"这种一次性动作。

这种方式的问题是：

- 简历和 JD 之间的**真实差距**没人告诉你，匹配靠感觉
- 学习计划和投递节奏**互相脱节**，今天该做什么靠记忆
- 每次投递、每次面试反馈**没有沉淀**，画像不更新
- 生成式工具能写漂亮文案，但**没有状态、没有约束、没有可解释性**

OfferClaw 的思路：用一个**带状态**的 Agent 把链路连起来——所有判断走 **Prompt 契约 + 规则代码双通路**，所有状态写入可读的 **Markdown 文件**，所有变更经同一个 **Orchestrator** 反向修正画像与计划。

---

## 核心能力

| 能力 | 说明 |
|---|---|
| **画像渐进收集** | 13 字段用户画像，按需 Onboarding，每次复盘自动回写更新 |
| **JD 匹配 + 缺口** | 输入一段 JD，输出结构化能力差距清单（带致命度 / 短期可补性元数据） |
| **学习路线规划** | 基于缺口生成 4 周路线，按周→按日两层任务展开 |
| **每日执行 + 复盘** | 每日计划 / 实际 / 偏离度判断，复盘结果回写画像 |
| **JD 定制简历段** | 给定 JD 自动从画像 + 故事库生成"专为这份 JD 写的"简历项目段 |
| **JD 半自动抽取** | 粘贴招聘页 URL，自动抓取（含 Playwright SPA 兜底）→ 落入候选池 |
| **今日建议** | 打开页面即看到"今天最该做什么"——由 Orchestrator 跨模块综合判断 |
| **本地 RAG 问答** | 顶部问答条直接查询全部 Prompt 契约 / 画像 / 投递记录 / 复盘日志 |
| **CareerFlow 编排** | LangGraph 8 节点串起完整求职流；条件路由按结论分流 |
| **ReAct Agent** | 一句自然语言驱动 6 个 OpenAI 兼容 Tool，无 KEY 也能跑 |
| **Trace 重放** | 每次 CareerFlow 落成 JSONL trace，可重放、可审计 |

---

## How It Works

```
                       用户输入一段 JD
                              │
                              ▼
                  ┌──────────────────────┐
                  │   profile_loader     │  读 user_profile.md
                  │   13 字段画像 + 缓存   │  按 JSON Schema 校验
                  └──────────┬───────────┘
                             │
                             ▼
              ┌────────────────────────────┐
              │  CareerFlow (LangGraph)    │  routed: 条件路由 4 分支
              │  profile → job_input →     │
              │  match → gap → plan →      │
              │  today → resume →          │
              │  application_suggest       │
              └──────────┬─────────────────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
         适合投递    中长期可转向    暂不建议
              │          │          │
              ▼          ▼          ▼
        full path  plan+today  gap-only  → END
              │          │          │
              └──────────┴──────────┘
                         │
                         ▼
              ┌────────────────────────────┐
              │  Observability             │  JSONL trace
              │  logs/traces/<id>.jsonl    │  /api/trace 重放
              └────────────────────────────┘

旁路：
  ReAct Agent (POST /api/agent)  ─→  Tool Registry (6 tools)
  RAG (LangGraph 4 节点)         ─→  ChromaDB (160 chunks)
  Memory Layers (V4)             ─→  Episodic / Semantic / Procedural
```

详见 [`docs/architecture.md`](docs/architecture.md)。

---

## Quick Start

```bash
# 1. 克隆 + 创建本地虚拟环境
git clone https://github.com/zhangyi-nb1/offerclaw.git
cd offerclaw
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

# 2. 配置本机 API 环境（已被 .gitignore 忽略）
cp .env.example .env.local
# 然后把 .env.local 里的 API Key 占位符替换为你自己的 Key。
# 百炼推荐配置见 .env.example：chat 走 OPENAI_*，embedding 走 EMBEDDING_PROVIDER=bailian。

# 2.5 如果切换了 embedding provider/model，重建对应 Chroma collection
python rag_ingest.py --rebuild

# 3. 启动 FastAPI 服务
python -m uvicorn rag_api:app --host 127.0.0.1 --port 8000

# 4. 浏览器打开任一控制台
#    /ui            — V2 6 卡片控制台（顶部 RAG 问答条 + 今日建议横条）
#    /ui/console    — V3 CareerFlow 8 步 Stepper（一页跑完整流程）
#    /docs          — Swagger（28 路由）
```

### 本机 Chrome 兜底

JD 半自动抽取会先用轻量请求抓正文；遇到 SPA 招聘页时，`job_discovery.py` 会优先调用本机 Google Chrome 的无头模式渲染页面，若本机没有 Chrome 或启动失败，再回退到 Playwright 自带 Chromium。

### 工程自检

```bash
python doctor.py                  # 10 项环境与文件健康检查
python verify_pipeline.py         # 6 步主链路端到端冒烟
python eval_match.py              # match_job 评估（status acc / direction acc）
python -m pytest tests/ -q        # pytest 130 passed / 3 skipped
python verify_docs.py             # 4 份关键文档指标口径一致性巡检
python normalize_applications.py  # applications.md 投递表 schema 校验
```

> `OPENAI_*` 用于 chat completion / Agent 推理；`EMBEDDING_PROVIDER`、`EMBEDDING_MODEL`、`RAG_COLLECTION_NAME` 用于 RAG 向量库切换。百炼可用 `DASHSCOPE_API_KEY`，旧智谱路径可用 `ZHIPU_API_KEY`。KEY 仅本地、绝不入 git。

JVS Claw 云部署见 [`deployment.md`](deployment.md)。

---

## V4 · 5 个 Agent 工程优化点

V4 把项目从「流程画板」推进到「真正可以被工程师 review 的 Agent 系统」。**5 个独立模块、66 个新增测试全部绿、不破坏 V3 任何回归。**

<table>
<tr>
<td width="50%" valign="top">

### ① Eval-driven Agent

- [`eval_match.py`](eval_match.py) + [`tests/match_eval_set.json`](tests/match_eval_set.json)
- 自建 **10 样本 × 3 档** 黄金集（适合 / 中长期 / 暂不建议）
- 双重审视：确定性 baseline + 可选 **LLM-as-judge**
- 当前 baseline status acc = **100%** / direction acc = **100%**

```bash
python eval_match.py           # 跑 baseline
python eval_match.py --judge   # 叠加 LLM 二次审视
```

</td>
<td width="50%" valign="top">

### ② Agentic Graph · 条件路由

- [`career_flow.py`](career_flow.py)::`build_routed_graph()`
- 同样 8 节点，**4 条不同后续路径**：
  - `suitable` → 全路径
  - `stretch` → plan + today, skip resume
  - `not_recommended` → gap + application_suggest only
  - `jd_too_short` → END
- 旧线性 flow 完整保留，不破坏 V3 回归

</td>
</tr>
<tr>
<td width="50%" valign="top">

### ③ Tool Ecology · ReAct Agent

- [`tools_registry.py`](tools_registry.py)：**6 个 OpenAI 兼容 Tool**
- [`react_agent.py`](react_agent.py)：deterministic + LLM 双模式
- 无 KEY 自动降级到 deterministic
- 一句自然语言 → 选 tool → 调 → 结论

```bash
curl -X POST localhost:8000/api/agent \
  -d '{"message":"今天该做什么？"}'
```

</td>
<td width="50%" valign="top">

### ④ Observability · 结构化 Trace

- [`observability.py`](observability.py)：JSONL TraceWriter
- 每次 CareerFlow 落成 `logs/traces/<id>.jsonl`
- `jq` / `grep` / `tail -f` 直接调试
- 新 API：`/api/trace`、`/api/trace/{id}`、`/api/flow/run_traced`

```bash
curl localhost:8000/api/trace?limit=20
curl localhost:8000/api/trace/{trace_id}
```

</td>
</tr>
<tr>
<td colspan="2" valign="top">

### ⑤ Profile Schema + 分层 Memory

- [`profile_schema.json`](profile_schema.json)：JSON Schema draft-07，13 字段类型 / 枚举 / 区间约束
- [`profile_loader.validate_profile()`](profile_loader.py)：实画像 + 3 个 persona fixture 零漂移
- [`memory_layers.py`](memory_layers.py)：认知心理学三层记忆
  - **Episodic** — append-only 事件流（`logs/memory/episodic.jsonl`）
  - **Semantic** — 沉淀偏好 KV（`logs/memory/semantic.json`）
  - **Procedural** — 学到的 SOP / 启发式（`logs/memory/procedural.json`）
- `distill_to_semantic()` 把 episodic 事件总结到 semantic 层

</td>
</tr>
</table>

---

## Tech Stack

| 层 | 选型 |
|---|---|
| **Agent 核心** | Python 3.10+ · OpenAI 兼容 Chat API（百炼 / 代理 / 智谱 fallback）· 仅 `requests`，无 LangChain / LlamaIndex |
| **RAG** | 可配置 Embedding provider（百炼 `text-embedding-v4` / 智谱 `embedding-3` fallback）· ChromaDB 本地持久化 · 自写分块 + 9 类 source_type 元数据 |
| **API** | FastAPI + Uvicorn · **28 路由**（24 业务 + 4 系统/UI）· Server-Sent Events 流式 · Swagger UI |
| **Orchestration** | LangGraph 声明式 StateGraph：RAG 4 节点 + CareerFlow 8 节点 + **条件路由变体**（V4） |
| **Tool Layer (V4)** | `tools_registry.py` 6 个 OpenAI 兼容 Tool · `react_agent.py` deterministic + LLM 双模式 |
| **Observability (V4)** | JSONL trace + `read_trace` / `list_traces` / `trace_career_flow` + 3 个新 API |
| **JD 抓取** | `requests` 快速通道 + Playwright Headless Chromium 兜底（覆盖字节 / 阿里 / 腾讯等 SPA 招聘页） |
| **State** | Markdown 文件 + `memory.json` 跨会话上下文 + `profiles/p*.json` 多 Persona · `profile_loader.py` 集中 13 字段解析 + mtime 缓存 + JSON Schema 校验 |
| **Memory (V4)** | 三层 `memory_layers.py`：Episodic（JSONL）+ Semantic（JSON KV）+ Procedural（学到的 SOP） |
| **Testing** | pytest **130 / 130**（+3 skipped 需 `OFFERCLAW_E2E=1`）· `match_eval_set.json`（10 样本）· `rag_eval_set.json`（50 题）· `doctor.py` / `verify_pipeline.py` / `verify_docs.py` / `normalize_applications.py` |
| **运行平台** | 本地 / JVS Claw（文件空间 + 定时任务） |

---

## Evaluation · 工程自检证据

> 评估基于**自建小规模评估集**，仅用于个人项目自检与回归对比，不代表通用基准。

| 指标 | 当前值 | 来源 / 备注 |
|---|---|---|
| **pytest** | **130 / 130 passed** (+3 skipped) | `python -m pytest tests/ -q` |
| **match_job baseline acc** | status **100%** · direction **100%** | `python eval_match.py`（10 样本 × 3 档） |
| **RAG Recall@5** | **0.96** | `python eval_rag.py`（50 题平均） |
| **RAG cross_doc Recall@5** | **1.00** | 跨文档子集 |
| **RAG MRR** | **0.67** | 知识库扩到 160 chunks 后 |
| **FastAPI 路由数** | **28**（Swagger 显示）= 24 业务 API + 4 系统/UI | V4 新增 4：`/api/agent` · `/api/trace` · `/api/trace/{id}` · `/api/flow/run_traced` |
| **ChromaDB 知识库** | **160 chunks** | 9 类 source_type |
| **工程体检** | **doctor 10 OK · 0 WARN · 0 ERR** | `python doctor.py` |
| **文档口径巡检** | **all green** | `python verify_docs.py` |
| **投递表校验** | **0 error** | `python normalize_applications.py` |
| **面试故事库** | **8 STAR+R** | [`interview_story_bank.md`](interview_story_bank.md) |
| **端到端链路** | **verify_pipeline 6 / 6** | `python verify_pipeline.py` |
| **SSE 首字延迟** | **< 2s** | 计划与简历流 |
| **多 Persona 回归** | **3 persona × multi-JD 差异化** | [`docs/persona_compare_report.md`](docs/persona_compare_report.md) |

完整现场输出固化在 [`docs/verification_report.md`](docs/verification_report.md)。

---

## Project Structure

```
offerclaw/
│
├─ Prompt 契约层（不变契约 · 全部入 Git）
│   SOUL.md · target_rules.md · source_policy.md
│   onboarding_prompt.md · job_match_prompt.md
│   plan_prompt.md · summary_prompt.md
│
├─ 核心代码（V1 → V4 演进）
│   agent_demo.py        # V1 Agent 核心 (tools.py)
│   match_job.py         # 规则版 JD 匹配（三档结论）
│   plan_gen.py          # 4 周路线生成
│   resume_builder.py    # JD 定制简历段
│   job_discovery.py     # JD 抓取（含 Playwright 兜底）
│   rag_*.py             # RAG + LangGraph 4 节点 + 工具循环
│   career_agent.py      # V2 Orchestrator（"今天最该做什么"）
│   career_flow.py       # V3 CareerFlow 8 节点 + V4 routed 变体
│   profile_loader.py    # V3 状态真实化 + V4 Schema 校验
│
├─ V4 新增模块
│   eval_match.py        # match_job 评估 + LLM-as-judge
│   tools_registry.py    # OpenAI 兼容 Tool 抽象 + 默认注册表
│   react_agent.py       # ReAct Agent（deterministic + LLM）
│   observability.py     # JSONL Trace + 重放
│   memory_layers.py     # Episodic / Semantic / Procedural
│   profile_schema.json  # 13 字段 JSON Schema
│
├─ FastAPI 层
│   rag_api.py           # 28 路由 · SSE 流 · Swagger
│
├─ 工程自检
│   doctor.py            # 10 项体检
│   verify_pipeline.py   # 6 步冒烟
│   verify_docs.py       # 文档口径漂移巡检
│   normalize_applications.py  # 投递表 schema 校验
│
├─ 运行时数据（部分入 Git，部分 .gitignore）
│   user_profile.md · daily_log.md · applications.md
│   jd_candidates.md · interview_story_bank.md
│   profiles/p1_zhangyi_ai.json / p2 / p3
│   chroma_db/ · logs/ · memory.json   ← .gitignore
│
├─ tests/                # pytest 130 + match/rag eval set
│
└─ docs/
    architecture.md · demo_script.md · v3_changelog.md
    verification_report.md · resume_pitch.md
    interview_qa.md · persona_compare_report.md
    project_one_pager.md · postmortem.md · ethical_use.md
    real_jd_run_nio_vas_v2.md · screenshots/
```

---

## Design Decisions

- **不依赖 Agent 框架**：核心 Agent 调用、工具循环、跨会话 memory 全部手写，便于在面试中拆解每一层逻辑
- **Prompt + 代码双通路**：关键判断（JD 匹配）必须两边都过，规则版作为 Prompt 版的回归基线
- **契约式 Prompt**：每份 Prompt 文件明确输入 / 步骤 / 输出 / 禁止条款，可像 API 一样回归测试
- **状态用文件而非数据库**：Markdown / JSON 直接 diff，故障与变更全部可读
- **声明式 RAG 工作流**：LangGraph 把"检索 → 提示拼装 → LLM → 工具调用"显式化为 4 节点，避免黑盒链路
- **抓取双通道 + 自动回退**：常规站点走 `requests`，SPA 自动回退 Playwright，控制成本同时覆盖主流招聘页
- **V4：Tool 与编排解耦**：所有能力暴露为 OpenAI 兼容 Tool；ReAct Agent / MCP / 第三方脚本从同一 `REGISTRY` 取，不重写 schema
- **V4：Trace 文件化**：每次 CareerFlow 落 JSONL，重放与审计零基础设施依赖

---

## Real-Application Reflow SOP · 真实投递回流

> 目标：用 OfferClaw 完成 ≥ 1 次**真实投递闭环**——抓 JD → CareerFlow 跑通 → 改简历 → 投出 → 状态机回填 → 复盘入 RAG。

```
1. 进 candidates 测试池       POST /api/discover         → jd_candidates.md 追加
2. CareerFlow 评估             POST /api/flow/run         → match_report + gaps + today
3. 决策分叉
   ├─ 适合投递                  → §4 生成简历
   └─ 其他三档                   → plan/4_weeks 中长期补能，本轮不投
4. 生成简历草稿                POST /api/resume/markdown  默认无 LLM 拿骨架
                              + POST /api/resume/build    SSE 流式 LLM 写定制段
5. 登记投递池                 applications.md 加一行     状态=准备投递
6. 真实投出                   状态改 已投递               POST /api/daily 追加日志
7. 回流证据                   HR 回复截图 → docs/screenshots/applications/ (脱敏)
8. 复盘入 RAG                 daily_log.md 写 1-2 句     python rag_ingest.py 入库
```

### 最小可交付证据集

- [x] **NIO VAS 实习 #1**：8 节点全过 / status=当前适合投递 / 0 errors — [`docs/real_jd_run_nio_vas_v2.md`](docs/real_jd_run_nio_vas_v2.md)
- [ ] 真实投递回流 #2：≥ 1 次新投递 + HR 反馈截图入 `docs/screenshots/applications/`

---

## Roadmap

- [x] **V1** — 画像 / 匹配 / 规划 / 执行 / 复盘五段 + Agent Demo
- [x] **V1.5** — RAG（LangGraph + ChromaDB）+ FastAPI 接口层
- [x] **V2** — 6 卡片控制台 + Orchestrator + JD 自动抓取 + JD 定制简历 + 多 Persona 回归
- [x] **V3 阶段 1-7（产品级 Agent 化）** — 状态真实化 · CareerFlow 8 节点 · Stepper UI · JD 排序 · 简历骨架 · RAG verification · 端到端验证 — [`docs/v3_changelog.md`](docs/v3_changelog.md)
- [x] **V3 收口审计** — `DEMO_PROFILE` 0 生产耦合 · `/api/info` 与 24 路由 0 漂移 · pytest 64/64
- [x] **真实投递回流 #1** — NIO VAS 8 节点全过 / 0 errors / 简历骨架 + daily log + applications 同步
- [x] **V4 · 5 个 Agent 工程优化点** — Eval-driven · Agentic Graph · Tool Ecology · Observability · Schema/Memory（pytest 64 → 130，新增 4 路由）
- [ ] 真实投递回流 #2 — ≥ 1 次新投递 + HR 反馈截图
- [ ] 简历最终可投递版本（Word / PDF）
- [ ] 1 分钟 Demo 视频（可选）
- [ ] RAG 评估集扩到 100 题（可选）
- [ ] match_eval_set 扩到 30 样本 + LLM-as-judge 集成 CI（可选）

完整推进记录见 [`PROJECT_STATUS.md`](PROJECT_STATUS.md)。

---

## Limitations · 硬边界

- **不自动投递** — 不会代为提交简历到任何平台；投递动作必须人工完成
- **JD 抓取仅半自动 · 不批量 · 不登录** — 一次只处理用户给定的单个 URL；不做门户扫描 / 翻页 / 列表遍历；不登录任何招聘平台、不绕验证码。详见 [`docs/ethical_use.md`](docs/ethical_use.md) §1.6
- **不伪造经历** — 简历草稿仅基于 `user_profile.md` 与 `interview_story_bank.md` 中的真实素材重组、强调和适配 JD，不会编造未发生的项目
- **不承诺录用概率** — 所有匹配结论是"差距分析 + 建议"，不输出录用率、面试通过率之类的数字预测
- **写入需人工确认** — 写入 `applications.md` / `user_profile.md` 等用户层文件的关键动作必须 UI 二次确认（详见 [`DATA_CONTRACT.md`](DATA_CONTRACT.md) §4.0 写入策略表）
- **个人作品集，非生产系统** — 单用户运行、本地存储、无多租户、无登录鉴权 / 限流 / 审计
- **指标规模小** — 自建评估集只覆盖本仓库内容，结论不推广到通用领域
- **LLM 输出不可强保证** — 尽管走 Prompt 契约，仍可能产生不符合规则的回答，需人工二次确认

---

## API Reference

> 28 routes total（V3 基线 24 + V4 新增 4）。完整 Swagger 在 `/docs`。

<details>
<summary><strong>展开查看完整路由清单</strong></summary>

### 系统 / UI

| Route | 用途 |
|---|---|
| `GET /` | 重定向到 `/ui` |
| `GET /ui` | V2 6 卡片控制台 |
| `GET /ui/console` | V3 CareerFlow 8 步 Stepper |
| `GET /health` | ChromaDB / 知识库健康检查 |
| `GET /api/info` | 元信息 + 路由清单 |
| `GET /docs` | Swagger UI |

### 画像 / RAG / 匹配

| Route | 用途 |
|---|---|
| `GET /api/profile` | 用户画像摘要 |
| `POST /api/query` | RAG 问答（一次性） |
| `POST /api/stream` | RAG 问答（SSE 流式） |
| `POST /api/search` | 仅检索（不生成答案） |
| `POST /api/match` | 岗位匹配（三档结论 + 缺口） |

### 计划 / 日志 / 简历 / 今日

| Route | 用途 |
|---|---|
| `POST /api/plan` | 4 周路线规划 |
| `POST /api/plan/stream` | 4 周路线（SSE 流式） |
| `GET /api/daily` | 今日 daily_log + 最近 7 天摘要 |
| `POST /api/daily` | 向 daily_log.md 追加今日条目 |
| `GET /api/resume` | 简历素材聚合 |
| `POST /api/resume/build` | JD 定制简历段（LLM） |
| `POST /api/resume/build/stream` | JD 定制简历段（SSE） |
| `POST /api/resume/markdown` | 完整 Markdown 简历草稿（默认无 LLM） |
| `GET /api/today` | 今日建议（聚合投递池 + 日志） |

### JD Discovery

| Route | 用途 |
|---|---|
| `POST /api/discover` | JD 半自动抽取 |
| `GET /api/jd/queries` | 根据 profile 生成搜索关键词组合 |
| `POST /api/jd/rank` | 对一组候选 JD 调 match_job 排序 |

### CareerFlow 编排

| Route | 用途 |
|---|---|
| `POST /api/flow/run` | CareerFlow 主流程（8 节点全状态） |
| `POST /api/reset` | 清空对话历史 |

### V4 新增

| Route | 用途 |
|---|---|
| `POST /api/agent` | ReAct Agent（deterministic + LLM 自动降级） |
| `GET /api/trace` | 列最近 N 条 trace |
| `GET /api/trace/{trace_id}` | 读回单条 trace 全部事件 |
| `POST /api/flow/run_traced` | routed CareerFlow + 自动落 JSONL trace |

</details>

---

## Citing & Contact

个人作品集项目，未配置开源许可。引用或参考请在 [issue](https://github.com/zhangyi-nb1/offerclaw/issues) 中联系。

<p align="center">
  <sub><em>Built around the discipline of stateful agent engineering.</em><br>
  <a href="https://github.com/zhangyi-nb1/offerclaw">github.com/zhangyi-nb1/offerclaw</a></sub>
</p>
