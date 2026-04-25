# OfferClaw · 简历项目栏 V1

> 用于贴在简历"项目经历"段。3 行核心 + 技术栈 + 数据 3 件套。

---

## 简历短版（3 行版，适合 1 页简历）

**OfferClaw · 个人求职作战 AI Agent** — 个人项目 · GitHub · 2026.04
- 基于 **LangGraph 状态机** 重构端到端 RAG 工作流（retrieve→prompt→llm→tools），统一 CLI / FastAPI / 流式 SSE 三种入口；自带友好 Web UI（/ui）+ Swagger（/docs）
- 自建 ChromaDB 知识库（12 文档 → 118 chunks）+ 智谱 `embedding-3`（2048 维）；自建 **50 题 3 桶评估集**（fact / explain / cross_doc），**Recall@5 = 0.96, MRR = 0.74**，与 baseline 做回归对比
- pytest **37/37**（含 3 persona × multi-JD 参数化 + FastAPI TestClient 接口测 + 6 步主链路冒烟），结构化 JSON 日志 + request_id；含 `doctor.py` 7 类自检与 `verify_pipeline.py` 6 步冒烟
- **技术栈**：Python 3.13 / LangGraph / FastAPI / ChromaDB / 智谱 GLM-4-Flash + `embedding-3` / pytest / SSE / Vanilla-JS UI

---

## 简历中版（5-7 行版，适合详细简历）

**OfferClaw · 求职作战 AI Agent**（全栈个人项目，GitHub: zhangyi-nb1/offerclaw）

> 自研一款"画像→岗位匹配→4 周路线→晚间复盘"全闭环的求职助手 Agent，
> 对标蔚来"大模型应用开发实习"JD 的 5 项核心要求一一对应实现。

- **LLM 工作流编排**：用 LangGraph 把"检索→Prompt 注入→LLM→工具调用"显式建模为状态机（4 节点 + 1 条件边），替代手工 if/else 链
- **RAG 知识库**：智谱 `embedding-3`（2048d）+ ChromaDB PersistentClient，12 文档 → 118 chunks；自写 Markdown 智能分块（按 ## 二级标题切，含重叠）
- **接口层**：FastAPI 11 接口（含 SSE 流式 `/api/stream` + 友好 UI `/ui`），中间件统一 request_id + JSON 结构化日志，Swagger 自带文档
- **业务规则层**：`match_job.py` 实现三档匹配（适合/暂不/中长期），硬门槛 6 项 + 软维度 6 项；**禁止 LLM 脑补硬门槛**，确保结论可解释
- **质量保证**：pytest 37 用例（含多 persona × 多 JD 参数化 + FastAPI TestClient 接口测 + 主链路冒烟）；`eval_rag.py` 输出 Recall@K / MRR / 桶级分项 + baseline 回归
- **数据治理**：`DATA_CONTRACT.md` 显式三层数据契约（User / System / Runtime）+ 7 条不变量；`applications.md` 9 状态投递台账；`interview_story_bank.md` 6 条 STAR+R
- **工程可信度**：`doctor.py` 7 类自检（API Key / 关键文件 / Chroma 状态 / 评估集 schema 等）+ `verify_pipeline.py` 6 步主链路冒烟
- **私密性**：`.env.local` + `.gitignore` 把 API Key 与个人画像隔离出 Git 流

**关键数据**：Recall@5=**0.96**, MRR=**0.74**（自建 50 题 3 桶评估集）, **37/37** pytest 通过, 118 chunks, 11 FastAPI 接口（含 SSE + UI）, 3 persona JSON, doctor 8 OK, verify_pipeline 6/6

**技术栈**：Python 3.13 · LangGraph · FastAPI · Pydantic · ChromaDB · 智谱 GLM-4-Flash + `embedding-3` · JWT · pytest · SSE · Vanilla-JS UI · Mermaid · Git

---

## 与蔚来 JD 的逐项对照（面试用）

| 蔚来 VAS 实习 JD 要求 | OfferClaw 对应实现 | 证据文件 |
|------|------|------|
| 基于 RAG 的知识增强问答系统 | rag_agent.py / rag_graph.py + ChromaDB | `rag_*.py` |
| 端到端 LLM 工作流（文档解析、向量检索、调用链路编排、API 服务集成） | LangGraph 4 节点 + FastAPI 6 接口 | `rag_graph.py` `rag_api.py` |
| RAG 评估方法 | Recall@K + MRR + 分桶 + baseline 回归 + **自建 50 题 3 桶评估集** | `eval_rag.py` / `tests/rag_eval_set.json` |
| 系统原型设计、接口开发和上线部署 | FastAPI + SSE + Swagger + JVS Claw 部署 | `rag_api.py` `deployment.md` |
| 跟踪开源生态灵活选型 | LangGraph / ChromaDB / FastAPI 全部为最新版选型 | `requirements.txt` |
| 熟练 Python | 全栈 ~3000 行 | 全部源码 |
| LangGraph / LlamaIndex / FastAPI 经验者优先 | LangGraph + FastAPI 都已落地 | 同上 |
| 文本解析、知识库构建、嵌入向量搜索 | 自写 Markdown 分块 + 嵌入入库 + 检索 + 评估 | `rag_tools.py` `rag_ingest.py` |
| 模型评估能力 | Recall@K / MRR + miss 案例分析 + V2 rerank 计划 | `eval_rag.py` |

---

## 一句话挑战自我（面试 elevator pitch）

> "我用 LangGraph 把 RAG 工作流显式建模成状态机，把规则匹配和 LLM 生成清晰隔离；
> 自建 50 题 3 桶评估集做回归，当前 Recall@5 = 0.96，下一步要做 LLM rerank 把剩下 2 个 miss 啃掉。
> 整套系统跑在 JVS Claw 上，自己每天用它来选岗、定计划、做复盘——
> **它是我求职过程中最严肃的一份'真实业务系统'**。"
