# OfferClaw · 项目一页纸（Project One-Pager）

> 用途：1-2 分钟内让面试官 / 评委 / 自己理解整个项目。  
> 长版见 `README.md` / `docs/architecture.md` / `docs/demo.md`。

---

## 1. 一句话
**OfferClaw 是一个面向求职者的长期执行型 AI Agent，覆盖画像 → 岗位匹配 → 缺口识别 → 学习计划 → 投递跟踪 → 复盘的闭环。**

## 2. 目标用户
正在准备 AI 应用 / Agent 方向实习与校招的工程类学生，特别是简历薄弱、缺乏明确方向的"非科班但目标明确"型用户。

## 3. 解决的问题
| 痛点 | OfferClaw 的应对 |
|---|---|
| JD 看了 100 份还不知道哪些适合 | 三档结论：适合 / 暂不 / 中长期可转向 |
| 知道方向但不知道下一步学什么 | 4 周计划生成（按画像缺口排序） |
| 学了忘了，没复盘 | daily_log + 周度 summary |
| 想问项目状态，要翻 9 份 markdown | RAG 知识库问答（Recall@5 = 0.75） |
| 投递后没有 tracker | applications.md + 状态机 |

## 4. 系统架构
```
┌──────────┐   ┌─────────────┐   ┌──────────────┐
│ FastAPI  │──▶│ LangGraph   │──▶│ Tools / RAG  │
│ + SSE UI │   │ State Graph │   │ ChromaDB     │
└──────────┘   └─────────────┘   └──────────────┘
      │              │                  │
      └──── memory.json / logs / plans ─┘
```
详见 `docs/architecture.md` 4 张 Mermaid 图。

## 5. 核心模块
- **match_job.py** — 规则 + LLM 双通路岗位匹配（硬否决在规则层，软评估在 LLM 层）
- **rag_graph.py** — LangGraph 工作流：retrieve → rerank → answer，带显式 State
- **rag_api.py** — 11 个 FastAPI 接口 + JSON 日志 + request_id 中间件
- **tools.py** — 6 个 Agent 工具：profile / rules / log / plan / match / summary
- **eval_rag.py** — Recall@K + MRR 黄金集（8 题）
- **static/index.html** — 零依赖前端控制台

## 6. 技术栈
Python 3.13 · FastAPI · LangGraph · ChromaDB · 智谱 GLM-4 / embedding-3 · pytest · uvicorn · Vanilla JS

## 7. 当前指标
| 指标 | 值 |
|---|---|
| 测试用例 | 17/17 通过 |
| RAG 召回 | Recall@5 = 0.75 / MRR = 0.69 |
| FastAPI 接口 | 11 个 |
| Persona 回归组合 | 3 personas × 4 JDs = 12 case |
| 知识库条数 | 50 chunks（9 份 markdown） |
| 端到端首字延迟 | < 2s（SSE 流式） |

## 8. Demo 链路（≤2 分钟）
1. `python -m uvicorn rag_api:app` → 浏览器打开 `http://127.0.0.1:8000`
2. 点 **系统健康** → 看 `chroma_db: connected, 50 records`
3. 点 **看用户画像** → 显示 §0 元信息 + 方向 + 技能
4. 粘 NIO JD → 点 **运行匹配** → 输出三档结论 + 缺口清单
5. 输入 "OfferClaw 主方向是什么？" → 流式问答（fetch + ReadableStream）

## 9. 关键技术难点 / 取舍
- **规则 vs LLM**：硬否决用规则（确定性 + 可测试），软评估给 LLM。— 见 Story 2
- **RAG chunk 切法**：从 token-based 切到 markdown-header-based，Recall@5 +25 个百分点。— 见 Story 4
- **POST + SSE**：浏览器 EventSource 不支持 POST，前端被迫用 fetch + ReadableStream。— 见 Story 6
- **LangGraph BaseMessage 序列化**：原生 `dict()` 失败，加 `_msg_to_dict()` 适配层。
- **状态契约**：用户层 vs 系统层 vs 运行时分层，详见 `DATA_CONTRACT.md`。

## 10. 当前不足与下一步
| 不足 | V2 计划 |
|---|---|
| RAG 评估集只有 8 题 | 扩到 50+ 题 + 引入 hit-rate 分桶 |
| 没有 LLM Reranker | 加 BGE-reranker 或 GLM-4 二阶段 rerank |
| applications.md 是手维护表 | 迁 SQLite + 自动化状态机 |
| 没有 CI / Docker | GitHub Actions + Dockerfile |
| 单用户 | 多 user 隔离（profile.md → users/<uid>/） |
| 没有自动投递 | **保持不做**（见 `docs/ethical_use.md`） |

---

GitHub: https://github.com/zhangyi-nb1/offerclaw
