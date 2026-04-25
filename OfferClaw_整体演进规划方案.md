# OfferClaw 整体演进规划方案

> 作用：本文档用于说明 OfferClaw 项目最终完成后应具备哪些核心功能、涉及哪些技术模块，以及如何从当前项目状态逐步演进为一个完整、可展示、可写入简历的 AI Agent 项目。  
> 定位：这是一个**大纲性质的全局路线文件**，不是立即执行的详细开发文档。后续每个阶段可以再拆成独立任务文档。  
> 当前建议：先完成阶段 0，再进入阶段 1，不要跳级直接上复杂框架。

---

## 1. 项目最终定位

OfferClaw 最终应成为一个面向求职者的长期执行型 AI Agent 系统。

它不是普通聊天机器人，也不是单次简历生成器，而是围绕一个求职者的长期成长过程，持续完成：

```text
用户画像构建
→ 岗位匹配分析
→ 能力缺口识别
→ 学习与项目路线规划
→ 每日执行推进
→ 学习留痕复盘
→ 动态更新画像与计划
```

最终形态可以概括为：

> 一个具备长期状态、文件记忆、岗位匹配、路线规划、工具调用、复盘调整和可服务化接口的求职执行 Agent。

---

## 2. 当前项目所处阶段

当前 OfferClaw 已经不再是概念原型，而是一个具备初步运行能力的 V1 项目。

当前已具备的基础包括：

1. **规则与身份层**
   - `SOUL.md`
   - `target_rules.md`
   - `source_policy.md`
   - 明确 Agent 身份、行为边界、证据规则和匹配原则

2. **用户画像层**
   - `user_profile.md`
   - 支持从不完整简历起步
   - 已围绕首个真实用户进行画像填充

3. **岗位匹配层**
   - `job_match_prompt.md`
   - `match_job.py`
   - 支持 Prompt 版和规则代码版双通路岗位匹配

4. **基础 Agent 代码层**
   - `agent_demo.py`
   - `tools.py`
   - 支持最小 LLM 调用、工具路由、多轮对话和 Function Calling

5. **项目文档层**
   - `README.md`
   - `PROJECT_STATUS.md`
   - 已能说明项目目标、功能模块、运行方式和当前进度

当前的主要短板是：

1. 项目状态文档与仓库真实能力需要进一步统一
2. 端到端演示链还需要固定
3. 文件级 RAG 尚未稳定成核心能力
4. 规划、执行、复盘模块还需要形成更强闭环
5. FastAPI、LangGraph、Docker 等工程化能力尚未引入
6. 多用户泛化与评测体系尚未完成

---

## 3. 项目最终应具备的核心功能

OfferClaw 成型后，应至少具备以下 8 类能力。

### 3.1 渐进式用户画像构建

目标：允许用户从不完整简历开始，由 Agent 逐步追问、补全和维护画像。

应具备能力：

- 读取用户基础信息
- 记录学历、专业、技能、项目、竞赛、实习、偏好
- 区分已知信息与待补充信息
- 根据后续交互动态更新用户画像
- 支持多个用户画像或 Persona 测试样本

核心文件：

- `user_profile.md`
- `onboarding_prompt.md`
- 后续可扩展为 `profiles/` 目录

---

### 3.2 岗位匹配与方向推荐

目标：根据用户画像和 JD，判断岗位是否适合当前用户，并输出可解释的匹配结果。

应具备能力：

- 解析 JD 基本信息
- 检查硬门槛
- 分析软性匹配维度
- 输出三档结论：
  - 当前适合投递
  - 当前暂不建议投递
  - 中长期可转向
- 生成缺口清单
- 给出下一步建议
- 支持 Prompt 版和 Python 规则版对照验证

核心文件：

- `target_rules.md`
- `job_match_prompt.md`
- `match_job.py`
- `jd_candidates.md`

---

### 3.3 能力缺口识别

目标：把岗位要求和用户画像之间的差距转成具体、可执行的任务。

应具备能力：

- 识别硬门槛缺口
- 识别技能缺口
- 识别项目/经历缺口
- 标注短期可补与短期不可补
- 为路线规划模块提供输入

核心输出：

```text
硬门槛缺口
技能缺口
经历缺口
短期可补项
长期补强项
```

---

### 3.4 学习与项目路线规划

目标：根据缺口清单，生成阶段性学习与项目推进路线。

应具备能力：

- 从缺口清单生成 4 周计划
- 按周拆分目标
- 按日生成任务
- 区分主线标签：
  - 补技能
  - 补项目
  - 补面试
  - 岗位调研
  - 投递准备
- 支持用户调整计划
- 根据复盘结果动态修正后续计划

核心文件：

- `plan_gen.py`
- `plan_prompt.md`
- `daily_log.md`

---

### 3.5 执行推进与每日复盘

目标：让 OfferClaw 不只给建议，而是持续推动用户执行。

应具备能力：

- 生成每日任务
- 记录完成情况
- 记录学习留痕
- 判断是否偏离主线
- 生成明日建议
- 每周生成阶段性复盘
- 更新用户画像中的能力和项目进展

核心文件：

- `daily_log.md`
- `summary_prompt.md`
- 后续可扩展为 `weekly_review.md`

---

### 3.6 文件级 RAG 与项目记忆

目标：让 Agent 能基于项目文件回答问题，而不是只依赖模型记忆。

应具备能力：

- 读取 Markdown 文件
- 对项目文件进行分块
- 基于关键词或向量检索相关片段
- 回答时引用来源文件
- 支持查询：
  - 当前项目进度
  - 用户当前缺口
  - 哪份 JD 更适合
  - 下一步应做什么

优先支持的文件：

- `user_profile.md`
- `PROJECT_STATUS.md`
- `jd_candidates.md`
- `daily_log.md`
- `README.md`

可引入技术：

- 关键词检索
- 本地 JSON 索引
- 智谱 `embedding-3`
- cosine similarity
- 后期可选 Chroma / FAISS

---

### 3.7 Agent 工具调用与工作流

目标：让 OfferClaw 具备真实 Agent 能力，而不是只做文本生成。

当前已具备：

- LLM 调用
- Function Calling
- 工具路由
- 多轮对话
- 时间工具
- 计算器工具
- echo 测试工具

后续可扩展：

- `profile_lookup`
- `jd_lookup`
- `rag_search`
- `match_job`
- `generate_plan`
- `summarize_daily_log`

最终目标：

```text
用户输入目标
→ Agent 判断需要哪些工具
→ 调用相关工具
→ 汇总结果
→ 输出可执行方案
```

---

### 3.8 服务化与部署

目标：让项目从本地脚本逐步演进为可服务化、可部署、可展示的工程项目。

应具备能力：

- 本地 CLI 运行
- JVS Claw 文件空间部署
- JVS Claw 对话运行
- FastAPI 接口服务
- 自动生成 API 文档
- Docker 可选部署
- GitHub README 可复现运行流程

可引入技术：

- JVS Claw
- FastAPI
- Uvicorn
- Pydantic
- Docker
- pytest
- GitHub Actions

---

## 4. 多阶段演进路线

---

## 阶段 0：当前版本收口 · 简历可投递切片

### 阶段目标

把当前项目从“内容较多”收束成一个清晰、可信、能放进简历的版本。

### 主要任务

1. 统一 README、PROJECT_STATUS、GitHub 仓库文件树的状态口径
2. 修正过期说明和状态漂移
3. 固定一条最短端到端演示链
4. 准备截图、输入输出案例和演示脚本
5. 把 Agent Demo 写入 `user_profile.md` 项目经历
6. 形成第一版简历项目描述

### 端到端演示链

```text
onboarding
→ job match
→ plan generation
→ daily summary
```

### 完成标志

- README 30 秒内能让人看懂项目
- GitHub 文件状态和项目状态文档一致
- 有一条可复现 Demo
- 简历中能写出 3 条技术亮点
- 项目可以作为“进行中的 AI Agent 项目”投递

### 暂不做

- LangGraph
- FastAPI
- Web UI
- 复杂 RAG
- 多用户系统

---

## 阶段 1：V1.1 · 最小文件级 RAG

### 阶段目标

让 Agent 能基于项目内文件回答问题，体现“长期状态”和“项目记忆”。

### 主要任务

1. 读取本地 Markdown 文件
2. 对文件进行分块
3. 建立最小索引
4. 支持基于关键词或 embedding 的检索
5. 回答时附带来源文件
6. 将 RAG 工具接入 Agent Demo

### 可引入技术

优先级从低到高：

```text
Python 标准库
→ 关键词检索
→ JSON 索引
→ 智谱 embedding-3
→ cosine similarity
→ Chroma / FAISS
```

### 推荐文件

```text
rag_tools.py
rag_index.json
test_rag_chunking.py
test_rag_retrieve.py
```

### 完成标志

Agent 能回答：

- “我当前项目进展到哪了？”
- “我目前最大的缺口是什么？”
- “我适合哪份 JD？”
- “下一步应该做什么？”

并且回答能基于文件片段，而不是纯模型编造。

---

## 阶段 2：V1.2 · 规划与复盘闭环稳定化

### 阶段目标

把“岗位缺口 → 学习计划 → 每日任务 → 晚间复盘”的链路做稳定。

### 主要任务

1. 从岗位匹配结果读取缺口清单
2. 生成 4 周计划
3. 生成每日任务
4. 将任务写入 `daily_log.md`
5. 晚间读取执行结果
6. 给出偏离度判断和明日建议
7. 必要时更新用户画像

### 可引入技术

- Pydantic
- JSON 中间结果
- pytest
- 规则模板 + LLM 润色

### 完成标志

输入一份岗位匹配结果后，系统能输出：

```text
4 周路线
本周目标
今日任务
晚间复盘
明日建议
```

并且任务可以直接执行。

---

## 阶段 3：V1.3 · JVS Claw 部署与运行闭环

### 阶段目标

让 OfferClaw 在 JVS Claw 上真实运行，而不是只停留在本地脚本。

### 主要任务

1. 上传核心 Markdown 文件
2. 配置系统提示词
3. 跑一次 onboarding
4. 跑一次岗位匹配
5. 跑一次路线规划
6. 跑一次复盘总结
7. 记录平台真实行为和限制

### 需要确认的平台行为

- 文件如何引用
- 文件是否能自动读取
- 文件是否能自动写回
- 定时任务如何配置
- 工具调用如何接入
- CloudSpace 是否稳定持久化

### 推荐产物

```text
deployment.md
jvs_claw_runbook.md
jvs_test_cases.md
screenshots/
```

### 完成标志

能在 JVS Claw 上跑通：

```text
画像初始化
→ JD 匹配
→ 计划生成
→ 每日复盘
```

---

## 阶段 4：V2 · FastAPI 服务化

### 阶段目标

把核心能力封装成 API，使项目更接近工程化后端项目。

### 什么时候做

满足以下条件后再做：

1. V1 端到端 Demo 稳定
2. 最小 RAG 已可用
3. 规划和复盘链路已稳定
4. JVS Claw 部署链路已明确

### 推荐接口

```text
POST /profile/analyze
POST /job/match
POST /plan/generate
POST /summary/daily
POST /rag/search
GET  /health
```

### 可引入技术

- FastAPI
- Uvicorn
- Pydantic
- Python logging
- pytest
- requests / httpx

### 完成标志

- 本地可启动 API 服务
- Swagger 页面可访问
- 至少 3 个核心接口能跑通
- README 中有 curl 示例

---

## 阶段 5：V2.1 · LangGraph 工作流重构

### 阶段目标

当系统流程变复杂后，用 LangGraph 管理状态流转和多节点工作流。

### 什么时候引入

只有出现以下情况时才引入：

1. 流程状态传递开始混乱
2. 工具数量超过 5 个
3. 多轮任务需要暂停和恢复
4. 需要 human-in-the-loop
5. Prompt 文件已经难以维护完整流程

### 推荐图结构

```text
profile_node
→ match_node
→ gap_node
→ plan_node
→ action_node
→ summary_node
→ memory_update_node
→ human_review_node
```

### 可引入技术

- LangGraph
- StateGraph
- checkpoint
- conditional edge
- human-in-the-loop
- tool node

### 完成标志

系统能以状态图方式跑通：

```text
画像 → 匹配 → 缺口 → 规划 → 执行 → 复盘 → 更新
```

并支持中途等待用户确认。

---

## 阶段 6：V2.2 · 多用户与泛化验证

### 阶段目标

从服务单个真实用户，扩展到能适配多类求职者画像。

### 主要任务

1. 抽离用户画像配置
2. 支持多个 profile
3. 将求职方向从硬编码改成读取 profile
4. 构造多种 persona 画像
5. 对不同用户跑回归测试

### 推荐目录

```text
profiles/
  zhangyi.md
  persona_cs_undergrad.md
  persona_non_cs_transfer.md
  persona_agent_project.md

configs/
  direction_rules.yaml
  city_rules.yaml
  skill_taxonomy.yaml
```

### 测试用户类型

1. 计算机专业本科
2. 非计算机转 AI 应用
3. 有 Agent 项目但工程弱
4. 有实习但 AI 弱
5. 通信 / 电子 / 自动化相关专业

### 完成标志

- 至少 3 个 persona 能跑完整链路
- 不同画像能得到合理差异化建议
- 系统不再只围绕单个用户硬编码

---

## 阶段 7：V3 · 产品化与展示

### 阶段目标

让 OfferClaw 成为一个可以用于求职展示、面试讲解和长期迭代的完整项目。

### 核心产物

1. GitHub README 最终版
2. 项目架构图
3. 演示视频
4. 项目复盘文档
5. 简历项目描述
6. 面试问答卡片
7. 技术难点总结
8. 后续规划说明

### 可选工程化能力

- Dockerfile
- GitHub Actions
- pre-commit
- logging
- tests/
- examples/
- docs/
- issue templates

### 可选展示方式

- JVS Claw 运行截图
- CLI 演示
- Gradio / Streamlit 轻量前端
- API Swagger 页面
- GitHub README GIF

### 完成标志

面试官打开 GitHub 后能快速理解：

1. 项目解决什么问题
2. 系统怎么运行
3. 你写了哪些核心代码
4. 使用了哪些 Agent 技术
5. 项目还有哪些后续演进空间

---

## 5. 技术引入优先级

### 5.1 立即保留

当前已经适合继续保留的技术：

- Python
- Markdown 配置体系
- requests
- 智谱 GLM API
- Function Calling
- JVS Claw
- JSON 文件状态
- pytest
- GitHub README

---

### 5.2 短期引入

适合下一阶段引入：

- 最小文件级 RAG
- 智谱 `embedding-3`
- cosine similarity
- Pydantic
- Python logging
- 简单 JSON 索引

---

### 5.3 中期引入

适合项目稳定后引入：

- FastAPI
- Uvicorn
- API schema
- Docker
- Chroma / FAISS

---

### 5.4 后期引入

只有复杂度上来后再引入：

- LangGraph
- checkpoint
- human-in-the-loop
- 多用户 profile
- CI/CD
- 轻量前端

---

### 5.5 暂不引入

当前阶段不建议引入：

- 大型数据库
- 复杂前端
- 多 Agent 架构
- 自动投递
- 招聘网站爬虫
- 大模型训练或微调
- 复杂推荐算法

---

## 6. 技术选择原则

后续每引入一个新技术，都必须回答以下问题：

1. 它解决当前哪个真实问题？
2. 不引入它会有什么阻塞？
3. 它是否会增加过多维护成本？
4. 它是否能增强简历或面试叙事？
5. 它是否和当前阶段匹配？

对应关系如下：

| 技术 | 解决的问题 |
|---|---|
| RAG | 让 Agent 基于项目文件回答，减少幻觉 |
| Embedding | 提高文件检索语义能力 |
| Pydantic | 约束计划、匹配、复盘输出结构 |
| FastAPI | 将模块封装为服务接口 |
| LangGraph | 管理复杂多步骤工作流 |
| Docker | 提升部署可复现性 |
| pytest | 提升规则稳定性 |
| JVS Claw | 承载实际对话与执行场景 |
| README / Demo | 提升对外展示可信度 |

---

## 7. 项目最终功能蓝图

OfferClaw 最终应形成以下模块体系：

```text
用户交互层
├── JVS Claw 对话入口
├── CLI Demo
└── 后期可选 Web / API

状态与文件层
├── user_profile.md
├── daily_log.md
├── PROJECT_STATUS.md
├── jd_candidates.md
└── RAG index

能力模块层
├── Onboarding
├── Job Match
├── Gap Analysis
├── Plan Generation
├── Daily Summary
├── RAG Search
└── Memory Update

Agent 工具层
├── profile_lookup
├── jd_lookup
├── rag_search
├── match_job
├── generate_plan
├── summarize_log
└── calculator / time / echo

工程服务层
├── FastAPI
├── Pydantic
├── pytest
├── Docker
└── deployment docs

工作流编排层
└── LangGraph
    ├── profile_node
    ├── match_node
    ├── plan_node
    ├── summary_node
    └── human_review_node
```

---

## 8. 最终简历叙事方向

项目最终应被包装为：

> 一个基于 Python、LLM Function Calling、Markdown 状态文件、RAG 与工作流编排的求职执行型 AI Agent 系统，支持用户画像构建、岗位匹配、缺口识别、学习规划、每日复盘和动态更新。

可强调能力：

1. Agent 工具调用
2. Function Calling
3. 规则 + LLM 双通路
4. 文件级 RAG
5. 长期状态管理
6. 规划与执行闭环
7. FastAPI 服务化
8. LangGraph 工作流治理
9. JVS Claw 部署
10. 简历与求职场景落地

---

## 9. 阶段节奏建议

### 第 1 周

主线：V1 收口

- README 对齐
- PROJECT_STATUS 对齐
- 端到端 Demo
- JVS Claw 初步部署
- 简历项目条目初稿

---

### 第 2 周

主线：RAG + 规划闭环

- 最小文件级 RAG
- 缺口到计划
- daily_log 复盘
- 本地回归测试

---

### 第 3 周

主线：服务化

- FastAPI
- Pydantic
- API 文档
- pytest
- 最小接口测试

---

### 第 4 周

主线：工作流治理或展示增强

二选一：

1. 若流程复杂：引入 LangGraph
2. 若求职更紧：优先完善 README、Demo、简历和投递材料

---

### 第 5 周以后

主线：泛化和产品化

- 多用户 profile
- Persona 测试
- Docker
- CI/CD
- 轻量前端
- 面试材料整理

---

## 10. 当前最重要的执行原则

1. 先收口，再增强
2. 先证明闭环，再引入框架
3. 先做本地可运行，再做服务化
4. 先文件级 RAG，再向量数据库
5. 先 FastAPI，再考虑复杂前端
6. 先流程复杂，再引入 LangGraph
7. 先单用户跑通，再做多用户泛化
8. 先 GitHub 可读，再追求架构高级
9. 先简历可投递，再追求产品成熟

---

## 11. 当前下一步建议

当前阶段最应该执行的是：

```text
阶段 0：当前版本收口 · 简历可投递切片
```

具体优先级：

1. 修正 README / PROJECT_STATUS / GitHub 文件状态漂移
2. 固定一条端到端 Demo 链
3. 把 Agent Demo 写进用户项目经历
4. 补最小演示截图或输入输出案例
5. 再进入最小文件级 RAG

不要现在直接进入：

- FastAPI
- LangGraph
- 多用户系统
- 复杂前端
- 自动投递
- 大规模招聘数据抓取

---

## 12. 一句话总路线

OfferClaw 后续路线不是立刻堆 RAG、FastAPI、LangGraph，而是：

> 先把当前 V1 收成一个能投简历的完整 Agent 项目；  
> 再补最小文件级 RAG，证明它能基于长期状态工作；  
> 再用 FastAPI 做服务化；  
> 最后在流程复杂后用 LangGraph 重构工作流，并扩展到多用户泛化。
