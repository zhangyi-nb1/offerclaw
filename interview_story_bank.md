# OfferClaw · 面试故事库（Interview Story Bank）

> 用途：把 OfferClaw 的关键技术决策沉淀为面试可复用的 STAR+R 故事。  
> 用法：每条都能独立讲 2-3 分钟；面试前按 JD 选 3-4 条配合 `docs/interview_qa.md`。

---

## Story 1 · 为什么做 OfferClaw

### Situation
我是 985 通信硕士在读，目标是 AI 应用 / Agent 实习方向，但本科到硕士前期没有计算机相关实习，简历主项目偏算法仿真，缺一个能在 AI Agent 工程能力上"撑得住"的主项目。

### Task
在 6 周内做出一个可以放进简历、能在面试时讲清楚技术决策、能体现长期 Agent 工程能力的主项目。不是 demo，是工程系统。

### Action
- 把项目定位为"求职作战 Agent"——围绕用户画像、岗位匹配、缺口识别、计划与复盘形成闭环
- 拆三个 Sprint：A 核心闭环 + 测试，B FastAPI + SSE + 多 persona 回归，C 文档与展示资产
- 每个 Sprint 都有验收标志（pytest 通过、Recall@5 阈值、SSE 真实可调）

### Result
- 35 个文件、**37 个测试**、**11 个 FastAPI 路由**（5 核心业务 + 6 辅助）、Recall@5 = **0.96** / MRR = **0.74**（自建 50 题 3 桶集）
- 4 张 Mermaid 架构图、一页纸、面试 10 题、伦理边界文档
- GitHub 仓库公开 + 多次提交追溯

### Reflection
最大的收获是**不再用功能数衡量项目**，而是用"是否形成闭环"。第一周我也想过堆技术栈（多模态、Function Calling、Agent Marketplace），后来砍掉，专注 RAG + LangGraph + FastAPI 三件事，反而 ship 出来了。

---

## Story 2 · 从 Prompt 契约到规则代码版岗位匹配

### Situation
最初版 OfferClaw 把岗位匹配完全交给 LLM：把 JD + 用户画像塞给 GLM-4，让它输出"适合 / 暂不 / 中长期可转向"。Demo 跑通但有两个问题：(1) 同一份 JD 不同 prompt 会得到不同结论；(2) 没法在 CI 里跑回归测试。

### Task
让岗位匹配**可测试、可解释、且失败可定位**，同时不丢掉 LLM 在长 JD 上的语义理解能力。

### Action
- 把"硬否决条件"（地点冲突、Java 主线、不接受日常实习）抽到 `target_rules.md` + `match_job.py` 规则代码
- LLM 只在规则放行后做软评估
- 写 `tests/test_offerclaw_core.py`（9 题）+ `tests/test_personas.py`（3 personas × 4 JDs = 12 组合 parametrize）
- 在 `eval_rag.py` 之外，单独跑 match 回归

### Result
17/17 测试通过；同一份 JD 跑 10 次结论稳定；新增一个硬规则只需要加一行 + 一条测试。

### Reflection
工程化的第一性原理是 **deterministic first, fuzzy second**。能用规则解的问题不要交给 LLM，否则你既无法回归也无法 debug。LLM 是兜底语义层，不是决策主体。

---

## Story 3 · 从 LLM API 到 Agent 工具调用

### Situation
规则版能给三档结论，但用户问"那我接下来 4 周该学什么"时，纯 LLM 的回答会乱编"先看 transformer 论文 → 再做项目"——既不结合用户画像，也不知道本周日历。

### Task
让 OfferClaw 能"读自己的状态、写自己的输出"，而不是无状态对话。

### Action
- 用 `tools.py` 注册了 6 个工具：`get_user_profile` / `read_target_rules` / `write_daily_log` / `gen_plan` / `match_job` / `summary`
- 用最小化 ReAct：LLM 决定调哪个工具，工具结果回写 prompt
- `memory.json` 做长期记忆 KV，跨会话保留"上次给用户推过哪 3 个 JD"

### Result
"4 周计划"质量从"通用学习路径"提升到"按用户画像缺口排序的具体任务清单"，用户可以直接照着做。

### Reflection
Agent 不是"更聪明的 ChatGPT"，是**有状态的执行体**。Tool 的最小集设计比花哨的 Reasoning 框架重要——我后来引入 LangGraph 时，Tool 直接复用没动。

---

## Story 4 · 从普通问答到 RAG 检索增强

### Situation
项目状态文件越来越多（user_profile / SOUL / target_rules / source_policy / 7 个 prompt），LLM 的 context window 装不下；用户问"OfferClaw 的硬否决规则是什么"时，要么截断要么答错。

### Task
让 LLM 可以**精确**引用项目自己的规则文档，而不是靠 prompt 里塞全文。

### Action
- 用 `rag_ingest.py` 把 12 份 markdown 切成 118 个 chunks（按 markdown header 切，不破坏语义单元）
- ChromaDB + 智谱 `embedding-3` 做向量检索
- 写 `eval_rag.py`：自建 **50 题 3 桶集**（fact / explain / cross_doc）+ baseline 回归对比，跑 Recall@5 / MRR + 桶级指标
- 调 chunk 大小（200/400/600 三档），最终选 400 token，**Recall@5 = 0.96**

### Result
"硬否决规则是什么" / "三档结论怎么定义" 这类元问题准确率从 ~30% 提到 96%；LLM 输出可追溯到具体 chunk。**Recall@5 由 0.75 提到 0.96，剩余 2 个 miss（f03/e05）已定位到根因（chunk 边界把关键句切散）。**

### Reflection
**RAG 没有银弹**——我一开始想用 token-based 切分，结果中文 markdown 章节被切散；改成 header-based 后立刻好了。RAG 的瓶颈 90% 在 ingest，不在 retrieval。我也明白了为什么蔚来的 JD 写"研究与实践 RAG 相关评估方法"——没有 eval 就没有 RAG。

---

## Story 5 · 从流程脚本到 LangGraph 工作流

### Situation
`pipeline.py` 一开始是顺序 Python 函数：match → plan → log。用户问"如果 match 是'暂不'还要不要跑 plan"时，要在主函数里写 if/else，而且没法在中间 checkpoint 重试。

### Task
让多步流程**可分支、可重试、状态可观测**，并保留升级空间（比如以后接 human-in-the-loop）。

### Action
- 用 LangGraph 把流程改写成 StateGraph：节点 = match / plan / summary / rag_query；边带条件
- `_msg_to_dict()` 适配 BaseMessage 序列化（这是个坑，原生不支持）
- 顺手把 `rag_graph.py` 的伪向量分支删掉，统一走真实 embedding

### Result
新增一个分支只改 graph 不改主函数；任何节点失败可以从该节点重试；前端 SSE 接的就是 graph 流式输出。

### Reflection
LangGraph 的价值不在节点数，而在**状态字段是显式声明的**。从此项目里所有"我以为 ChatGPT 记得"的隐式状态，都被迫写进 State——一开始麻烦，后来发现 debug 反而更容易。

---

## Story 6 · 从本地脚本到 FastAPI 服务化 + 友好前端

### Situation
所有功能能跑，但只有命令行；没法演示给非技术评委 / 面试官，简历贴 GitHub 链接对方看到的是一堆 .py。

### Task
做一个**零依赖、能演示**的 web 入口，覆盖健康检查、画像、岗位匹配、流式问答。

### Action
- FastAPI 11 个接口；中间件加 `request_id` + JSON 日志（`logging_utils.py`）
- `/api/stream` 用 SSE 真流式（不是先 buffer 再切）；前端用 fetch + ReadableStream 解析（POST + SSE 不能用 EventSource）
- 单文件 `static/index.html`，3 张卡片，深色主题，零依赖（不引 CDN）
- `/` → 重定向 `/ui`，开发者仍可走 `/docs` Swagger

### Result
`uvicorn rag_api:app` 起来后浏览器打开 `http://127.0.0.1:8000` 就能用；面试演示 ≤2 分钟跑完所有功能。

### Reflection
做前端那一刻才意识到，**用户体验决定项目可信度**。再厉害的 RAG 召回，如果第一眼是 Swagger JSON，对非技术面试官就是 0 分。后续如果真上生产，会加 CORS / Rate Limit / 鉴权——这些是 V2 的事。

---

## 用法索引（面试问题 → 推荐故事）

| 面试常见问题 | 主讲 | 配菜 |
|---|---|---|
| 为什么做这个项目？ | Story 1 | Story 6 |
| 项目最难的部分？ | Story 4 | Story 5 |
| 为什么选 LangGraph 而不是 LangChain Chain？ | Story 5 | Story 3 |
| 怎么评估 RAG？ | Story 4 | — |
| 怎么处理 LLM 不稳定？ | Story 2 | Story 3 |
| 工程化做了什么？ | Story 6 | Story 2 |
| 如果重做会怎么改？ | 任意 Reflection | — |
