# OfferClaw 下一步项目优化实验规划报告

> 版本：V1.0  
> 用途：指导 OfferClaw 从“技术功能较完整的 AI Agent 项目”进一步优化为“可用于简历、投递、面试展示的主项目”。  
> 适用阶段：当前 OfferClaw 已具备 Agent、RAG、FastAPI、LangGraph、岗位匹配、规划与复盘等核心雏形后。  
> 核心目标：不再盲目扩功能，而是补齐求职运营闭环、数据契约、投递追踪、面试故事沉淀和工程可信度，让项目更适合放入简历与实习投递材料。

---

## 1. 当前项目定位与优化方向

### 1.1 项目当前定位

OfferClaw 当前应被定位为：

> 一个面向求职者的长期执行型 AI Agent 系统，围绕用户画像、岗位匹配、缺口识别、学习规划、执行复盘和动态更新形成闭环。

它不是普通聊天机器人，也不是一次性简历生成器，而是一个持续帮助求职者成长和投递的 Agent 项目。

当前已经具备的关键能力包括：

1. 用户画像构建  
2. 岗位匹配分析  
3. 缺口识别  
4. 学习与求职计划生成  
5. Agent 工具调用  
6. 文件级 RAG  
7. LangGraph 工作流雏形  
8. FastAPI 接口层  
9. JVS Claw 部署文档  
10. GitHub 项目展示基础  

### 1.2 当前优化总原则

接下来不建议继续大幅扩展新技术栈，而应优先做“求职展示收口”。

当前优化原则是：

```text
技术功能冻结
→ 求职运营闭环补齐
→ 数据边界明确
→ 投递记录可追踪
→ 面试故事可复用
→ 工程健康可检查
→ README / 简历 / 演示链统一
```

核心判断：

> 当前 OfferClaw 技术栈已经足够支撑简历主项目，下一步最重要的是把项目做成一个“可信、可讲、可演示、可用于投递”的求职工程系统。

---

## 2. 对 Career-Ops 的借鉴边界

### 2.1 Career-Ops 值得借鉴的核心思想

Career-Ops 的价值不在于某一个模型或某一个技术，而在于它把求职过程做成了一个可持续运行的运营系统。

OfferClaw 可以借鉴的内容包括：

1. 数据契约  
2. 投递 Tracker  
3. 面试故事库  
4. 项目 One-pager  
5. 复盘与反思文档  
6. 工程健康检查脚本  
7. Pipeline 验证脚本  
8. 伦理使用边界  

这些内容都能增强 OfferClaw 的求职实用性和工程可信度。

### 2.2 不建议照搬的内容

当前不建议照搬 Career-Ops 中偏自动化运营和批量投递的部分，包括：

1. 自动扫描招聘网站  
2. 批量抓取 Greenhouse / Lever / Ashby 等平台  
3. 自动生成 ATS PDF  
4. 自动填写申请表  
5. 批量投递或半自动海投  
6. Go TUI Dashboard  
7. 大规模门户扫描脚本  
8. 复杂薪资谈判流程  

原因：

1. 这些功能与当前 AI Agent / RAG / FastAPI / LangGraph 主线不完全一致。  
2. 它们会增加维护成本。  
3. 容易让项目从“求职执行 Agent”偏移成“招聘网站自动化工具”。  
4. 对当前投递 AI 应用 / Agent 实习岗的简历价值不如现有主线。  

OfferClaw 的优化边界应是：

```text
吸收 Career-Ops 的“求职运营结构”
不照搬 Career-Ops 的“批量自动化投递系统”
```

---

## 3. 当前距离“完美满足最初需求”的关键差距

最初需求是：

> 用 OfferClaw 作为 AI 应用 / Agent 实习投递的主项目，弥补无计算机实习和工程项目不足的问题，在简历、GitHub 和面试中证明具备 AI Agent 工程能力。

从这个标准看，当前主要差距不是技术栈不足，而是以下 6 点。

### 3.1 差距一：缺少明确的数据契约

当前项目中已有多个状态文件和系统文件，例如：

- `user_profile.md`
- `daily_log.md`
- `PROJECT_STATUS.md`
- `jd_candidates.md`
- `README.md`
- `rag_*.py`
- `*_prompt.md`

但还缺少一个正式文档说明：

1. 哪些是用户状态文件  
2. 哪些是系统规则文件  
3. 哪些文件允许自动更新  
4. 哪些文件必须用户确认后再写入  
5. 哪些文件应进入 GitHub  
6. 哪些文件应被 `.gitignore` 忽略  

这会影响项目的长期状态可信度。

### 3.2 差距二：投递过程还没有形成 Tracker

当前 `jd_candidates.md` 更多是测试 JD 池，用来验证岗位匹配能力，但它还不是“真实投递追踪系统”。

OfferClaw 若要成为求职执行 Agent，需要区分：

```text
JD 候选池：用于测试和横向对比
投递 Tracker：用于记录真实求职进展
```

缺少投递 Tracker 会导致项目仍停留在“分析岗位”，而不是“推动投递”。

### 3.3 差距三：面试故事没有沉淀

当前项目已经有很多可讲内容，例如：

1. 从 Prompt 文件演进到 Python 规则匹配  
2. 从 API 调用演进到 Agent 工具调用  
3. 从规则检索演进到 RAG  
4. 从普通流程演进到 LangGraph  
5. 从本地脚本演进到 FastAPI 接口  

但这些还没有沉淀为面试可复用的 STAR 故事。

如果没有故事库，面试时容易出现：

1. 能说技术名词，但说不清为什么做  
2. 能说功能，但说不清技术难点  
3. 能说结果，但说不清取舍和反思  

### 3.4 差距四：项目缺少 One-pager

当前 README 已经能介绍项目，但 README 面向完整浏览；简历和面试前更需要一页式概览。

One-pager 用于快速回答：

1. 项目解决什么问题  
2. 目标用户是谁  
3. 系统架构是什么  
4. 核心技术是什么  
5. 当前效果如何  
6. 难点和取舍是什么  
7. 后续如何演进  

这能显著提高项目展示效率。

### 3.5 差距五：工程健康检查不足

当前项目已有测试和运行脚本，但还缺少一个统一的健康检查入口。

理想状态下，克隆项目后可以快速运行：

```bash
python doctor.py
```

然后看到：

1. Python 版本是否合适  
2. 依赖是否安装  
3. API Key 是否存在  
4. RAG 索引是否存在  
5. 核心文件是否存在  
6. 测试是否可跑  
7. FastAPI 是否可启动  

这能体现项目的工程成熟度。

### 3.6 差距六：Pipeline 验证还不够集中

当前各模块可能能单独跑，但需要一个脚本验证核心链路：

```text
profile
→ match
→ plan
→ summary
→ rag
→ api
```

如果没有 pipeline 验证脚本，项目容易出现：

1. 单个模块可运行，但整体链路断裂  
2. README 写已完成，但实际运行无法复现  
3. 修改某个文件后不知道是否破坏主链路  

因此需要 `verify_pipeline.py`。

---

## 4. 建议借鉴的 8 个设计

## 4.1 设计一：新增 `DATA_CONTRACT.md`

### 作用

定义 OfferClaw 中“用户数据层”和“系统逻辑层”的边界。

### 为什么现在需要

OfferClaw 的核心价值之一是长期状态。长期状态必须有明确边界，否则会让项目显得像多个 Markdown 文件堆叠，而不是一个可维护系统。

### 建议内容

```text
User Layer:
- user_profile.md
- daily_log.md
- applications.md
- interview_story_bank.md
- plans/
- summaries/
- memory.json

System Layer:
- SOUL.md
- target_rules.md
- source_policy.md
- onboarding_prompt.md
- job_match_prompt.md
- plan_prompt.md
- summary_prompt.md
- match_job.py
- plan_gen.py
- rag_*.py
- tests/
- docs/

Rules:
- 用户层文件不得被无确认自动覆盖
- 系统层文件可版本化更新
- 涉及用户画像、投递状态、计划调整的写入必须可追溯
- 敏感信息不得进入 GitHub
```

### 对简历价值

体现：

1. 状态管理意识  
2. 系统边界设计能力  
3. 长期运行 Agent 的工程思维  

### 优先级

最高优先级。建议第一个做。

---

## 4.2 设计二：新增 `applications.md`

### 作用

记录真实求职投递 Pipeline。

### 为什么现在需要

当前 `jd_candidates.md` 是测试池，不是真实投递池。OfferClaw 如果要作为求职执行系统，必须有投递状态追踪。

### 建议字段

```markdown
| 日期 | 公司 | 岗位 | 来源 | 地点 | 匹配结论 | 样本定位 | 当前状态 | 下一步动作 | 备注 |
|---|---|---|---|---|---|---|---|---|---|
```

### 推荐状态枚举

```text
已评估
准备投递
已投递
等待反馈
面试中
已拒绝
主动放弃
不投递
```

### 与 `jd_candidates.md` 的区别

```text
jd_candidates.md：后台测试池，用于回归测试和横向对比
applications.md：前台投递池，用于真实投递状态追踪
```

### 对简历价值

体现：

1. 求职流程运营能力  
2. Agent 不只是分析，还能推动执行  
3. 项目真实服务实习投递目标  

---

## 4.3 设计三：新增 `interview_story_bank.md`

### 作用

沉淀面试可讲的项目故事。

### 为什么现在需要

项目已经有一定复杂度，但面试时不能只讲功能清单。需要能讲清楚：

1. 为什么做这个项目  
2. 遇到什么问题  
3. 如何解决  
4. 最终效果如何  
5. 有什么反思  

### 建议结构

每条故事采用 STAR+R：

```markdown
## Story 1：从 Prompt 原型到规则代码版匹配

### Situation
背景是什么？

### Task
当时要解决什么问题？

### Action
做了哪些设计和实现？

### Result
最后达到了什么结果？

### Reflection
从中学到了什么？如果重做会怎么优化？
```

### 首批建议故事

1. 为什么做 OfferClaw  
2. 从 Prompt 契约到 `match_job.py` 规则版  
3. 从 LLM API 到 Agent 工具调用  
4. 从普通问答到 RAG 检索增强  
5. 从流程脚本到 LangGraph 工作流  
6. 从本地脚本到 FastAPI 服务化  

### 对简历价值

直接服务面试，尤其适合回答：

1. 项目中最难的部分是什么？  
2. 为什么这样设计？  
3. 如何评估项目效果？  
4. 如何处理失败和边界？  

---

## 4.4 设计四：新增 `docs/project_one_pager.md`

### 作用

用一页纸解释整个项目。

### 为什么现在需要

README 适合完整浏览，但面试和投递材料需要快速理解。One-pager 用于让面试官或自己在 1-2 分钟内理解项目价值。

### 建议结构

```markdown
# OfferClaw Project One-pager

## 1. 项目一句话
## 2. 目标用户
## 3. 解决的问题
## 4. 系统架构
## 5. 核心模块
## 6. 技术栈
## 7. 当前指标
## 8. Demo 链路
## 9. 关键技术难点
## 10. 当前不足与下一步
```

### 对简历价值

体现：

1. 项目表达能力  
2. 架构概括能力  
3. 面试展示能力  

---

## 4.5 设计五：新增 `docs/postmortem.md`

### 作用

总结项目的技术复盘和关键取舍。

### 为什么现在需要

一个成熟项目不只展示“做成了什么”，还要展示“为什么这么做、踩过什么坑、如何修正”。

### 建议内容

1. 为什么先做规则版匹配，而不是端到端 LLM  
2. 为什么先做最小 Agent，再引入 RAG  
3. 为什么 RAG 先做文件级而不是复杂知识库  
4. 为什么 FastAPI 放在服务化阶段  
5. 为什么 LangGraph 后引入  
6. RAG 评估有哪些不足  
7. 当前系统还不能解决什么问题  

### 对简历价值

体现：

1. 工程反思能力  
2. 技术取舍能力  
3. 不是只会堆功能  

---

## 4.6 设计六：新增 `doctor.py`

### 作用

提供项目环境与核心依赖的一键健康检查。

### 为什么现在需要

GitHub 项目如果别人无法快速判断能否运行，会降低可信度。`doctor.py` 可以快速告诉用户项目是否准备好运行。

### 建议检查项

1. Python 版本  
2. `requirements.txt` 是否安装  
3. `.env.local` 是否存在  
4. `ZHIPU_API_KEY` 是否存在  
5. 核心文件是否存在  
6. ChromaDB 索引目录是否存在  
7. RAG 基础查询是否可用  
8. pytest 是否可运行  

### 建议输出

```text
[OK] Python 3.10+
[OK] requirements installed
[OK] ZHIPU_API_KEY found
[OK] core markdown files found
[WARN] chroma_db not found, please run rag_ingest.py
[OK] tests passed: 17/18
```

### 对简历价值

体现：

1. 工程可复现意识  
2. 开发者体验意识  
3. 项目不是只能在自己电脑上跑  

---

## 4.7 设计七：新增 `verify_pipeline.py`

### 作用

验证 OfferClaw 的核心链路是否能端到端跑通。

### 为什么现在需要

当前模块较多，单模块成功不代表整体链路稳定。需要一个脚本验证核心流程。

### 建议验证链路

```text
读取 user_profile
→ 匹配一份 JD
→ 生成缺口清单
→ 生成计划
→ 生成复盘建议
→ RAG 查询项目状态
```

### 最小验证目标

1. `match_job.py` 能运行  
2. `plan_gen.py` 能运行  
3. `summary_tool.py` 能运行  
4. `rag_graph.py` 能返回结果  
5. FastAPI `/health` 能访问  

### 对简历价值

体现：

1. 自动化验证意识  
2. 端到端工程能力  
3. 多模块集成能力  

---

## 4.8 设计八：新增 `docs/ethical_use.md`

### 作用

明确 OfferClaw 的使用边界和合规原则。

### 为什么现在需要

求职工具涉及简历、岗位、投递和用户画像，必须明确不做高风险行为。

### 建议内容

```text
不自动投递
不伪造经历
不承诺录用概率
不绕过招聘平台规则
不把低可信来源当事实
不批量骚扰招聘方
用户最终确认所有投递材料
所有简历内容必须可验证
```

### 对简历价值

体现：

1. AI 应用安全意识  
2. 合规意识  
3. 对真实业务场景的边界判断能力  

---

## 5. 三阶段优化计划

## 阶段 A：简历可投递收口

### 时间建议

1-2 天。

### 阶段目标

让 OfferClaw 当前版本可以进入简历和投递材料。

### 核心任务

1. 修正 README、PROJECT_STATUS、GitHub 文件树之间的状态口径  
2. 完成 `docs/demo.md` 的真实输入输出样例  
3. 完成 `docs/resume_pitch.md` 最终版  
4. 完成 `docs/interview_qa.md` 10 题版  
5. 新增 `docs/project_one_pager.md`  

### 不做内容

1. 不继续扩 RAG  
2. 不继续加 FastAPI 接口  
3. 不继续改 LangGraph  
4. 不做自动投递  
5. 不做招聘网站爬虫  

### 完成标志

1. README 状态与仓库真实文件一致  
2. 项目有一条可讲清的 Demo 链  
3. 简历项目描述可直接使用  
4. 面试问答有基本准备  
5. One-pager 能单独解释项目  

---

## 阶段 B：求职运营闭环

### 时间建议

2-3 天。

### 阶段目标

把 OfferClaw 从“项目展示”升级为“真实求职执行工具”。

### 核心新增文件

1. `DATA_CONTRACT.md`  
2. `applications.md`  
3. `interview_story_bank.md`  
4. `docs/ethical_use.md`  

### 核心小修

1. 区分 `jd_candidates.md` 和 `applications.md`  
2. 修正 `rag_api.py` 中可能存在的用户信息硬编码  
3. 将 `docs/interview_qa.md` 与 `interview_story_bank.md` 对齐  
4. 让 `daily_log.md`、`applications.md`、`user_profile.md` 的职责边界更清晰  

### 完成标志

1. 有真实投递状态表  
2. 有面试故事库  
3. 有数据契约  
4. 有合规边界说明  
5. 项目不只是“会分析”，而是能支持真实投递推进  

---

## 阶段 C：工程可信度补强

### 时间建议

2-4 天。

### 阶段目标

让 OfferClaw 更像一个可复现、可检查、可持续维护的工程项目。

### 核心新增文件

1. `doctor.py`  
2. `verify_pipeline.py`  
3. `docs/postmortem.md`  
4. `tests/test_api.py`  
5. `tests/test_pipeline.py`  

### 核心任务

1. 一键检查环境  
2. 一键验证主链路  
3. 增加 API 测试  
4. 增加 pipeline 测试  
5. 写项目技术复盘  

### 完成标志

1. `python doctor.py` 能检查环境  
2. `python verify_pipeline.py` 能跑主链路  
3. 测试覆盖 API 和主流程  
4. 项目文档能解释技术取舍  
5. 面试时能清楚说明项目不足和后续规划  

---

## 6. 推荐执行优先级

当前最推荐的执行顺序是：

```text
1. DATA_CONTRACT.md
2. applications.md
3. docs/project_one_pager.md
4. interview_story_bank.md
5. docs/ethical_use.md
6. 修 rag_api.py 的 profile 硬编码
7. doctor.py
8. verify_pipeline.py
9. docs/postmortem.md
```

### 为什么这样排

1. `DATA_CONTRACT.md` 是所有状态文件的基础。  
2. `applications.md` 直接服务真实投递。  
3. `project_one_pager.md` 直接服务简历和面试展示。  
4. `interview_story_bank.md` 直接服务面试表达。  
5. `ethical_use.md` 提升项目可信度。  
6. `rag_api.py` 去硬编码提升泛化可信度。  
7. `doctor.py` 和 `verify_pipeline.py` 提升工程可信度。  
8. `postmortem.md` 最后沉淀技术复盘。  

---

## 7. 每个新增文件的验收标准

### 7.1 `DATA_CONTRACT.md`

- 明确 User Layer 和 System Layer  
- 明确哪些文件可自动写入  
- 明确哪些文件需要用户确认  
- 明确哪些文件不得提交 GitHub  
- 明确数据变更追踪方式  

### 7.2 `applications.md`

- 有表格模板  
- 有状态枚举  
- 能记录真实岗位  
- 能和 `jd_candidates.md` 明确区分  
- 能支持后续投递复盘  

### 7.3 `interview_story_bank.md`

- 至少 5 条 STAR+R 故事  
- 每条能对应一个面试问题  
- 每条能说明技术难点或项目取舍  
- 每条有 Result 和 Reflection  

### 7.4 `docs/project_one_pager.md`

- 1 页内讲清项目  
- 有问题、方案、架构、技术、指标、Demo、下一步  
- 能直接辅助面试讲解  

### 7.5 `docs/ethical_use.md`

- 明确不自动投递  
- 明确不伪造经历  
- 明确不承诺录用概率  
- 明确用户最终确认  
- 明确信息源可信度边界  

### 7.6 `doctor.py`

- 可本地运行  
- 检查环境变量  
- 检查核心文件  
- 检查依赖  
- 检查索引  
- 输出 OK / WARN / ERROR  

### 7.7 `verify_pipeline.py`

- 能顺序跑核心模块  
- 能定位失败环节  
- 输出清晰状态  
- 不依赖人工操作  
- 可作为 README 的复现命令  

### 7.8 `docs/postmortem.md`

- 总结至少 5 个技术取舍  
- 写出失败或不足  
- 写出后续优化  
- 能体现工程反思能力  

---

## 8. 简历与投递使用方式

### 8.1 简历中应强调

1. AI Agent 系统设计  
2. RAG 检索增强  
3. LangGraph 工作流  
4. FastAPI 服务化  
5. 规则 + LLM 双通路匹配  
6. 长期用户状态管理  
7. pytest / doctor / verify pipeline 工程化  

### 8.2 简历中不应夸大

1. 不要说是生产级商业系统  
2. 不要说已支持大规模用户  
3. 不要说自动投递  
4. 不要说能保证 Offer  
5. 不要把小规模评估包装成大规模 Benchmark  

### 8.3 面试中应讲清

1. 为什么做这个项目  
2. 为什么先规则后 LLM  
3. 为什么引入 RAG  
4. 为什么引入 LangGraph  
5. 为什么需要 FastAPI  
6. 如何评估 RAG  
7. 如何管理用户状态  
8. 当前项目有哪些不足  

---

## 9. 风险与控制

### 9.1 风险一：继续堆技术导致主线发散

控制方式：

```text
当前阶段不再扩新框架。
只做求职运营闭环和工程收口。
```

### 9.2 风险二：项目看起来像自用脚本

控制方式：

```text
新增 DATA_CONTRACT、doctor、verify_pipeline、project_one_pager。
```

### 9.3 风险三：投递价值不明显

控制方式：

```text
新增 applications.md 和 interview_story_bank.md。
```

### 9.4 风险四：文档与代码不一致

控制方式：

```text
定期更新 PROJECT_STATUS。
doctor.py 和 verify_pipeline.py 作为事实校验入口。
```

---

## 10. 下一步唯一推荐动作

当前第一步应执行：

```text
新增 DATA_CONTRACT.md
```

原因：

1. 它是后续 applications、story bank、daily log、memory 的基础。  
2. 它能立刻提升项目结构可信度。  
3. 它不需要复杂代码，成本低、收益高。  
4. 它能防止 OfferClaw 状态层继续混乱。  

完成 `DATA_CONTRACT.md` 后，第二步再做：

```text
applications.md
```

---

## 11. 给 Claude 的后续执行入口

后续可以直接把下面指令发给 Claude：

```text
你现在基于 OfferClaw 当前仓库状态，执行下一步项目优化。

本轮只做 DATA_CONTRACT.md，不写其他文件，不改代码。

要求：
1. 明确 User Layer 和 System Layer
2. 明确每类文件的职责
3. 明确哪些文件允许自动写入
4. 明确哪些文件必须用户确认
5. 明确哪些文件可以进入 GitHub
6. 明确哪些文件必须加入 .gitignore
7. 明确数据变更追踪原则
8. 结合 OfferClaw 当前已有文件命名

输出：
- DATA_CONTRACT.md 的完整内容
- 为什么这个文件是下一步第一优先级
- 完成后下一步应做什么
```

---

## 12. 总结

OfferClaw 当前已经具备进入简历的技术基础。接下来最关键的不是继续堆新功能，而是把它从“功能丰富的 AI Agent 项目”优化为“可用于真实求职投递的执行型系统”。

本报告建议从 Career-Ops 借鉴 8 个轻量设计：

1. `DATA_CONTRACT.md`  
2. `applications.md`  
3. `interview_story_bank.md`  
4. `docs/project_one_pager.md`  
5. `docs/postmortem.md`  
6. `doctor.py`  
7. `verify_pipeline.py`  
8. `docs/ethical_use.md`  

并按 3 个阶段推进：

```text
阶段 A：简历可投递收口
阶段 B：求职运营闭环
阶段 C：工程可信度补强
```

最终目标是：

> 让 OfferClaw 不只是一个能运行的 AI 项目，而是一个能证明你具备 AI Agent 工程能力、能支撑实习投递、能在面试中讲清楚技术取舍的主项目。
