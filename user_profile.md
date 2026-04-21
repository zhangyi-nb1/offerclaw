# OfferClaw · 用户画像（User Profile）

> 本文件是 OfferClaw 的核心状态文件。允许从不完整简历起步。
> 凡是暂未填写的字段，请保留 `【待补充】` 标记，**不要删除对应条目**。
> 每次与 OfferClaw 交互产生新信息后，优先回写到本文件对应章节。

---

## 0. 元信息
- 画像创建时间：2026-04-15
- 最近更新时间：2026-04-22
- 画像完整度自评（0–100）：85
  - 计算依据：§4 项目 2 追加 LangGraph 工作流编排描述；§3 技能自评更新（Agent/Workflow 含 LangGraph 实战）
- 更新人：OfferClaw（§4 项目 2 LangGraph 更新 + §3 技能更新）

---

## 1. 基础信息（建议优先补全）
- 姓名 / 昵称：Zhang Yi
- 学历层次：硕士（在读）
- 专业：通信工程
- 学校：985 高校（东南大学）
- 毕业时间：2027年7月
- 所在地：南京
- 可接受工作地域：上海/南京/苏州/无锡/南通/远程

---

## 2. 求职方向与偏好（建议优先补全）
- 目标方向（按优先级排序）：
  1. Agent 应用工程
  2. AI 应用开发
  3. Prompt / Workflow 工程
- 目标岗位类型：优先日常实习    
- 期望薪资区间：实习无薪资要求，正式工作月薪底薪3万，上不封顶
- 工作性质偏好：不限
- 行业偏好：互联网性质、AI大模型相关
- 明确不做的方向：
  - Java：以 Java 为主线的业务后端岗位（JD 把 Java 列为"精通 / 熟练 / 为主"即视为不匹配；仅作加分项可接受）
  - Meta 规则：与大模型主线出入大的方向一律过滤（具体方向名由后续岗位调研逐步积累，不参与字面关键词匹配）

---

## 3. 技能清单
> 允许只写当前确定的。不确定的列到"想学但还没学"。

- 编程语言：
  - 熟练：MATLAB（科研与算法实验使用较多）
  - 会用：Python（有一定基础，但不熟练，自述仍需系统提升）
  - 想学：【待补充】
- 工具与框架：
  - JVS Claw（OfferClaw 项目的主要运行平台）
  - Claude（代码与配置协作助手，负责生成 Python 脚本、Prompt、文档）
  - 其他：GPT
- AI / LLM 相关技能：
  - Prompt 工程：了解有一定实战 
  - Agent / Workflow：2/5（rag_agent.py 实战 + rag_graph.py LangGraph 状态机编排）
  - 模型 API 调用：2/5（JWT 签名 + Embedding 批量调用 + LLM 对话）
  - RAG / 向量检索：2/5（2026-04-22 完成 ChromaDB ingest + 检索全链路）（2026-04-22 开始实战：ChromaDB + Embedding API + 检索链路）
- 科研 / 算法工具：MATLAB（常用，用于科研和算法实验）
- 其他：能熟练使用各类AI问题完成日常工作学习需求，并可以训练大模型完成较为复杂的科研任务
- 自学能力强

---

## 4. 项目经历
> 可以为空。若暂时没有，保留一条占位条目即可，不要删掉整节。

- 项目 1
  - 名称：OfferClaw Agent Demo（最小可运行 AI Agent）
  - 时间：2026-04
  - 角色：独立开发
  - 技术栈：Python 3.10 / requests / 智谱 GLM-4-Flash API / OpenAI 兼容 function calling / JWT 签名（HS256）/ Python ast 解析
  - 做了什么：
    - 从零实现一个命令行交互的 AI Agent，走通"用户提问 → LLM 判断是否调工具 → 工具执行 → LLM 整合结果 → 回复"的完整链路
    - 单会话内保留多轮对话历史，基于 OpenAI 兼容 tools 参数让 LLM 自主选择工具
    - 实现工具调用循环：单轮对话内最多 5 次 tool call 迭代，防止 LLM 无限循环
    - 注册 3 个工具：当前时间查询、数学表达式求值器（用 Python ast 白名单解析替代 eval，阻止 `__import__` 等代码注入）、文本回显
    - 手写智谱 JWT Bearer token 签名，纯标准库实现，无 PyJWT 第三方依赖
    - 把工具实现独立拆分到 `tools.py`，主入口 `agent_demo.py` 通过 import 使用，两个文件职责清晰
  - 产出 / 成果：
    - `agent_demo.py`（约 300 行）+ `tools.py`（约 150 行）+ `README.md`（架构图 / 运行说明 / 4 级阶梯测试 / 安全设计 / 简历描述）
    - 4 级阶梯测试（无工具闲聊 / 单工具调用 / 带参数工具 / 多工具链式调用）全部通过；阶梯 4 验证 Agent 能在单轮对话内串联 `get_current_time + calculator` 完成"现在到某日期还剩几天"这类任务
    - 纯标准库 + `requests` 实现，无 LangChain / LlamaIndex / LangGraph 等第三方 Agent 框架依赖
    - 作为 OfferClaw 项目（LLM 求职作战 Agent）代码实现层的基础，为后续画像查询 / JD 匹配工具接入预留接口
- 项目 2
  - 名称：OfferClaw RAG 检索增强系统
  - 时间：2026-04
  - 角色：独立开发
  - 技术栈：Python 3.10 / ChromaDB / 智谱 Embedding API (embedding-3) / LangChain TextSplitter / 智谱 GLM-4-Flash API / FastAPI / LangGraph
  - 做了什么：
    - 将 OfferClaw 核心 .md 文件（user_profile / daily_log / SOUL / target_rules / source_policy）作为 RAG 文档源，共 5 文件 50 个分块
    - 实现文档 ingest 管线（rag_ingest.py）：读取 Markdown → 按标题智能分块 → Embedding 向量化 → 批量存入 ChromaDB
    - 实现 RAG 检索链路（rag_query.py）：用户自然语言提问 → 向量化 → top_k 语义检索 → 基于检索片段由 LLM 整合回答
    - 实现完整 RAG Agent（rag_agent.py）：自动检索注入 + 多轮对话历史 + 工具调用循环（search_docs / get_current_time）
    - 搭建 FastAPI 接口层（rag_api.py）：6 个 API 端点（health / profile / query / search / match / reset），Swagger UI 自动文档
    - 用 LangGraph 重构工作流（rag_graph.py）：声明式状态机编排 retrieve → build_prompt → call_llm → tools 循环，替代手动 Python 编排
    - 手写智谱 JWT Bearer Token 签名（纯标准库，无 PyJWT 依赖），用于 Embedding 和 LLM 调用鉴权
  - 产出 / 成果：
    - `rag_ingest.py`（文档入库）+ `rag_query.py`（检索问答）+ `rag_agent.py`（完整 Agent）+ `rag_api.py`（HTTP API）+ `rag_tools.py`（工具函数）+ `rag_graph.py`（LangGraph 状态机）
    - LangGraph 工作流：4 节点（retrieve → build_prompt → call_llm → execute_tools）+ 条件边（有工具调用则循环），替代手动编排
    - 端到端测试通过：用户提问 → LLM 自动调 search_docs → 检索 → 整合回答，全链路跑通
    - FastAPI 服务支持 Swagger UI 交互式测试，6 个端点全部可用
    - 作为 OfferClaw V1.5 核心升级，直接对应蔚来 JD 的"RAG 知识增强问答系统" + "LLM 应用工作流编排" + "接口开发和上线部署"职责

> 备注（OfferClaw 填写）：§4 项目 2 于 2026-04-21 确立方向（RAG 引入 OfferClaw），2026-04-22 启动编码。Week 1 交付：ingest + 检索 + Agent + FastAPI 全链路（超前完成）。Week 2 目标：LangGraph 工作流编排 + RAG 评估（RAGAS）。

---

## 5. 竞赛 / 获奖经历
- 竞赛 1：全国大学生数学竞赛
- 获奖 1：全国一等奖
- 竞赛 2：江苏省数学竞赛
- 获奖 2：省一等奖
- 竞赛 3：TI杯电子竞赛
- 获奖 3：全国三等奖
- 竞赛 4：华为杯数模竞赛
- 获奖 4：二等奖
> 对口大模型的竞赛暂无，因此需要项目支撑

---

## 6. 科研 / 论文 / 专利
- 研究方向：通信系统优化
- 论文：【待补充】
- 专利：【待补充】

---

## 7. 实习 / 工作经历
- 实习 1：【待补充】

---

## 8. 兴趣与长期倾向
- 兴趣爱好：和AI大模型相关
- 擅长的思维方式：偏工程收敛，以看到结果为导向，后续对已验证的结果进行理论分析和探讨
- 不擅长或不感兴趣的方向：外语交流，销售等语言性表达工作

---

## 9. 当前能力自评
> 用 1–5 分，1 = 不会，5 = 熟练可独立交付。
> 区分前后期，当前作为初始默认，后期根据学习计划后的掌握情况每天/每周更新。
| 维度 | 自评 | 备注 |
|---|---|---|
| Python 工程 | 2 | 有一定基础但不熟练，仍需系统提升（用户自述） |
| LLM API 调用 | 1 | |
| Prompt 设计 | 2 | |
| Agent / Workflow | 1 | |
| 数据处理 | 1 | |
| 前端基础 | 1 | |
| 英语读写 | 2 | |

---

## 10. 可投入时间
- 每天可投入（小时）：每天大概8-10小时
- 每周可投入（小时）：每周周一和周日时间较少，周日在4-8小时，周一1-2小时，自行估计
- 黄金时段：下午 13：00-18：00 晚上 21:00–24:00
- 不可打扰时段：睡眠时间 1：00-10：00（用户可自行调整）

---

## 11. 已知缺口与风险（由 OfferClaw 维护，用户不用手动改）

> 以下内容基于 2026-04-21 蔚来汽车「大模型应用开发实习生（VAS）」岗位匹配分析。

- 硬门槛缺口：
  - 无直接硬门槛缺口（学历/专业/经验/地域/技术主线均命中，语言要求 JD 未显式说明）
- 技能缺口：
  - §3 缺少 RAG / 向量检索实操经验 [致命度: 高] [短期性: 可补（2 周内）]
  - §3 缺少 LangGraph / LlamaIndex 框架使用经验 [致命度: 高] [短期性: 可补（2 周内）]
  - §3 缺少 FastAPI 接口开发经验 [致命度: 中] [短期性: 可补（1 周内）]
  - §3 缺少大模型评估方法了解 [致命度: 中] [短期性: 可补（3–5 天）]
  - Python 工程实操不足（§9 自评 2/5），需要通过具体项目提升（历史遗留）
- 经历缺口：
  - §4 项目经历仅有 1 个纯工具调用 Agent Demo，未覆盖 RAG / 向量检索 / 工作流编排等核心职责 [致命度: 高] [短期性: 可补（2 周内可产出 RAG Demo）]
  - §7 对口实习经历暂空（历史遗留）
- 风险项：
  - JD 要求"每周实习 4 天+、4 个月+"，用户线下出勤能力待确认（取决于 §10 精确时间规划）
  - 4 周计划时间充裕但内容密集，Week 1 交付物未完成将触发连锁延期

---

## 12. 补充说明
- 用户当前项目：OfferClaw —— 基于 OpenClaw / JVS Claw 的求职作战官
- 项目双重目标：① 交付 OpenClaw 养成挑战赛；② 在 2026-05-01 前成长为可写进简历的 AI 应用 / Agent 项目
- 运行平台：JVS Claw（文件空间 + 定时任务 + 对话交互）
- 协作分工：Claude 负责代码实现、配置文件、Prompt 设计、文档草稿；用户负责需求收敛、决策、在 JVS Claw 里实际运行
- 实现语言偏好：Python 3.10+，少依赖，不走 Java 主线
- 其他待归类内容：【待补充】
