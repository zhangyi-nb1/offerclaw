# OfferClaw · 简历项目栏 V1（含 V2 全功能版）

> 用于贴在简历"项目经历"段。提供 80 字短版 / 短版 / 中版三档，配套 30 分钟面试口述脚本。

---

## 简历 80 字版（适合两段以上多项目并列）

**OfferClaw · 个人求职作战 AI Agent**（个人项目 / GitHub）  
基于 LangGraph + RAG + FastAPI 自研本地"画像→匹配→规划→复盘→简历定制"求职闭环；自建 50 题 RAG 评估集 Recall@5=0.96，pytest 37/37，160 chunks 知识库，6 卡片本地控制台 + SSE 流式输出。

---

## 简历短版（3 行版，适合 1 页简历）

**OfferClaw · 个人求职作战 AI Agent** — 个人项目 · GitHub · 2026.04
- 基于 **LangGraph 状态机** 重构端到端 RAG 工作流（retrieve→prompt→llm→tools），统一 CLI / FastAPI / 流式 SSE 三种入口；6 卡片本地求职控制台（/ui）+ Swagger（/docs）
- 自建 ChromaDB 知识库（15 文档 → **160 chunks**）+ 智谱 `embedding-3`（2048 维）；自建 **50 题 3 桶评估集**（fact / explain / cross_doc），**Recall@5 = 0.96, cross_doc = 1.00, MRR = 0.67**
- pytest **37/37**（含 3 persona × multi-JD 参数化 + FastAPI TestClient 接口测）；**19 FastAPI 接口**（含 2 条 SSE 流式 + Playwright 无头浏览器抓 JD）；含 `doctor.py` 自检与 `verify_pipeline.py` 6/6 冒烟
- **技术栈**：Python 3.13 / LangGraph / FastAPI / ChromaDB / 智谱 GLM-4 + `embedding-3` / Playwright / pytest / SSE / Vanilla-JS UI

---

## 简历中版（5-7 行版，适合详细简历 / 一页全用 OfferClaw）

**OfferClaw · 求职作战 AI Agent**（全栈个人项目，GitHub: zhangyi-nb1/offerclaw）

> 自研一款"画像 → JD 抽取 → 岗位匹配 → 4 周路线 → 每日执行 → 简历定制"全闭环的求职助手 Agent，
> 对标蔚来 / 字节"大模型应用开发实习"JD 的核心能力一一对应实现。

- **LLM 工作流编排**：用 LangGraph 把"检索→Prompt 注入→LLM→工具调用"显式建模为状态机（4 节点 + 1 条件边），替代手工 if/else 链
- **RAG 知识库**：智谱 `embedding-3`（2048d）+ ChromaDB PersistentClient，**15 文档 → 160 chunks**；自写 Markdown 智能分块（按 ## 二级标题切，含重叠）；source_type 标签覆盖 8 类知识源（profile / jd / log / story / resume / application / system / doc）
- **JD 半自动抽取**：requests 快速抓 + Playwright 无头 Chromium 自动回退渲染 SPA（字节/阿里/腾讯均可），规则 + 40+ 关键字命中提取结构化 JD
- **简历定制生成**：基于事实清单（防 LLM 幻觉）+ 用户画像 + JD 关键字段，调智谱 GLM-4 生成 bullet+段落+命中分析三段式简历，支持 SSE 流式输出
- **顶层 Orchestrator**：`career_agent.py` 状态机驱动"今日建议"，聚合 applications.md + daily_log.md，输出最高优先级动作（准备投递/面试中/Offer 中/已拒绝转向）
- **接口层**：**FastAPI 19 路由**（含 2 条 SSE 流式 `/api/plan/stream` + `/api/resume/build/stream`），中间件统一 request_id + JSON 结构化日志，Swagger 自带文档
- **业务规则层**：`match_job.py` 实现三档匹配（适合/暂不/中长期），硬门槛 6 项 + 软维度 6 项；**禁止 LLM 脑补硬门槛**，确保结论可解释
- **质量保证**：pytest 37 用例（含 3 persona × 多 JD 参数化 + FastAPI TestClient 接口测 + 主链路冒烟）；`eval_rag.py` 输出 Recall@K / MRR / 桶级分项 + baseline 回归；`docs/persona_compare_report.md` 证明同一 JD 在 3 类 persona 下输出明显不同结论
- **数据治理**：`DATA_CONTRACT.md` 显式三层数据契约（User / System / Runtime）+ 不变量；`applications.md` 9 状态投递台账；`interview_story_bank.md` 6 条 STAR+R
- **工程可信度**：`doctor.py` 7 类自检 + `verify_pipeline.py` 6 步主链路冒烟，全部固化到 `docs/verification_report.md`
- **私密性**：`.env.local` + `.gitignore` 把 API Key 与个人画像隔离出 Git 流

**关键数据**：Recall@5=**0.96**, cross_doc=**1.00**, MRR=**0.67**, **37/37** pytest, **160 chunks**, **19 FastAPI 路由**, 3 persona JSON 回归, doctor 7/7, verify_pipeline 6/6

**技术栈**：Python 3.13 · LangGraph · FastAPI · Pydantic · ChromaDB · 智谱 GLM-4 + `embedding-3` · Playwright · JWT · pytest · SSE · Vanilla-JS UI · Mermaid · Git

---

## 与蔚来 / 字节大模型实习 JD 的逐项对照（面试用）

| JD 核心要求 | OfferClaw 对应实现 | 证据文件 |
|------|------|------|
| 基于 RAG 的知识增强问答系统 | rag_agent.py / rag_graph.py + ChromaDB | `rag_*.py` |
| 端到端 LLM 工作流（文档解析、向量检索、调用链路编排、API 服务集成） | LangGraph 4 节点 + FastAPI 19 接口 | `rag_graph.py` `rag_api.py` |
| RAG 评估方法 | Recall@K + MRR + 分桶 + baseline 回归 + **自建 50 题 3 桶评估集** | `eval_rag.py` / `tests/rag_eval_set.json` |
| 系统原型设计、接口开发和上线部署 | FastAPI + SSE + Swagger + JVS Claw 部署 | `rag_api.py` `deployment.md` |
| 跟踪开源生态灵活选型 | LangGraph / ChromaDB / FastAPI / Playwright 全部为最新版选型 | `requirements.txt` |
| 熟练 Python | 全栈 ~3500 行 | 全部源码 |
| LangGraph / LlamaIndex / FastAPI 经验者优先 | LangGraph + FastAPI 都已落地 | 同上 |
| 文本解析、知识库构建、嵌入向量搜索 | 自写 Markdown 分块 + 嵌入入库 + 检索 + 评估 + Playwright SPA 抓取 | `rag_tools.py` `rag_ingest.py` `job_discovery.py` |
| 模型评估能力 | Recall@K / MRR + miss 案例分析 + 桶级分项 + baseline | `eval_rag.py` |
| Agent 主动性 / 多步规划 | `career_agent.py` 状态机 + `/api/today` 顶层 Orchestrator | `career_agent.py` |

---

## 一句话挑战自我（面试 elevator pitch）

> "我用 LangGraph 把 RAG 工作流显式建模成状态机，把规则匹配和 LLM 生成清晰隔离；
> 自建 50 题 3 桶评估集做回归，当前 Recall@5 = 0.96 / cross_doc = 1.00；
> 用 Playwright 自动渲染字节/阿里这类 SPA 招聘页，再喂给 LLM 做 JD 定制简历，从粘 URL 到出简历段全程自动；
> **整套系统是我每天求职用的真实生产工具，不是 demo**。"

