# OfferClaw · 项目状态总览

> 本文档是项目进度的**单一事实来源**。每次重大推进后更新。
> 用于：快速回忆当前所处阶段、已做/未做事项、下一步动作。

---

## 元信息

- **项目名**：OfferClaw —— 基于 OpenClaw / JVS Claw 的求职作战官
- **首个真实样本用户**：Zhang Yi（东南大学通信工程硕士，2027-07 毕业）
- **项目双重目标**：
  1. 交付 OpenClaw 养成挑战赛
  2. 2026-05-01 前成长为可写进简历的 AI 应用 / Agent 项目
- **最终形态**：适用于各类用户形象的通用智能体（当前用项目作者做训练验证）
- **状态更新时间**：2026-04-25
- **版本**：V1.5 · 阶段 C（RAG + FastAPI + LangGraph 已交付 → 简历公开化 → 投递准备）
- **GitHub 仓库**：https://github.com/zhangyi-nb1/offerclaw （2026-04-21 首次推送）

---

## 本文档的读者身份 · 核心区分

本文档**只服务于"后台搭建者"视角**。OfferClaw 项目里有两种身份的 Zhang Yi，它们**记录在不同文件里**：

| 维度 | 后台搭建者身份（本文档适用） | OfferClaw 用户身份（daily_log.md 适用） |
|---|---|---|
| 你在做什么 | 搭建 OfferClaw 系统：写 Prompt / 写代码 / 修 bug / 部署 JVS Claw | 作为求职者使用 OfferClaw：按它的规划学 Python / 做项目 / 刷题 / 投简历 |
| 产出 | `.md` Prompt / `.py` 代码 / 配置文件 / 测试 JD 池 | 学习笔记 / 代码练习 / 简历条目 / 投递记录 |
| 记录位置 | **PROJECT_STATUS.md**（本文档）| **daily_log.md**（OfferClaw 运行时用户数据）|
| 读者 | 搭建者本人 / 协作的 Claude | OfferClaw 智能体 / 复盘时的用户本人 |

**决定性规则**：
- 搭 OfferClaw 的活（改 match_job.py、调 API、跑回归）**只记进本文档**，不进 daily_log.md
- 用 OfferClaw 学 / 做 / 投的活（学框架、写项目、投简历）**只记进 daily_log.md**，不进本文档
- 在 MVP 阶段，Day 2 的 Agent Demo 是**两个身份的重合点**：它既是 OfferClaw 项目的代码迭代（后台），也是 Zhang Yi 本人简历的第一个 AI 项目（前台）——但**分别写到两个文件里**，内容会重合，写作角度不同

---

## 一句话项目定位

OfferClaw 是一个**长期运行、带状态、围绕单个求职者成长的执行型 Agent**，核心闭环是：
**画像 → 匹配 → 规划 → 执行 → 复盘 → 回到画像更新**。

它不是岗位推荐机器人，也不是简历生成工具。核心价值在于"长期执行 + 可解释 + 渐进式画像"。

---

## V1.5 总完成度：约 85%（V1 90% + V1.5 RAG/API 已完成 → 待简历 + 投递）

| 维度 | 状态 |
|---|---|
| 身份 / 规则 / 边界层 | ✓ 完成 |
| 用户画像层 | ✓ 完成（§4 已填 Agent Demo + RAG 首条；§11 缺口由 JD #6 匹配自动写入）|
| 岗位匹配层（双通路） | ✓ 完成 · LLM 版 + 规则版都通过 JD #6 端到端回归 |
| 路线规划层 | ✓ 完成 · `plan_prompt.md` + `plan_gen.py` 落地 |
| 执行推进 / 提醒层 | 🟡 90% · daily_log 模板就位 + JVS Claw 3 条定时任务已配置开启 |
| 学习留痕层 | ✓ 完成 · `summary_prompt.md` 9 步契约已落地 |
| 代码实现层（Agent Demo · V1） | ✓ **100%** · `simple_profile_lookup` + 跨会话 `memory.json` + `/clear /save /history` |
| **RAG 检索增强系统（V1.5）** | ✓ **完成** · `rag_agent.py`（手动编排）+ `rag_graph.py`（LangGraph StateGraph）+ `rag_ingest.py` + `rag_tools.py` · Recall@5=0.75 / MRR=0.69 |
| **FastAPI 接口层（V1.5）** | ✓ **完成** · `rag_api.py` 6 端点 + SSE 流式 + Swagger UI 自动文档 |
| JVS Claw 部署 | 🟡 90% · 智能体 `jarvis` 跑通 onboarding / match / plan，3 条定时任务已开 |
| GitHub 公开化 | 🟡 **80%** · 仓库已建，README + PROJECT_STATUS 已同步最新进展，.py 文件已推送 |
| 简历 / 项目栏 | ⏳ **进行中** · 简历描述草稿就绪，待写入正式简历 |

---

## 五大核心模块完成度

### 模块 ① 渐进式用户画像构建 · ✓ 完成
- 12 节画像结构（§0 元信息 → §12 补充）完备
- 真实填充到 ~85%（§4 项目经历仍待把 Agent Demo 作为首条项目条目填入；Agent Demo 的 README 里已有简历描述草稿）
- 首次启动工作流（onboarding_prompt.md）支持双模式写回（自动 / 建议 diff）

### 模块 ② 岗位推荐与匹配分析 · ✓ 完成（双通路都通）
- 规则定义：target_rules.md 完备（硬门槛 6 项 / 软性 6 项 / 三档结论 / 7 项输出结构 / 8 条禁止条款）
- Prompt 工作流：job_match_prompt.md 9 步流程 + 5.1 三档结论 + 5.2 样本定位 + 缺口元数据（致命度 + 短期性）
- 代码实现：match_job.py 三层规则（硬门槛 / 软性 / 结论 + 缺口）
- 真实 JD 池：jd_candidates.md 共 7 份（字节 ×5 + 蔚来 ×1 + 上海 AI 实验室 ×1）
- 已完成一次真实端到端回归（JD #6 蔚来）

### 模块 ③ 学习与求职路线规划 · ✓ 完成
- `plan_prompt.md` —— 9 步规划契约（缺口清单 → 主题分桶 → Week 主题 → Day 任务 → 风险与回退）
- `plan_gen.py` —— 最小代码版，复用 agent_demo 的智谱 JWT，把整篇 prompt 喂 LLM 让其内部走 9 步流程
- 已在 JVS Claw 上跑通 /plan：基于 §11 缺口清单输出了 04-22→04-28 周计划，写入 daily_log.md（每日带主线标签 + 依据 P0-x 编号）

### 模块 ④ 执行推进与提醒 · ⏳ 部分就位
- daily_log.md 模板完整（含今日主线标签 + 偏离度判断 + 明日建议）
- **定位澄清**：daily_log.md 是 OfferClaw 上线后供**前台用户**（按 OfferClaw 规划执行学习 / 做项目的求职者）每日填写的复盘文件，**不记录后台搭建进度**
- 2026-04-15 首条条目是 Onboarding Day 的过渡期条目，内容里混有搭建任务（如"搭建 match_job.py"），属历史遗留——用户可选择保留或清理，Claude 不主动动。从 Day 2 起该文件只应记录学习 / 项目 / 刷题 / 投递类用户行为
- 早晚定时任务需在 JVS Claw 部署时配置（不在本地做）

### 模块 ⑤ 学习留痕总结与动态修正 · ✓ 完成
- `summary_prompt.md` —— 9 步复盘契约（单日模式 / 周度模式分支；按 source_policy A/B/C 给学习留痕打证据等级；判断偏离度并产出明日建议）
- 已配为 JVS Claw 定时任务 `OfferClaw_Daily_Summary`（每天 23:30）+ 周日 21:30 周复盘任务

---

### 模块 ⑥ RAG 检索增强系统（V1.5 新增）· ✓ 完成

**在 OfferClaw 中引入 RAG 能力，使 Agent 能检索 daily_log / user_profile / 匹配报告等文件并回答自然语言问题。**

| 文件 | 作用 | 状态 |
|---|---|---|
| `rag_ingest.py` | 文档入库：读取 Markdown → RecursiveCharacterTextSplitter 分块 → glm-4-embed 向量化 → ChromaDB 持久化 | ✅ |
| `rag_tools.py` | RAG 工具函数：分块 / Embedding 调用 / ChromaDB 检索 / LLM 问答 | ✅ |
| `rag_agent.py` | RAG Agent 主入口（**手动编排**：检索 → Prompt 注入 → LLM → 回答） | ✅ |
| `rag_graph.py` | **LangGraph 声明式工作流**（4 节点 StateGraph + 条件边工具循环） | ✅ |
| `rag_query.py` | 独立检索查询脚本（仅检索，不调 LLM） | ✅ |
| `chroma_db/` | ChromaDB 持久化目录（50 chunks，`offerclaw_docs` 集合） | ✅ |

**架构对比（rag_agent.py vs rag_graph.py）：**

| 维度 | rag_agent.py（手动编排） | rag_graph.py（LangGraph） |
|---|---|---|
| 编排方式 | Python if/else 手动控制流程 | 声明式 StateGraph，节点 + 边定义 |
| 状态管理 | 类属性 `self.conversation_history` | `TypedDict AgentState`，LangGraph 自动传递 |
| 工具循环 | for 循环 + 手动判断 | 条件边 `should_continue_to_tools` 自动路由 |
| 可扩展性 | 新增节点需改类方法 | 新增节点只需 `add_node` + `add_edge` |
| 可观测性 | 手动 print 日志 | LangGraph 原生支持 trace/stream |

**LangGraph 工作流图：**
```
__start__
    ↓
[retrieve]  ← 检索 ChromaDB
    ↓
[build_prompt] ← 注入检索结果到 System Prompt
    ↓
[call_llm] ← 调用 LLM（带 tools）
    ↓
{条件边：有工具调用？}
 ├─ 是 → [execute_tools] → 回到 call_llm（循环）
 └─ 否 → __end__（输出最终回答）
```

**对应蔚来 JD 职责：**
| 蔚来 JD 职责 | 实现状态 |
|---|---|
| 构建基于 RAG 的知识增强问答系统 | ✅ `rag_agent.py` + `rag_graph.py` |
| 文档解析、向量检索 | ✅ `rag_ingest.py` + ChromaDB（50 chunks） |
| 调用链路编排 / LLM 应用工作流 | ✅ LangGraph 4 节点 StateGraph |
| RAG 相关评估方法 | ✅ Recall@5=0.75 / MRR=0.69 |

---

### 模块 ⑦ FastAPI 接口层（V1.5 新增）· ✓ 完成

**把 RAG 检索、岗位匹配、用户画像查询包装为 HTTP API。**

| 端点 | 方法 | 功能 | 状态 |
|---|---|---|---|
| `GET /` | GET | API 信息 + 端点列表 | ✅ |
| `GET /health` | GET | 健康检查（ChromaDB 连接 + 记录数） | ✅ |
| `GET /api/profile` | GET | 获取用户画像摘要 | ✅ |
| `POST /api/query` | POST | RAG 问答（检索 + LLM 整合） | ✅ |
| `POST /api/search` | POST | 仅检索（不调 LLM，返回原始片段） | ✅ |
| `POST /api/match` | POST | 岗位匹配（占位，后续对接 job_match） | ✅ |
| `POST /api/reset` | POST | 清空对话历史 | ✅ |

**技术特点：**
- FastAPI + Pydantic 数据模型 + Uvicorn ASGI 服务器
- Swagger UI 自动文档（`/docs`）
- 懒加载 RAG Agent（启动不阻塞）
- 支持 SSE 流式响应（后续扩展）

**对应蔚来 JD 职责：**
| 蔚来 JD 职责 | 实现状态 |
|---|---|
| 推进系统原型设计、接口开发和上线部署 | ✅ `rag_api.py` 6 端点 + Swagger UI |

---

## 全部文件清单

按"功能层级"分组列出工作目录下的全部文件（不含历史参考文档）。

### 规则与身份层

| 文件 | 行数范围 | 作用 | 完成度 |
|---|---|---|---|
| [SOUL.md](SOUL.md) | ~50 | Agent 身份 / 8 条行为原则 / 5 条硬边界 / 依赖文件索引 | 100% |
| [target_rules.md](target_rules.md) | ~120 | 求职方向 / 硬门槛 6 项 / 软性 6 项 / 三档结论规则 / 8 条禁止条款 | 100% |
| [source_policy.md](source_policy.md) | ~110 | A/B/C 证据等级 + 任务路由表 A + 证据等级表 B（刚重构完） | 100% |

### OfferClaw 前台运行时数据层（前台用户视角，OfferClaw 智能体读写）

| 文件 | 作用 | 完成度 |
|---|---|---|
| [user_profile.md](user_profile.md) | Zhang Yi 12 节画像（作为首个样本用户的真实填充版）| 85%（§4 待 Day 2 Agent Demo 以前台用户视角填入） |
| [daily_log.md](daily_log.md) | 前台用户每日计划/执行/复盘模板 + 2026-04-15 首条（过渡期）条目 | 95% |

### 后台搭建者测试 / 样本数据层

| 文件 | 作用 | 完成度 |
|---|---|---|
| [jd_candidates.md](jd_candidates.md) | **后台回归测试用**的 7 份 JD 候选池（用于验证 job_match_prompt.md 和 match_job.py，不是用户投递记录） | 100% |

### 工作流层（Prompt 契约）

| 文件 | 作用 | 完成度 |
|---|---|---|
| [onboarding_prompt.md](onboarding_prompt.md) | 首次启动 6 步流程 + Mode A/B 双模式写回 | 100% |
| [job_match_prompt.md](job_match_prompt.md) | 匹配 JD 的 9 步流程 + 5.2 样本定位（已放宽）+ 缺口元数据 | 100% |

### 代码实现层

| 文件 | 作用 | 完成度 |
|---|---|---|
| [match_job.py](match_job.py) | 规则版 JD 匹配 · 三层（硬门槛 / 软性 / 结论）· 含 check_experience 质性识别 | 90% |
| [day1_api_starter.py](day1_api_starter.py) | LLM API 调用起点 + 智谱 JWT 认证 + .env.local 加载 | 100% |
| [agent_demo.py](agent_demo.py) | Agent 主入口 · LLM 调用 + tool call loop + 命令行交互 · 4 级阶梯测试通过 | 100% |
| [tools.py](tools.py) | Agent 工具模块 · 3 个工具函数（时间 / 安全计算器 / 回显）+ OpenAI 兼容 schema | 100% |
| [README.md](README.md) | Agent Demo 运行说明 + 架构图 + 简历描述草稿 | 100% |
| [requirements.txt](requirements.txt) | 完整依赖清单（ChromaDB / LangGraph / FastAPI / Pydantic） | 100% |

### RAG + API 层（V1.5 新增）

| 文件 | 作用 | 完成度 |
|---|---|---|
| [rag_ingest.py](rag_ingest.py) | 文档向量化入库：Markdown → 分块 → Embedding → ChromaDB | 100% |
| [rag_tools.py](rag_tools.py) | RAG 工具函数（分块 / Embedding / 检索 / LLM 调用） | 100% |
| [rag_agent.py](rag_agent.py) | RAG Agent 主入口（手动编排） | 100% |
| [rag_graph.py](rag_graph.py) | **LangGraph 声明式工作流**（4 节点 StateGraph + 条件边循环） | 100% |
| [rag_api.py](rag_api.py) | **FastAPI HTTP 接口层**（6 端点 + SSE 流式 + Swagger UI） | 100% |
| [rag_query.py](rag_query.py) | 独立检索查询脚本 | 100% |
| `chroma_db/` | ChromaDB 持久化目录（50 chunks，`.gitignore` 排除） | ✅ 运行中 |

### 配置与安全层

| 文件 | 作用 | 完成度 |
|---|---|---|
| [.env.local](.env.local) | 本地密钥存放（智谱 API Key） | 100% |
| [.gitignore](.gitignore) | Git 忽略清单（保护 .env.local 等敏感文件） | 100% |

### 本文档

| 文件 | 作用 |
|---|---|
| [PROJECT_STATUS.md](PROJECT_STATUS.md) | 本文档 —— 项目状态单一事实来源 |

### 历史参考（不由项目维护）

- `OfferClaw_Claude_直接投喂提示词.md` —— 用户给 Claude 的原始主控提示词
- `OfferClaw_项目与竞赛推进指导报告.docx` —— 用户自有的指导文档

---

## 已修复的问题清单（截至 2026-04-15）

### 第一批 · 基础文件修正（首个 6 个骨架文件建立后立即做）
- 把 user_profile.md 从模板状态改为"Zhang Yi 真实填充版"
- 把 onboarding_prompt.md 改为"双模式写回"（A 自动写 / B 建议 diff 片段）
- daily_log.md 增加"今日主线标签"字段（5 值封闭集合，便于周度聚合）

### 第二批 · 真实 JD 测试前的对齐
- user_profile.md 字段标准化（工作性质偏好 / 期望薪资 / 明确不做的方向 三处）
- match_job.py 的 DEMO_PROFILE 同步到 Zhang Yi 真实画像
- match_job.py 软性维度 4 个函数的 `?` 分支全部映射到 `部分命中`（对齐三值契约）

### 第三批 · 首轮 LLM 匹配报告审阅后的契约升级
- job_match_prompt.md 第 3 步：硬门槛判断必须基于 JD 显式条款，禁止从业务背景推断
- job_match_prompt.md 第 4 步：软性维度禁用 `?`，profile 未填或 JD 未明说时一律 `部分命中`
- job_match_prompt.md 第 5 步：拆成 5.1 三档结论 + 5.2 样本定位（四分类正交维度）
- job_match_prompt.md 第 6 步：缺口清单强制带 `[致命度]` + `[短期性]` 元数据标签
- job_match_prompt.md 第 8 步：输出模板同步加入 5.2 样本定位和缺口元数据

### 第四批 · Day 1 Task 1 部署与踩坑
- 把智谱 GLM-4-Flash 作为 day1_api_starter.py 默认 provider
- 新建 .env.local + .gitignore 完成凭证安全隔离
- 手写智谱 JWT 签名（纯标准库，无 PyJWT 依赖）—— 因为直接 Bearer 在新 key 上被拒
- 凭证问题根因定位：.env.local 里的 key 是旧 key，用户以为换了但没真的换
- 最终跑通 glm-4-flash API 全链路

### 第五批 · JD #6 端到端回归后的契约与规则修复
- **发现 ①**：match_job.py 的 check_experience 只匹配 `N 年` 模式，忽略"项目经验"等质性要求 → 新增 QUALITATIVE_EXP_KEYWORDS + SOFTEN_HINTS + _scan_qualitative_exp 辅助函数，改判断优先级为 5 级
- **发现 ②**：job_match_prompt.md 5.2 "短期可投样本" 触发条件过紧，JD #6 这种"暂不建议 + 方向对 + 缺口可补"的边缘情况无归类 → 放宽 5.2 条件允许 5.1 ∈ {中长期可转向, 暂不建议投递}
- **发现 ③**：规则版建议误导（由发现 ① 链式传播） → 发现 ① 修好后自动消除
- **附带**：source_policy.md §4 平台用途表混写 → 拆成正交的表 A（任务路由）+ 表 B（证据等级）

### 第七批 · 阶段 A 闭环补齐（2026-04-21）
- **plan_prompt.md（9 步规划契约）+ plan_gen.py（最小代码版）**：从 §11 缺口清单 → 4 周路线（周/日两层 + 主线标签 + 依据缺口编号）；plan_gen.py 不在本地复现 9 步逻辑，整篇 prompt 喂 LLM 让其内部走流程，只负责组装上下文 + 调 LLM + 落盘到 plans/
- **tools.py 新增 `simple_profile_lookup`**：按章节抽 user_profile.md，带 mtime 缓存 + 别名匹配（"1" / "§1" / "基础信息" 都能命中），TOOLS_SCHEMA 扩到 4 项
- **agent_demo.py 跨会话 memory**：新增 `load_memory` / `save_memory` + `/clear` `/save` `/history` 命令；`MEMORY_PATH = "memory.json"`；剔除 system prompt 落盘（保证每次启动用最新版 prompt），每轮成功后立即保存（防崩溃丢历史）
- **summary_prompt.md（9 步复盘契约）**：单日 / 周度双模式；按 source_policy A/B/C 标证据等级；输出"偏离度判断 + 明日建议"
- **deployment.md 骨架**：JVS Claw 部署文档（system prompt 配置 / 文件引用语法 / 定时任务配置 / 故障排查）

### 第八批 · JVS Claw 部署 + GitHub 推送（2026-04-21）
- **JVS Claw 工作空间 `openclaw-control-ui` + 智能体 `jarvis`（智能客服·严谨专业版）**：上传全部 .md 文件 + 配 system prompt
- **跑通三条主指令**：onboarding（含 §11 缺口写回 user_profile.md）/ /match（JD #6 端到端，5 张截图验证）/ /plan（输出 04-22→04-28 周计划写入 daily_log.md）
- **3 条定时任务已配置开启**：
  - `OfferClaw_Daily_Plan` 每天 09:00（早间生成今日计划）
  - `OfferClaw_Daily_Summary` 每天 23:30（晚间复盘）
  - 周日 21:30 周复盘任务（基于 summary_prompt.md 周度模式）
- **关键踩坑**：JVS Claw 写文件**只改云端副本，不会自动同步回本地** → 已写入 `.vscode/sync_protocol.md` 同步规约
- **GitHub 首推**：仓库 https://github.com/zhangyi-nb1/offerclaw 已建，目前已推 8 个 .md 文件 + .gitignore（基础版只忽略 .DS_Store / *.pyc / __pycache__/）。**未推**：所有 .py 文件、PROJECT_STATUS.md、AGENT_DEMO.md、deployment.md
- **本地同步**：从云端 raw 拉回 daily_log.md（13KB，含 04-22→04-28 周计划）+ user_profile.md（8.3KB，含 §11 缺口）覆盖本地

### 第六批 · Agent Demo 最小可运行版落地
- **核心产物**：`agent_demo.py`（主循环 + LLM 调用 + tool call loop）+ `tools.py`（3 个工具 + OpenAI 兼容 schema）+ `README.md`（运行说明 + 架构图 + 简历描述草稿）
- **技术栈**：智谱 GLM-4-Flash + OpenAI 兼容 function calling + 手写 JWT 签名，纯标准库 + `requests`，无 LangChain / LlamaIndex 等第三方 Agent 框架依赖
- **已注册工具**：`get_current_time` / `calculator`（AST 白名单解析，拒绝 `__import__` 等注入）/ `echo`
- **Agent 主循环**：单轮对话内最多 5 次 tool call 迭代（防死循环保险丝），工具结果以 `role=tool` 追加进 messages，继续下一轮 LLM 调用
- **4 级阶梯测试全通过**：
  - 阶梯 1 · 无工具闲聊 ✓（LLM 正确识别无需工具）
  - 阶梯 2 · 单工具调用 ✓（`get_current_time` 被正确调用）
  - 阶梯 3 · 带参数工具调用 ✓（`calculator("5*61") → 305`）
  - 阶梯 4 · 多工具链式调用 ✓（`get_current_time → calculator` 链式串联，计算 2026-05-01 还剩天数）
- **代码拆分**：先写自包含的 `agent_demo.py` 跑通全链路，之后拆出 `tools.py` 并用 `from tools import TOOL_FUNCTIONS, TOOLS_SCHEMA` 导入；验证 `agent_demo.TOOL_FUNCTIONS is tools.TOOL_FUNCTIONS = True`
- **本批结果**：代码实现层完成度从 30% → 65%，OfferClaw V1 从"只有 Prompt + 规则脚本"跃迁到"有自己写的 Agent 代码"——可对外演示、可写进简历

### 第九批 · RAG + LangGraph + FastAPI（V1.5，2026-04-22 ~ 04-25）
- **`rag_ingest.py` + `rag_tools.py`**：文档入库链路（RecursiveCharacterTextSplitter 分块 → glm-4-embed 向量化 → ChromaDB 持久化）；工具函数（分块 / Embedding / 检索 / LLM 调用）
- **`rag_agent.py`（手动编排）**：检索 → Prompt 注入 → LLM → 回答，完整 RAG 问答链路
- **`rag_graph.py`（LangGraph 声明式工作流）**：4 节点 StateGraph（retrieve → build_prompt → call_llm → execute_tools），条件边自动路由工具循环
- **`rag_api.py`（FastAPI 接口层）**：6 端点（`/health` · `/api/profile` · `/api/query` · `/api/search` · `/api/match` · `/api/reset`）+ Swagger UI 自动文档 + SSE 流式支持
- **`rag_query.py`**：独立检索脚本（仅检索，不调 LLM）
- **`requirements.txt` 更新**：补充 chromadb / langgraph / fastapi / uvicorn / pydantic
- **`chroma_db/`**：50 chunks 知识库（`offerclaw_docs` 集合）
- **本批结果**：V1 从"纯 Agent Demo"跃迁到"带 RAG 检索 + LangGraph 工作流 + FastAPI 接口的 AI 应用系统"；对应蔚来 JD 的"RAG 知识增强问答 + 调用链路编排 + 接口开发"三项职责
- **指标**：Recall@5 = 0.75 · MRR = 0.69 · pytest 17/18

---

## 当前待办清单（截至 2026-04-25）

> **注意**：本清单只列**后台搭建视角**的任务。同一天里前台用户视角的学习 / 做项目 / 投递活动由 daily_log.md 管理，不在本清单。

### ✅ 已完成（P1–P4 全部）

- [x] Agent Demo 最小可运行版 + 4 级阶梯测试
- [x] JVS Claw 部署 + 3 条定时任务
- [x] 规划模块（plan_prompt + plan_gen）
- [x] RAG 系统（rag_agent + rag_graph + rag_ingest + rag_tools）
- [x] FastAPI 接口层（6 端点 + Swagger UI）
- [x] LangGraph 工作流（4 节点 StateGraph）

### ⏳ 阶段 C 待办（距 05-01 剩余 6 天）

- [ ] **简历 V1 定稿**：把 RAG + LangGraph + FastAPI 写入简历项目描述
- [ ] **docs/interview_qa.md**：准备 RAG / LangGraph 面试问答卡
- [ ] **docs/resume_pitch.md**：更新简历介绍（反映 V1.5 新增能力）
- [ ] **用户画像 §4 补充**：把 Agent Demo + RAG 作为首条项目经历填入
- [ ] **比赛材料**：架构图更新（V1.5 新增 RAG 层）+ 演示视频 + README
- [ ] **投递准备**：挑 1-2 份"当前适合投递"的 JD 做实际投递

---

## 已知技术债务（V1.5 以后再清）

1. **target_rules.md §1 方向硬编码**：当前写死了 Agent/AI/Prompt 三条，未来支持多用户时应参数化为"读 profile §2 目标方向"
2. **match_job.py DEMO_PROFILE 是字典镜像**：未来多用户需要一个真正的 Markdown 解析器从 user_profile.md 构造 profile dict
3. **match_job.py 的关键词列表**（MAIN_DIRECTION_KWS / AI_FRIENDLY_MAJORS / COMMON_CITIES / QUALITATIVE_EXP_KEYWORDS / SOFTEN_HINTS）**维护成本高**，V1.5 可能考虑拆到独立的 config 文件
4. **match_job.py 的 `check_tech_mainline` 用 `b.split()[0]` 取 key**，如果 profile 写"纯前端"这种短语会误判，当前靠用户维护清洁的 token 列表绕过
5. **规则版的项目契合度**目前只判"有/无项目"，不判"项目与 JD 语义对齐度"——语义匹配是 V1.5 的事
6. **daily_log.md 周度聚合逻辑缺失**：周日 21:00 触发的周度复盘需要真实实现，不能只靠 LLM 现场读 7 天日志
7. **JVS Claw 定时任务机制未知**：需要 Day 3 部署时摸清实际支持方式

---

## 风险与风向标

### 已识别风险

1. **时间紧**：距 2026-05-01 还有 6 天，简历定稿 + 投递准备需加速
2. **项目经历 §4 尚未完整**：Agent Demo 和 RAG 作为项目条目仍需正式写入 user_profile.md §4
3. **RAG 评估数据有限**：Recall@5=0.75 / MRR=0.69 基于 50 chunks，知识库扩大后指标可能波动
4. **FastAPI /api/match 仍是占位**：尚未对接 job_match_prompt.md 的完整 9 步流程

### 如何判断项目进展健康

**后台搭建视角**（本文档关心的，用于判断 OfferClaw 系统本身的推进健康度）：
- **绿灯**：本文档的"V1 完成度总览"表每 3 天至少有 1 个维度向前推进
- **黄灯**：同一个技术债连续出现在"已知技术债务"清单超过 2 次未处理
- **红灯**：主线模块（匹配 / 规划 / 执行）连续 3 天没有任何 Prompt 或代码迭代

**前台用户视角**（daily_log.md 关心的，本文档不负责监督但此处列出便于区分）：
- 绿灯：daily_log 近 3 天主线标签有 ≥ 2 次 `[补项目]` 或 `[投递准备]`
- 黄灯：连续 2 天以上 `[补技能]` 占主导（学习陷阱风险）
- 红灯：连续 3 天没产出任何可落到 user_profile.md §4 的东西

---

## 下一次对话启动时的默认动作

当用户回来时，Claude 应该先读本文档确认当前阶段，然后按下面的优先级决策：

| 用户发来的话 | Claude 应该做的 |
|---|---|
| "开始 Day 2" / "做 Agent Demo" | 按 P1 清单给完整的 Day 2 任务 + 代码骨架，最小可运行的工具调用循环 |
| "跑一下 JD #x" | 以 OfferClaw 身份按 job_match_prompt.md 对指定 JD 跑完整 9 步，同时用 match_job.py 跑规则版对比 |
| "我在 JVS Claw 里搭智能体卡住了" | 按用户描述的具体卡点给针对性指令，必要时更新 JVS Claw 部署文档 |
| "我在 daily_log 里该写什么" | 提醒用户 daily_log 是前台用户视角，只记学习 / 做项目 / 刷题 / 投递类活动；搭 OfferClaw 的活要记进本文档 |
| "今天状态不好" / 任何情绪表达 | 不发散、不煽情，问一句"想今天减量还是休息"，按回答给对应的缩减方案 |

---

## 维护纪律 · 两文件分工

**本文档 PROJECT_STATUS.md 的更新范围（后台搭建视角）**
- ✓ 记录：Prompt / 代码 / 配置文件的结构性变更
- ✓ 记录：发现的技术债 / 修复记录 / 模块完成度调整
- ✓ 记录：JVS Claw 部署相关的配置和卡点
- ✗ 不记录：Zhang Yi 作为 OfferClaw 用户的学习、做项目、投简历活动（这些进 daily_log.md）
- ✗ 不记录：搭建者的情绪、状态、灵感——本文档不是日记

**daily_log.md 的更新范围（前台用户视角）**
- ✓ 记录：按 OfferClaw 规划执行的学习 / 做项目 / 刷题 / 投递行为
- ✓ 记录：每日偏离度判断、明日建议、主线标签
- ✗ 不记录：搭建 OfferClaw 的开发活动
- ✗ 不记录：搭建者调试 / 修 bug / 建文档的细节

**何时写哪一份** —— 问自己一个问题：
> "我现在做的事，是在**增加 OfferClaw 系统的功能**（进 PROJECT_STATUS.md），还是在**使用 OfferClaw 作为工具推进我的求职**（进 daily_log.md）？"

如果两者同时发生（如 Day 2 的 Agent Demo），**在两个文件里各写一条，写作角度不同**：
- 本文档写"OfferClaw V1 代码层从 30% → 60%，新增工具调用能力..."
- daily_log.md 写"今日主线：补项目 / 完成 Agent Demo 最小闭环 / 耗时 5 小时 / 学到了..."

**更新节奏**
- **每次完成一个 P 级任务**：追加到"已修复"清单并更新相关模块完成度
- **每次发现新的技术债**：追加到"已知技术债务"
- **每次重大结构性变更完成**：更新"状态更新时间"字段
- **每完成一个模块**：在"V1 完成度总览"表里调整对应维度的状态

---

**本文档是活文件**。有问题直接改，改完告诉 Claude。
