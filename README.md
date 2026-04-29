# OfferClaw

> 一个长期运行、带状态的个人求职 AI Agent。
> 把"找工作"当成持续运行的工程项目：画像 → 匹配 → 规划 → 执行 → 复盘 → 回到画像。

个人作品集项目（V2，功能主体完成）。**不是**生产级商业系统，**不会**自动投递、不伪造经历、不预测录用概率。

---

## Why OfferClaw

求职过程通常被拆成"刷岗位 → 改简历 → 投 → 等"这种一次性动作，问题是：

- 简历和 JD 之间的**真实差距**没人告诉你，匹配靠感觉
- 学习计划和投递节奏**互相脱节**，今天该做什么靠记忆
- 每次投递、每次面试反馈**没有沉淀**，画像不更新
- 生成式工具能写漂亮文案，但**没有状态、没有约束、没有可解释性**

OfferClaw 的思路是用一个带状态的 Agent 把这条链路连起来：所有判断走 Prompt 契约 + 规则代码双通路，所有状态写入可读的 Markdown 文件，所有变更通过同一个 Orchestrator 反向修正画像与计划。

---

## What It Does

| 用户视角的能力 | 一句话说明 |
|---|---|
| **画像渐进收集** | 12 节用户画像，按需 Onboarding，每次复盘自动回写更新 |
| **JD 匹配 + 缺口** | 输入一段 JD，输出结构化能力差距清单（带致命度 / 短期可补性元数据） |
| **学习路线规划** | 基于缺口生成 4 周路线，按周→按日两层任务展开 |
| **每日执行 + 复盘** | 每日计划 / 实际 / 偏离度判断，复盘结果回写画像 |
| **JD 定制简历段** | 给定 JD 自动从画像 + 故事库生成"专为这份 JD 写的"简历项目段 |
| **JD 半自动抽取** | 粘贴招聘页 URL，自动抓取（含 Playwright SPA 兜底）→ 落入候选池 |
| **今日建议** | 打开页面即看到"今天最该做什么"——由 Orchestrator 跨模块综合判断 |
| **本地 RAG 问答** | 顶部问答条直接查询全部 Prompt 契约 / 画像 / 投递记录 / 复盘日志 |

---

## Demo

启动后浏览器打开 `http://127.0.0.1:8000/ui`：6 卡片控制台 + 顶部 RAG 问答条 + 今日建议横条，无需后台命令。

- 1 分钟现场演示脚本：[`docs/demo_script.md`](docs/demo_script.md)
- 现场可复现的证据链（doctor / pytest / RAG eval / `/health` / 一次完整查询）：[`docs/verification_report.md`](docs/verification_report.md)

---

## Quick Start

```bash
git clone https://github.com/zhangyi-nb1/offerclaw.git
cd offerclaw
pip install -r requirements.txt

# 配置智谱 API Key（已被 .gitignore 忽略）
echo "ZHIPU_API_KEY=你的智谱密钥" > .env.local

# 一键启动（含 6 卡片 UI）
python -m uvicorn rag_api:app --host 127.0.0.1 --port 8000
```

打开 `http://127.0.0.1:8000/ui` 即可使用。Swagger 文档在 `/docs`。

工程自检 / 端到端冒烟：

```bash
python doctor.py            # 9 项环境与文件健康检查
python verify_pipeline.py   # 6 步主链路验证
```

JVS Claw 部署见 [`deployment.md`](deployment.md)。

---

## Architecture

```
浏览器  http://127.0.0.1:8000/ui
   ↓
┌────────────────────────────────────────────────────────────┐
│  今日建议横条   GET /api/today  ← career_agent.py（Orchestrator） │
├──────┬───────┬──────┬──────┬──────┬─────────────────────────┤
│ ① 画像 │ ② JD  │ ③ 缺口 │ ④ 计划 │ ⑤ 每日 │ ⑥ 简历                  │
│profile│match  │ gap  │plan  │daily │resume/build            │
│       │discover│      │stream│ log  │stream                  │
└──────┴───────┴──────┴──────┴──────┴─────────────────────────┘
                            ↓
              ┌─────────────────────────────┐
              │  FastAPI（19 路由 · SSE 流式）│
              └──────────────┬──────────────┘
                             ↓
              ┌─────────────────────────────┐
              │  LangGraph 4 节点 StateGraph │
              │  retrieve → prompt → llm → tools │
              └──────────────┬──────────────┘
                             ↓
              ┌─────────────────────────────┐
              │  ChromaDB（160 chunks）      │
              │  8 类 source_type 元数据     │
              └─────────────────────────────┘

旁路：job_discovery.py（Playwright SPA 抓取）· resume_builder.py（JD 定制简历段）
```

完整文字版与 V1 / V1.5 演进图见 [`docs/architecture.md`](docs/architecture.md)。

---

## Core Capabilities

按交付到用户面前的价值组织：

1. **持续状态**：`user_profile.md` / `daily_log.md` / `applications.md` 是真正的运行时状态，每次操作都读写真实文件，不靠会话内存。
2. **双通路判断**：JD 匹配同时存在 Prompt 契约版（`job_match_prompt.md`）和规则代码版（`match_job.py`），互为兜底与回归基线。
3. **声明式编排**：RAG 走 LangGraph 4 节点 StateGraph + 条件边工具循环，工具调用可被自动路由。
4. **流式响应**：计划生成与简历草稿走 Server-Sent Events，首字延迟 < 2s。
5. **主动 Orchestrator**：`career_agent.py` 跨模块读 profile / log / 投递记录，输出"今日最该做什么"。
6. **可解释**：所有 JD 缺口带 `[致命度]` / `[短期性]` 元数据；复盘带"偏离度判断"。
7. **多 Persona 回归**：`profiles/p*.json` 参数化 3 份用户画像，同一 JD 给出明显差异化结论，证明非单用户硬编码。

---

## Tech Stack

| 层 | 选型 |
|---|---|
| **Agent 核心** | Python 3.10+ · 智谱 GLM-4-Flash（OpenAI 兼容 function calling）· 仅 `requests`，无 LangChain / LlamaIndex |
| **RAG** | 智谱 `embedding-3`（2048 维）· ChromaDB 本地持久化 · 自写分块（RecursiveCharacterTextSplitter）+ 8 类 source_type 元数据 |
| **API** | FastAPI + Uvicorn · 19 路由（13 核心 + 6 辅助）· Server-Sent Events 流式 · Swagger UI |
| **Orchestration** | LangGraph 声明式 StateGraph（4 节点 + 条件边）· `career_agent.py` 跨模块状态聚合 |
| **JD 抓取** | `requests` 快速通道 + Playwright Headless Chromium 兜底（覆盖字节 / 阿里 / 腾讯等 SPA 招聘页） |
| **State** | Markdown 文件 + `memory.json` 跨会话上下文 + `profiles/p*.json` 多 Persona |
| **Testing** | pytest · `tests/rag_eval_set.json`（自建 50 题 3 桶）· `doctor.py`（9 项体检）· `verify_pipeline.py`（6 步冒烟） |
| **运行平台** | 本地 / JVS Claw（文件空间 + 定时任务） |

---

## Evaluation

> 评估基于**自建小规模 RAG 评估集**：50 题、3 桶（fact / explain / cross_doc），开源在 [`tests/rag_eval_set.json`](tests/rag_eval_set.json)。仅用于个人项目自检与回归对比，不代表通用基准。

| 指标 | 当前值 | 备注 |
|---|---|---|
| RAG Recall@5 | **0.96** | 50 题平均 |
| RAG cross_doc Recall@5 | **1.00** | 跨文档子集 |
| RAG MRR | **0.67** | 知识库扩到 160 chunks 后较 118 chunks 时的 0.74 略降，召回率上升换来排序难度 |
| FastAPI 路由数 | **19** | 13 核心业务 + 6 辅助/系统，含 2 条 SSE |
| ChromaDB 知识库 | **160 chunks** | 覆盖 8 类 source_type |
| pytest | **37 / 37** | 另有 3 个 e2e 默认跳过，需 `OFFERCLAW_E2E=1` |
| 工程体检 | **doctor 9 OK** | 见 `python doctor.py` |
| 端到端链路 | **verify_pipeline 6 / 6** | 见 `python verify_pipeline.py` |
| SSE 首字延迟 | **< 2s** | 计划与简历流 |
| 多 Persona 回归 | **3 persona × multi-JD 差异化** | 报告：[`docs/persona_compare_report.md`](docs/persona_compare_report.md) |

完整现场输出固化在 [`docs/verification_report.md`](docs/verification_report.md)。

---

## Project Structure

```
offerclaw/
├─ Prompt 契约层（不变契约）
│   SOUL.md · target_rules.md · source_policy.md
│   onboarding_prompt.md · job_match_prompt.md
│   plan_prompt.md · summary_prompt.md
│
├─ 代码实现
│   agent_demo.py · tools.py            # V1 Agent 核心
│   match_job.py · plan_gen.py          # 规则版匹配 / 规划
│   rag_*.py                            # RAG + LangGraph + FastAPI
│   career_agent.py                     # V2 Orchestrator
│   job_discovery.py                    # JD 抓取（含 Playwright）
│   resume_builder.py                   # JD 定制简历段
│   doctor.py · verify_pipeline.py      # 工程自检
│
├─ 运行时数据
│   user_profile.md · daily_log.md
│   jd_candidates.md · applications.md
│   memory.json · profiles/p*.json · chroma_db/
│
├─ tests/
│   pytest 套件 + rag_eval_set.json
│
└─ docs/
    architecture.md · demo_script.md
    verification_report.md · resume_pitch.md
    interview_qa.md · persona_compare_report.md
    project_one_pager.md · postmortem.md · ethical_use.md
```

---

## Design Decisions

- **不依赖 Agent 框架**：核心 Agent 调用、工具循环、跨会话 memory 全部手写，便于在面试中拆解每一层逻辑。
- **Prompt + 代码双通路**：关键判断（JD 匹配）必须两边都过，规则版作为 Prompt 版的回归基线。
- **契约式 Prompt**：每份 Prompt 文件明确输入 / 步骤 / 输出 / 禁止条款，可像 API 一样回归测试。
- **状态用文件而非数据库**：Markdown / JSON 直接 diff，故障与变更全部可读。
- **声明式 RAG 工作流**：用 LangGraph 把"检索 → 提示拼装 → LLM → 工具调用"显式化为 4 节点，避免黑盒链路。
- **抓取双通道 + 自动回退**：常规站点走 `requests`，SPA 自动回退 Playwright，控制成本同时覆盖主流招聘页。

---

## Limitations

- **不自动投递**：不会代为提交简历到任何平台。投递动作必须人工完成。
- **JD 抓取仅半自动 · 不批量 · 不登录**：`job_discovery.py` 一次只处理用户给定的单个 URL；Playwright 只做 SPA 渲染兜底，不做门户扫描 / 翻页 / 列表遍历；不登录任何招聘平台、不绕验证码。详见 [`docs/ethical_use.md`](docs/ethical_use.md) §1.6。
- **不伪造经历**：简历草稿仅基于 `user_profile.md` 与 `interview_story_bank.md` 中的真实素材重组、强调和适配 JD，不会编造未发生的项目。
- **不承诺录用概率**：所有匹配结论是"差距分析 + 建议"，不输出录用率、面试通过率之类的数字预测。
- **写入需人工确认**：写入 `applications.md` / `user_profile.md` 等用户层文件的关键动作必须 UI 二次确认，Agent 不静默落库（详见 [`DATA_CONTRACT.md`](DATA_CONTRACT.md) §4.0 写入策略表）。
- **个人作品集，非生产系统**：单用户运行、本地存储、无多租户、无登录鉴权 / 限流 / 审计。
- **指标规模小**：50 题评估集只覆盖本仓库内的 Prompt / 画像 / JD 等内容，结论不推广到通用领域。
- **LLM 输出不可强保证**：尽管走 Prompt 契约，仍可能产生不符合规则的回答，需人工二次确认。

---

## Roadmap

- [x] V1：画像 / 匹配 / 规划 / 执行 / 复盘五段 + Agent Demo
- [x] V1.5：RAG（LangGraph + ChromaDB）+ FastAPI 接口层
- [x] V2：6 卡片控制台 + Orchestrator + JD 自动抓取 + JD 定制简历 + 多 Persona 回归 + 工程自检
- [ ] 简历最终可投递版本（Word / PDF）
- [ ] 1 分钟 Demo 视频（可选）
- [ ] RAG 评估集扩到 100 题（可选）

详细推进记录见 [`PROJECT_STATUS.md`](PROJECT_STATUS.md)。

---

## License

个人作品集项目，未配置开源许可。引用或参考请在 issue 中联系。
