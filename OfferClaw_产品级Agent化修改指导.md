# OfferClaw 产品级 Agent 化修改指导文件

> 版本：V1.0  
> 目标：将 OfferClaw 从“功能模块较完整的 AI Agent 项目”进一步推进为“状态真实、流程清晰、可交互、可展示、可用于实习投递材料的产品级智能求职 Agent”。  
> 适用对象：项目开发者本人、Claude 协作开发、后续 README / 简历 / 面试材料整理。  
> 当前项目地址：https://github.com/zhangyi-nb1/offerclaw/tree/main  

---

## 0. 当前核心判断

OfferClaw 当前已经具备比较完整的 V2 功能主体，不再是早期原型。它已经有：

- 用户画像
- JD 匹配
- 缺口分析
- 学习规划
- 每日执行
- 周期复盘
- Agent Demo
- RAG
- LangGraph
- FastAPI
- 本地 `/ui`
- JD 半自动抽取
- 简历项目段生成
- applications 投递追踪
- DATA_CONTRACT
- doctor / verify_pipeline / pytest / verification_report

因此，下一步不应该继续盲目增加新技术栈，而应该围绕：

```text
状态真实化
→ 流程编排化
→ UI 产品化
→ 投递闭环化
→ 简历生成完整化
→ 演示与验证收口
```

把 OfferClaw 从“多个功能模块的集合”升级为一个真正可用的产品级智能求职 Agent。

---

## 1. 最终产品级目标

OfferClaw 产品级目标不是“做一个更复杂的 RAG Chatbot”，而是：

> 一个本地运行、围绕求职者长期成长和真实投递过程运行的 Career Operating Agent。

最终用户每天打开系统后，应该能看到：

```text
1. 我当前目标岗位是什么
2. 我距离目标岗位还差什么
3. 今天最该做什么
4. 为什么今天做这件事
5. 这个任务对应哪个岗位缺口
6. 做完以后更新到哪里
7. 当前哪些岗位值得投
8. 我的简历草稿是否已经足够投递
```

最终核心闭环应为：

```text
用户画像
→ JD 发现 / 导入
→ 岗位匹配
→ 缺口分析
→ 计划生成
→ 今日任务
→ 每日执行
→ 周期复盘
→ 简历草稿
→ 投递状态更新
→ 画像与计划再更新
```

---

## 2. 当前最关键的问题

---

### 2.1 问题一：状态驱动不彻底

当前系统已经有 `user_profile.md`、`applications.md`、`daily_log.md` 等状态文件，但部分接口或模块仍可能依赖演示用数据，例如 `DEMO_PROFILE`。

这会导致一个严重问题：

```text
用户在页面中更新画像后，后续 JD 匹配、计划生成、今日建议不一定真正基于最新用户状态。
```

产品级 Agent 的第一原则是：

```text
所有决策必须基于真实状态，而不是 demo 数据。
```

因此第一优先级是：

```text
取消 DEMO_PROFILE 在核心链路中的依赖。
```

---

### 2.2 问题二：Agent 主动性还不够强

当前系统已经有 `career_agent.py` 和 `/api/today`，但它仍更像“今日建议函数”，还不是完整求职 Agent Orchestrator。

产品级 Agent 不应该只是被动回答用户问题，而应该：

```text
读取当前画像
检查 applications
检查 daily_log
分析当前最大阻塞
判断今日最优任务
给出理由
等待用户确认
写入 daily_log 或 applications
```

目前还缺一个完整的 CareerFlow 主流程。

---

### 2.3 问题三：UI 仍偏功能卡片集合

当前 `/ui` 已有用户画像、JD 分析、计划、每日执行、简历草稿等卡片，但整体体验仍更像“功能面板”。

产品级 UI 应是一个有明确工作流的求职控制台：

```text
Step 1：完善画像
Step 2：导入 / 发现 JD
Step 3：匹配岗位
Step 4：分析缺口
Step 5：生成计划
Step 6：执行今日任务
Step 7：生成简历草稿
Step 8：更新投递状态
```

当前 UI 需要从“模块展示”升级为“流程驱动”。

---

### 2.4 问题四：JD Discovery 仍是半自动抽取

当前 `job_discovery.py` 已支持粘贴 JD 或 URL 抽取，但还不是完整推荐系统。

产品级目标应逐步升级为：

```text
根据用户画像生成搜索 query
→ 抽取公开 JD
→ 去重
→ 匹配排序
→ 推荐写入 applications
```

但要注意边界：

```text
不自动登录招聘网站
不绕过平台规则
不自动投递
不做高风险大规模爬虫
```

---

### 2.5 问题五：简历生成仍偏项目段生成

当前 `resume_builder.py` 更像是“JD 定制项目段生成器”，还不是完整简历生成器。

产品级目标应分阶段升级：

```text
项目段生成
→ 技能栏生成
→ 项目经历生成
→ 竞赛 / 科研经历整理
→ Markdown 简历草稿
→ 可选 PDF / Word 导出
```

当前不要求一步完成 PDF，但至少应支持 Markdown 简历草稿。

---

### 2.6 问题六：RAG 已有技术链路，但应用场景仍需扩展

当前 RAG 已能基于项目文档回答问题，但产品级求职 Agent 的 RAG 应覆盖：

```text
profile
jd
application
daily_log
weekly_summary
resume
story
learning_note
project_doc
```

RAG 不应只回答“项目是什么”，还应该回答：

```text
我最近投递了什么？
我这周做了什么？
哪个 JD 最值得投？
哪个面试故事适合当前岗位？
我的简历应该突出什么？
```

---

### 2.7 问题七：简历展示与面试叙事需要压缩

项目功能很多，但面试时不能平铺所有文件和接口。

需要压成三条主线：

```text
1. 状态驱动型求职 Agent
2. RAG + LangGraph 的 grounded answer
3. FastAPI + 本地 UI 的产品化展示
```

所有后续优化都应围绕这三条主线服务。

---

## 3. 产品级 Agent 化总体设计

---

## 3.1 产品架构

建议 OfferClaw 产品级架构分为四层：

```text
前端控制台
→ FastAPI 服务层
→ CareerFlow Agent 编排层
→ 状态 / RAG / 工具层
```

### 第一层：前端控制台

目标：

```text
用户打开一个页面，就能完成主要求职流程。
```

页面应包含：

- 今日建议
- 当前目标岗位
- 当前最大阻塞
- 用户画像
- JD 导入 / 发现
- 匹配结果
- 缺口清单
- 计划生成
- 每日执行
- 简历草稿
- applications 状态

---

### 第二层：FastAPI 服务层

建议 API 按功能分组：

```text
Profile API
GET  /api/profile
POST /api/profile/update-draft

Job API
POST /api/discover
POST /api/match
POST /api/jobs/rank

Plan API
POST /api/plan
GET  /api/today
POST /api/daily

Resume API
GET  /api/resume
POST /api/resume/build
POST /api/resume/draft

RAG API
POST /api/query
POST /api/search
POST /api/stream

Application API
GET  /api/applications
POST /api/applications/add
POST /api/applications/update-status
```

优先补强：

```text
/api/profile
/api/match
/api/today
/api/resume/build
/api/applications
```

---

### 第三层：CareerFlow Agent 编排层

建议新增或升级：

```text
career_flow.py
```

核心流程：

```text
profile_node
→ job_import_or_discovery_node
→ job_match_node
→ gap_analysis_node
→ plan_node
→ daily_action_node
→ resume_draft_node
→ application_update_node
→ weekly_review_node
→ memory_update_node
```

每个节点负责一件事：

| 节点 | 作用 |
|---|---|
| profile_node | 读取并检查用户画像 |
| job_import_or_discovery_node | 导入或发现 JD |
| job_match_node | 调用岗位匹配 |
| gap_analysis_node | 生成技能 / 项目 / 经历缺口 |
| plan_node | 调用规划模块 |
| daily_action_node | 生成今日任务 |
| resume_draft_node | 生成简历草稿 |
| application_update_node | 更新投递状态 |
| weekly_review_node | 做周度复盘 |
| memory_update_node | 更新长期状态 |

---

### 第四层：状态 / RAG / 工具层

状态文件：

```text
user_profile.md
applications.md
daily_log.md
interview_story_bank.md
resume_draft.md
PROJECT_STATUS.md
```

RAG 知识源：

```text
profile
jd
application
daily_log
story
resume
project_doc
learning_note
```

工具：

```text
profile_lookup
job_discovery
match_job
gap_to_plan
today_task
resume_builder
rag_search
application_update
```

写入策略：

```text
分析可以自动
建议可以自动
写入需确认
投递必须人工
```

---

## 4. 第一阶段：状态真实化

这是当前最优先阶段。

---

## 4.1 阶段目标

确保 OfferClaw 的核心判断全部基于真实用户状态，而不是 demo 数据。

---

## 4.2 必做任务

### 任务 1：新增 `profile_loader.py`

作用：

```text
从 user_profile.md 或 profiles/*.json 中解析出程序可用的 profile dict。
```

至少解析字段：

```text
学历
专业
所在地
可接受地域
方向优先级
明确不做
工作性质偏好
期望薪资
熟练技能
会用技能
项目数量
实习数量
英语自评
```

第一版不做复杂 Markdown parser，只做稳定规则提取。

---

### 任务 2：修改 `/api/match`

要求：

```text
/api/match 不再使用 DEMO_PROFILE。
必须改用 profile_loader.load_profile()。
```

保持响应结构不变，避免破坏前端和测试。

---

### 任务 3：检查 `/api/today`

要求：

```text
/api/today 必须读取真实 applications.md、daily_log.md、user_profile.md。
```

它输出的今日建议必须能解释来源：

```text
基于最近投递状态
基于最近执行记录
基于当前目标岗位
基于当前缺口
```

---

### 任务 4：补测试

新增或修改测试：

```text
test_profile_loader.py
test_api_match_uses_real_profile.py
test_today_advice_reads_state.py
```

测试目标：

1. `load_profile()` 返回必要字段
2. `/api/match` 不再使用 `DEMO_PROFILE`
3. `/api/today` 能读取真实状态并输出建议

---

## 4.3 验收标准

状态真实化完成后，应满足：

```text
1. 页面修改 user_profile 后，匹配结果会变化
2. /api/match 不依赖 DEMO_PROFILE
3. /api/today 的建议能追溯到 applications 或 daily_log
4. 测试能证明上述行为
```

---

## 5. 第二阶段：CareerFlow 编排化

---

## 5.1 阶段目标

把多个分散模块组织成一个真正的求职 Agent 主流程。

---

## 5.2 新增文件

```text
career_flow.py
```

---

## 5.3 建议核心状态结构

```python
CareerState = {
    "profile": {},
    "target_role": "",
    "jd": {},
    "match_report": {},
    "gaps": {},
    "plan": {},
    "today_task": {},
    "resume_draft": {},
    "application_update": {},
    "requires_confirmation": []
}
```

---

## 5.4 建议流程

```text
load_profile
→ import_or_discover_jd
→ match_job
→ analyze_gaps
→ generate_plan
→ generate_today_task
→ build_resume_draft
→ suggest_application_update
```

---

## 5.5 写入规则

任何写入动作都不应直接执行，必须输出：

```text
confirm_required = true
target_file = xxx
suggested_patch = xxx
reason = xxx
```

用户确认后再写入。

---

## 5.6 验收标准

CareerFlow 完成后，应能运行：

```text
输入一份 JD
→ 系统读取真实 profile
→ 输出匹配报告
→ 输出缺口清单
→ 输出计划
→ 输出今日任务
→ 输出简历草稿
→ 输出是否建议写入 applications
```

---

## 6. 第三阶段：UI 产品化

---

## 6.1 阶段目标

让 `/ui` 从功能卡片集合升级为本地求职控制台。

---

## 6.2 页面结构

建议页面分为：

```text
顶部：今日建议 + 当前目标岗位 + 当前最大阻塞
左侧：用户画像摘要 + applications 状态
中间：求职流程 Stepper
右侧：RAG 问答 + 面试故事推荐
```

---

## 6.3 Stepper 流程

```text
Step 1：完善画像
Step 2：导入 / 发现 JD
Step 3：匹配岗位
Step 4：分析缺口
Step 5：生成计划
Step 6：今日执行
Step 7：生成简历草稿
Step 8：更新投递状态
```

---

## 6.4 第一版技术路线

继续使用：

```text
FastAPI + static/index.html + Vanilla JS
```

暂不引入：

```text
React
Vue
登录系统
数据库
复杂前端状态管理
```

---

## 6.5 验收标准

打开 `/ui` 后，应能完成：

```text
查看画像
导入 JD
匹配 JD
查看缺口
生成计划
生成今日任务
生成简历草稿
查看 applications 状态
```

---

## 7. 第四阶段：JD Discovery 增强

---

## 7.1 阶段目标

从“JD 抽取器”升级为“半自动 JD 发现与推荐模块”。

---

## 7.2 分层设计

### query_builder

根据用户画像生成搜索关键词：

```text
AI 应用开发 实习 上海 Python Agent RAG
大模型应用开发 实习 南京 FastAPI Agent
```

### jd_fetcher

支持：

```text
用户提供官方招聘页 URL
公开页面抽取
Playwright 回退
```

### jd_ranker

调用现有匹配模块：

```text
候选 JD
→ match_job
→ 排序
→ 推荐理由
→ 是否写入 applications
```

---

## 7.3 边界

不做：

```text
自动登录
自动投递
批量爬虫
绕过平台规则
```

---

## 7.4 验收标准

用户输入目标城市和方向后，系统能输出：

```text
推荐搜索关键词
候选 JD 列表
匹配排序
推荐理由
下一步动作
```

---

## 8. 第五阶段：Resume Builder 完整化

---

## 8.1 阶段目标

从“项目段生成”升级为“Markdown 简历草稿生成”。

---

## 8.2 建议新增能力

```text
build_skill_section()
build_project_section()
build_competition_section()
build_research_section()
build_summary_section()
build_resume_markdown()
```

---

## 8.3 输入

```text
user_profile.md
interview_story_bank.md
PROJECT_STATUS.md
applications.md
target JD
```

---

## 8.4 输出

```text
技能栏
项目经历
竞赛经历
科研经历
求职摘要
JD 定制项目描述
```

---

## 8.5 边界

不做：

```text
伪造经历
夸大结果
自动承诺指标
自动投递
```

---

## 8.6 验收标准

输入一个 JD 后，系统能生成：

```text
一份 Markdown 简历草稿
一个 JD 定制项目段
一个可复制到简历中的技能栏
```

---

## 9. 第六阶段：RAG 知识域扩展

---

## 9.1 阶段目标

让 RAG 真正服务求职执行，而不只是回答项目文档问题。

---

## 9.2 应纳入的知识源

```text
applications.md
daily_log.md
interview_story_bank.md
docs/resume_pitch.md
docs/project_one_pager.md
docs/verification_report.md
learning_notes/
```

---

## 9.3 source_type 设计

```text
profile
jd
application
log
story
resume
project_doc
learning_note
verification
```

---

## 9.4 目标问题

RAG 应能回答：

```text
我最近投递了什么？
我这周做了什么？
我最适合哪份 JD？
哪个故事适合某次面试？
简历应该突出什么？
项目当前真实进度如何？
```

---

## 9.5 验收标准

至少支持 20 个跨文档问题，并能返回来源文件。

---

## 10. 第七阶段：真实使用与投递验证

---

## 10.1 阶段目标

让 OfferClaw 不只在 demo 中运行，而是真的服务用户求职。

---

## 10.2 必须积累的数据

```text
applications 至少 5 条岗位
daily_log 至少 7 天记录
interview_story_bank 至少 5 条故事
resume_draft 至少 1 版
实际投递至少 1 次
```

---

## 10.3 验收标准

系统能回答：

```text
过去一周我做了什么？
哪一个岗位现在最值得投？
我今天最该做什么？
我的简历现在还缺哪一段？
```

---

## 11. 简历呈现建议

最终简历项目名称：

```text
OfferClaw：基于 FastAPI + LangGraph + RAG 的求职执行型 AI Agent
```

简历核心描述：

```text
基于 Python、FastAPI、LangGraph、ChromaDB 与智谱 GLM API 构建本地运行的求职执行 Agent，支持用户画像构建、JD 半自动抽取、岗位匹配、能力缺口识别、4 周规划、每日任务、RAG 问答和 JD 定制简历段生成。系统采用 Markdown 状态文件管理长期上下文，通过规则引擎 + LLM 双通路实现可解释匹配，并封装 FastAPI 接口、SSE 流式响应、本地控制台和 doctor / verify_pipeline / pytest 工程验证。
```

面试主线：

```text
1. Agent 主线：career_agent / career_flow / /api/today / 工具调用
2. RAG 主线：embedding-3 / ChromaDB / LangGraph / eval_rag
3. 工程主线：FastAPI / SSE / UI / tests / doctor / verification_report
```

---

## 12. 当前第一步执行指令

下一步只做：

```text
状态真实化
```

不要同时做 UI、JD discovery、resume builder。

第一步任务：

```text
新增 profile_loader.py
修改 /api/match
确保 /api/match 使用真实 user_profile.md
补测试
```

---

## 13. 给 Claude 的执行指令

```text
你现在基于当前 OfferClaw 仓库继续推进产品级智能 Agent 化。

仓库：
https://github.com/zhangyi-nb1/offerclaw/tree/main

当前判断：
1. OfferClaw 已经有完整 V2 功能主体。
2. 现在不继续扩新技术。
3. 当前最关键的问题是：状态驱动不彻底，/api/match 仍可能使用 DEMO_PROFILE，CareerFlow 还没有形成完整求职主流程。
4. 本轮只做“状态真实化”，不要改 UI，不要新增 JD 搜索，不要改 RAG。

请执行以下任务：

一、检查 rag_api.py
重点检查：
- /api/profile 是否读取 user_profile.md
- /api/match 是否仍使用 DEMO_PROFILE
- /api/today 是否读取 applications / daily_log / profile
- /api/plan 是否接收真实 gap_list
- /api/resume/build 是否读取真实 profile 和 story bank

二、设计 profile_loader.py
要求：
- 从 user_profile.md 解析出 match_job 所需 profile dict
- 至少包含：
  学历
  专业
  所在地
  可接受地域
  方向优先级
  明确不做
  工作性质偏好
  期望薪资
  熟练技能
  会用技能
  项目数量
  实习数量
  英语自评
- 不做复杂 parser，先做稳定规则提取

三、修改 /api/match
要求：
- 不再使用 DEMO_PROFILE
- 改用 profile_loader.load_profile()
- 保持原响应结构不变

四、增加测试
新增或修改 tests：
- 测试 load_profile 返回必要字段
- 测试 /api/match 不再调用 DEMO_PROFILE
- 测试一个 JD 能基于真实 profile 返回三档结论

五、输出
- 修改方案
- 涉及文件
- 完整代码
- 本地验证命令
- 可能风险
```

---

## 14. 总结

OfferClaw 现在已经足够吸引面试官，但要成为产品级智能 Agent，关键不是继续堆技术，而是：

```text
状态真实化
流程编排化
UI 产品化
投递闭环化
简历生成完整化
```

当前第一步必须是：

```text
取消 DEMO_PROFILE 依赖，让所有核心判断基于真实用户状态。
```

这一步完成后，OfferClaw 的智能感、可信度和简历说服力都会明显提升。
