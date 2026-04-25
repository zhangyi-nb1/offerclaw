# OfferClaw

> 一个**长期运行、带状态、围绕单个求职者成长的执行型 AI Agent**。
> 核心闭环：**画像 → 匹配 → 规划 → 执行 → 复盘 → 回到画像更新**。

📚 快速链接：[一页纸](docs/project_one_pager.md) · [验证报告](docs/verification_report.md) · [架构图](docs/architecture.md) · [演示流程](docs/demo.md) · [简历介绍](docs/resume_pitch.md) · [面试问答卡](docs/interview_qa.md) · [故事库](interview_story_bank.md) · [技术复盘](docs/postmortem.md) · [伦理边界](docs/ethical_use.md) · [数据契约](DATA_CONTRACT.md) · [投递追踪](applications.md)

🖥️ **本地求职作战控制台**：启动 FastAPI 后访问 [http://127.0.0.1:8000/ui](http://127.0.0.1:8000/ui) — 6 卡片布局（① 画像 / ② JD 匹配 / ③ 缺口 / ④ 计划 / ⑤ 每日执行 / ⑥ 简历草稿）+ 顶部 RAG 问答条。

🔢 当前指标：**RAG Recall@5 = 0.96 · MRR = 0.74 · pytest 37/37 (+3 e2e skip) · 11 FastAPI 接口（含 SSE 流式 + 友好 UI）· 118 chunks 知识库 · doctor 8 OK · verify_pipeline 6/6**

> ℹ️ 评估集为**自建小规模 RAG 评估集**：50 题 · 3 桶（fact / explain / cross_doc）· 已开源在 [`tests/rag_eval_set.json`](tests/rag_eval_set.json)，基线快照见 [`tests/rag_eval_baseline.json`](tests/rag_eval_baseline.json)。此规模仅用于单人项目自检与回归对比，不代表通用基准。

🛠️ 一键体检：`python doctor.py` · 一键链路：`python verify_pipeline.py` · 一键启动：`python -m uvicorn rag_api:app` 然后浏览器打开 http://127.0.0.1:8000

OfferClaw 不是岗位推荐机器人，也不是简历生成工具。它把求职过程当成一个 *持续运行的工程项目*：用 Prompt 契约定义每一步的输入输出，用规则代码兜底关键判断，用 JVS Claw 的定时任务承载长期执行，用 daily_log 沉淀真实数据并反向修正画像与计划。

当前样本用户：Zhang Yi（东南大学通信工程硕士，2027-07 毕业）。系统设计上面向通用求职者。

---

## 架构总览

### V1 · Agent 核心闭环

```
┌─────────────────────────────────────────────────────────────┐
│  身份与规则层（不变契约）                                     │
│  SOUL.md · target_rules.md · source_policy.md               │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐    ┌──────────────┐
│ ① 画像层      │   │ ② 匹配层      │    │ ③ 规划层      │
│ user_profile │   │ job_match_   │    │ plan_prompt  │
│ onboarding   │   │ prompt + .py │    │ + plan_gen   │
└──────────────┘   └──────────────┘    └──────────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            ▼
                ┌──────────────────────┐
                │ ④ 执行 / ⑤ 复盘层     │
                │ daily_log.md         │
                │ summary_prompt.md    │
                │ （由 JVS Claw 定时任务驱动）│
                └──────────────────────┘
                            │
                            ▼
                ┌──────────────────────┐
                │ 代码实现层            │
                │ agent_demo.py        │
                │ tools.py             │
                │ match_job.py         │
                └──────────────────────┘
```

### V1.5 · RAG + API 层（新增）

```
用户提问
  ↓
┌─────────────────────┐
│  FastAPI 接口层      │  ← rag_api.py（6 端点 + SSE 流式 + Swagger UI）
│  rag_api:app        │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  LangGraph 工作流    │  ← rag_graph.py（4 节点状态机 + 条件边工具循环）
│  StateGraph          │
│  retrieve → prompt   │
│  → call_llm → ...   │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  ChromaDB 向量库     │  ← chroma_db/（50 chunks · offerclaw_docs 集合）
│  offerclaw_docs     │
└─────────────────────┘
```

---

## 核心模块

| 模块 | 状态 | 关键文件 |
|---|---|---|
| ① 渐进式用户画像 | ✅ | `user_profile.md` · `onboarding_prompt.md` |
| ② 岗位匹配（双通路：Prompt + 规则） | ✅ | `job_match_prompt.md` · `match_job.py` · `jd_candidates.md` |
| ③ 学习与求职路线规划 | ✅ | `plan_prompt.md` · `plan_gen.py` |
| ④ 执行推进与提醒（JVS Claw 定时） | 🟡 90% | `daily_log.md` |
| ⑤ 学习留痕复盘 | ✅ | `summary_prompt.md` · `source_policy.md` |
| Agent Demo（V1 代码层） | ✅ | `agent_demo.py` · `tools.py` · [`AGENT_DEMO.md`](AGENT_DEMO.md) |
| **RAG 检索增强系统** | ✅ | `rag_agent.py` · `rag_graph.py` · `rag_ingest.py` · `rag_tools.py` · `rag_query.py` |
| **FastAPI 接口层** | ✅ | `rag_api.py`（11 路由：5 核心业务 + 6 辅助/系统，含 SSE 流式 + 友好 UI + Swagger） |
| JVS Claw 部署 | 🟡 90% | `deployment.md` |

## 📊 当前指标

| 指标 | 值 |
|---|---|
| RAG 评估（自建 50 题 3 桶集） | Recall@5 = **0.96** · MRR = **0.74** |
| pytest | **37/37**（+3 e2e 默认跳过，需 `OFFERCLAW_E2E=1`） |
| FastAPI 路由 | **11**（5 核心业务 + 6 辅助/系统，详见下方） |
| ChromaDB 知识库 | 118 chunks（12 文档） |
| 工程自检 | doctor 8 OK · verify_pipeline 6/6 |
| SSE 首字延迟 | < 2s |

📑 全部指标的现场输出已固化在 [`docs/verification_report.md`](docs/verification_report.md)。

### 11 路由分类
- **核心业务 5**：`POST /api/match` · `POST /api/query` · `POST /api/stream` · `POST /api/search` · `POST /api/reset`
- **辅助/系统 6**：`GET /` · `GET /ui` · `GET /api/info` · `GET /api/profile` · `GET /health` · `GET /docs`

---

## 技术栈

- **语言**：Python 3.10+
- **LLM**：智谱 GLM-4-Flash（OpenAI 兼容 function calling）
- **向量库**：ChromaDB（本地持久化）
- **Embedding**：智谱 `embedding-3`（2048 维，rag_tools.py 实际调用值；与 README 口径一致）
- **工作流编排**：LangGraph（声明式 StateGraph）
- **API 框架**：FastAPI + Uvicorn
- **Agent 核心**：仅 `requests`，无 LangChain / LlamaIndex
- **认证**：手写 JWT（HS256），纯标准库
- **运行平台**：JVS Claw（文件空间 + 定时任务 + 对话交互）
- **本地命令行**：
  - `python agent_demo.py` — Agent Demo
  - `python rag_graph.py "问题"` — RAG 查询
  - `uvicorn rag_api:app --host 0.0.0.0 --port 8000 --reload` — FastAPI 服务

---

## 仓库结构

### Prompt 契约层（`.md`）
- `SOUL.md` — Agent 身份与硬边界
- `target_rules.md` — 求职方向、6 项硬门槛、6 项软性维度、三档结论规则
- `source_policy.md` — 信息源 A/B/C 证据等级
- `onboarding_prompt.md` — 首次启动 6 步流程（双模式写回）
- `job_match_prompt.md` — JD 匹配 9 步契约 + 缺口元数据
- `plan_prompt.md` — 4 周路线规划契约（缺口清单 → 周/日两层计划）
- `summary_prompt.md` — 每日 / 每周复盘契约 + 偏离度判断

### 用户运行时数据
- `user_profile.md` — 12 节画像（实样本 ≈ 85% 完成度）
- `daily_log.md` — 每日计划 / 执行 / 复盘 / 学习留痕
- `jd_candidates.md` — JD 候选池（7 份，用作回归测试）

### 代码实现
- `agent_demo.py` — Agent 主入口（LLM 调用 / 工具循环 / 跨会话 memory）
- `tools.py` — 4 个工具（time / calculator / echo / simple_profile_lookup）
- `match_job.py` — 规则版 JD 匹配引擎
- `plan_gen.py` — 路线规划生成器
- `day1_api_starter.py` — LLM API 调用起点

### RAG + API 层（V1.5 新增）
- `rag_agent.py` — RAG Agent 主入口（手动编排：检索 → Prompt 注入 → LLM）
- `rag_graph.py` — **LangGraph 声明式工作流**（4 节点 StateGraph + 条件边工具循环）
- `rag_api.py` — **FastAPI HTTP 接口层**（6 端点 + SSE 流式 + Swagger UI 自动文档）
- `rag_ingest.py` — 文档向量化入库（Markdown 分块 → Embedding → ChromaDB）
- `rag_tools.py` — RAG 工具函数（分块 / Embedding / 检索 / LLM 调用）
- `rag_query.py` — 独立检索查询脚本
- `chroma_db/` — ChromaDB 持久化目录（118 chunks / 12 文档，`.gitignore` 排除）
- `requirements.txt` — 完整依赖清单（ChromaDB / LangGraph / FastAPI / Pydantic）

### 部署 & 项目状态
- [`deployment.md`](deployment.md) — JVS Claw 部署文档
- [`PROJECT_STATUS.md`](PROJECT_STATUS.md) — 项目进度单一事实来源
- [`AGENT_DEMO.md`](AGENT_DEMO.md) — Agent Demo 详细说明（架构图 / 4 级阶梯测试 / 安全设计）

---

## 快速开始

### 本地跑 Agent Demo

```bash
git clone https://github.com/zhangyi-nb1/offerclaw.git
cd offerclaw
pip install -r requirements.txt

# 创建 .env.local（已被 .gitignore 忽略）
echo "ZHIPU_API_KEY=你的智谱密钥" > .env.local

python agent_demo.py
```

详细使用与 4 级阶梯测试见 [`AGENT_DEMO.md`](AGENT_DEMO.md)。

### 跑 RAG 查询

```bash
# LangGraph 工作流模式（推荐）
python rag_graph.py "我的求职方向是什么"

# 手动编排模式（对比学习用）
python rag_agent.py "我的求职方向是什么"
```

### 启动 FastAPI 服务

```bash
uvicorn rag_api:app --host 0.0.0.0 --port 8000 --reload

# 浏览器访问 http://localhost:8000/docs 打开 Swagger UI
# 或用 curl 测试：
curl http://localhost:8000/health
curl -X POST http://localhost:8000/api/query -d '{"query": "我的求职方向"}'
```

### 在 JVS Claw 上跑

把仓库内所有 `.md` 上传到 JVS Claw 工作空间，配 system prompt = `SOUL.md`，详见 [`deployment.md`](deployment.md)。

---

## 设计亮点（简历向）

- **不依赖 Agent 框架**：Agent 核心仅用 `requests`，无 LangChain / LlamaIndex，从零实现 LLM 调用 + 工具路由 + 多轮对话 + 工具调用循环
- **Prompt + 代码双通路**：核心模块（如 JD 匹配）同时有 Prompt 契约版和规则代码版，互相验证、互为兜底
- **契约式 Prompt 工程**：每个 Prompt 文件都明确定义输入 / 步骤 / 输出 / 禁止条款，可像 API 一样回归测试
- **长期运行**：跨会话 memory（`memory.json`）+ JVS Claw 定时任务承载日维度执行
- **可解释**：所有 JD 匹配判断带 `[致命度]` `[短期性]` 元数据；复盘带"偏离度判断"
- **声明式工作流编排**：RAG 链路用 LangGraph StateGraph 重构为 4 节点状态机，支持条件边自动路由 + 工具循环
- **HTTP API + SSE 流式**：6 个 FastAPI 端点覆盖 RAG 查询 / 检索 / 画像 / 匹配 / 重置，含 Server-Sent Events 流式响应

---

## 项目状态

详见 [`PROJECT_STATUS.md`](PROJECT_STATUS.md)。

- 项目目标截止日：**2026-05-01**
- 当前阶段：阶段 C（RAG + FastAPI + LangGraph 交付 → 简历公开化 → 投递准备）

---

## License

本仓库为个人作品集项目，未配置开源许可。如需引用或参考，请在 issue 中联系。
