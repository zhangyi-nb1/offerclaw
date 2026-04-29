# OfferClaw 对标 Career-Ops 的借鉴分析与优化方案

> 版本：V1.0  
> 项目：OfferClaw  
> 参考项目：Career-Ops  
> 作用：分析 Career-Ops 中值得 OfferClaw 学习的设计思想、技术组织方式与求职运营机制；同时明确哪些内容不适合学习，避免项目偏离“AI 应用 / Agent 工程求职主项目”的原始目标。  
> 当前 OfferClaw 地址：https://github.com/zhangyi-nb1/offerclaw  
> Career-Ops 地址：https://github.com/santifer/career-ops  

---

## 1. 总体判断

Career-Ops 是一个非常成熟的“求职运营系统”，它的优势不只是某个单点功能，而是把求职过程工程化、流程化、资产化。

它的核心能力包括：

- 岗位 URL / JD 输入
- 结构化岗位评估
- CV 匹配
- 定制简历 / PDF 生成
- 招聘门户扫描
- 批量处理
- 投递 tracker
- 面试故事库
- Pipeline integrity
- Human-in-the-loop 边界

但 Career-Ops 与 OfferClaw 的阶段和目标并不完全相同。

Career-Ops 更像：

```text
已有 CV 和已有经历候选人的 Job Search Operating System
```

OfferClaw 更应该定位为：

```text
非典型背景候选人的 Career Growth + Job Search Agent
```

也就是说：

- Career-Ops 重点在“已有材料如何高效投递”
- OfferClaw 重点在“经历不足的人如何通过项目、学习、复盘逐步变成可投递候选人”

因此，OfferClaw 应该学习 Career-Ops 的系统结构与求职运营设计，但不应照搬它的自动化投递、PDF 生成、Portal Scanner、Go Dashboard 等方向。

---

## 2. Career-Ops 值得学习的核心点

---

## 2.1 README 的叙事方式

### Career-Ops 的做法

Career-Ops 的 README 第一屏非常有叙事感：

```text
I spent months applying to jobs the hard way. So I engineered the system I wish I had.
Companies use AI to filter candidates. I just gave candidates AI to choose companies.
```

它不是先堆技术，而是先讲清楚：

1. 用户痛点是什么
2. 为什么需要这个系统
3. 系统如何帮助候选人反制低效求职流程
4. 这个项目是作者真实使用后的产物

### OfferClaw 该怎么转化

OfferClaw 也应该先讲“为什么做”，而不是先展示所有技术指标。

推荐叙事：

```text
我不是 CS 科班，也没有 AI 实习经历。
所以我做了 OfferClaw：
一个帮助非典型背景学生把求职准备变成可执行工程流程的 AI Agent。
```

README 第一屏应从当前的“指标密集型”改为“问题驱动型”。

### 推荐改法

README 开头建议结构：

```markdown
# OfferClaw

一个面向 AI / Agent 求职者的长期执行型求职 Agent。

我做这个项目的原因很简单：
作为非典型背景求职者，求职准备并不是“改一份简历就投”，而是要持续补项目、补技能、选岗位、做复盘。OfferClaw 把这个过程变成一个可运行系统。

它围绕：
画像 → 岗位匹配 → 缺口识别 → 计划生成 → 每日执行 → 复盘 → 简历材料更新
形成闭环。
```

---

## 2.2 产品化功能命名方式

### Career-Ops 的做法

Career-Ops 用很清楚的产品化模块描述功能：

- Auto-Pipeline
- 6-Block Evaluation
- Interview Story Bank
- ATS PDF Generation
- Portal Scanner
- Batch Processing
- Dashboard TUI
- Human-in-the-Loop
- Pipeline Integrity

这些名称不是文件名，而是用户能理解的功能名。

### OfferClaw 当前问题

OfferClaw 的功能目前仍容易被理解为代码文件堆叠：

- `rag_api.py`
- `career_agent.py`
- `plan_gen.py`
- `resume_builder.py`
- `job_discovery.py`

这些对开发者清楚，但对 HR / 面试官不一定直观。

### OfferClaw 应该转化成的功能命名

建议统一为：

| 产品能力名 | 对应文件 / 模块 |
|---|---|
| Career Profile Builder | `user_profile.md`, `/api/profile` |
| JD Match Engine | `match_job.py`, `/api/match` |
| Gap-to-Plan Generator | `plan_gen.py`, `/api/plan` |
| Daily Action Agent | `career_agent.py`, `/api/today` |
| Weekly Review Agent | `summary_tool.py`, `daily_log.md` |
| RAG Knowledge Assistant | `rag_tools.py`, `rag_graph.py`, `rag_api.py` |
| Job Discovery Assistant | `job_discovery.py` |
| Resume Draft Builder | `resume_builder.py` |
| Application Tracker | `applications.md` |
| Interview Story Bank | `interview_story_bank.md` |

### 价值

这样可以让 README、简历、面试表达更清楚：

```text
不是“我写了很多 py 文件”，而是“我实现了一个求职执行系统的 9 个能力模块”。
```

---

## 2.3 数据契约设计

### Career-Ops 的做法

Career-Ops 的 `DATA_CONTRACT.md` 明确区分：

- User Layer：用户个人数据、CV、profile、tracker、reports、output、JDs
- System Layer：系统 modes、脚本、dashboard、templates、docs
- 规则：User Layer 不能被系统更新流程自动修改或覆盖；System Layer 可安全更新

这个设计非常成熟。

### OfferClaw 已经做了什么

OfferClaw 已经有 `DATA_CONTRACT.md`，并且已经区分：

- User Layer
- System Layer
- Runtime / Secrets

这一步是正确的。

### 还需要进一步强化的点

OfferClaw 后续应继续强化：

1. 所有写入 `user_profile.md` 的行为必须有用户确认
2. `daily_log.md` 只能追加，不应回溯改写
3. `applications.md` 状态变更必须保留时间和原因
4. `resume_builder.py` 只能生成草稿，不直接覆盖正式简历
5. `memory.json`、`logs/`、`chroma_db/`、`.env.local` 不得进入 GitHub
6. 多 persona 测试数据必须和真实用户数据分离

### 可加入的改进

在 `DATA_CONTRACT.md` 中新增“写入策略表”：

| 文件 | 可读 | 可写 | 自动写 | 需确认 | 入 Git |
|---|---|---|---|---|---|
| user_profile.md | 是 | 是 | 否 | 是 | demo 可入 |
| daily_log.md | 是 | 是 | 可追加 | 是 | 脱敏可入 |
| applications.md | 是 | 是 | 可追加 | 是 | 模板 / 示例可入 |
| interview_story_bank.md | 是 | 是 | 否 | 是 | 可入 |
| memory.json | 是 | 是 | 是 | 否 | 不入 |
| chroma_db/ | 是 | 是 | 是 | 否 | 不入 |
| .env.local | 是 | 是 | 否 | 是 | 不入 |

---

## 2.4 投递 Tracker 设计

### Career-Ops 的做法

Career-Ops 把 `applications.md` / tracker 作为核心资产。每次评估、投递、状态变化都进入统一追踪系统，并有 dedup、normalize、merge、verify 等完整性脚本。

### OfferClaw 当前状态

OfferClaw 已经有 `applications.md`，并且已经区分：

- `jd_candidates.md`：测试池
- `applications.md`：真实投递池

这是对的。

### 还需要学习的点

OfferClaw 的 `applications.md` 需要从“有结构”推进到“真实使用”。

至少应支持：

| 字段 | 说明 |
|---|---|
| 日期 | 评估或投递时间 |
| 公司 | 公司名称 |
| 岗位 | 岗位名 |
| 来源 | 官方页 / 平台 / 用户粘贴 |
| 地点 | 城市 / 远程 |
| 匹配结论 | 当前适合 / 暂不建议 / 中长期 |
| 样本定位 | 立即投递 / 短期可投 / 能力上限 |
| 状态 | 已评估 / 准备投递 / 已投递 / 等待反馈等 |
| 下一步动作 | 修改简历 / 补项目 / 准备面试 |
| 备注 | 风险或补充说明 |

### 进一步优化

新增 applications 周复盘：

```text
本周新增岗位数
准备投递数
已投递数
不投递原因 Top 3
最常见缺口
下周投递优先方向
```

### 价值

这个模块能证明 OfferClaw 不只是分析 JD，而是能推进真实求职流程。

---

## 2.5 面试故事库

### Career-Ops 的做法

Career-Ops 会把 JD 要求映射到 STAR+R 故事，长期沉淀可复用的 Interview Story Bank。

这点非常适合 OfferClaw。

### OfferClaw 应该怎么转化

OfferClaw 的 `interview_story_bank.md` 应从“面试准备文档”升级成“项目故事资产库”。

建议至少沉淀 8 类故事：

1. 为什么做 OfferClaw
2. 从 Prompt 契约到规则代码匹配
3. 从 LLM API 到 Function Calling
4. 从工具调用到 Agent Orchestrator
5. 从普通 RAG 到 LangGraph RAG
6. 从模块功能到 FastAPI 服务化
7. 从本地脚本到 `/ui` 控制台
8. 从单用户样本到 persona 泛化

每个故事使用 STAR+R：

```markdown
## Story：从 Prompt 契约到规则版 JD 匹配

### Situation
当时只有 Prompt，匹配结果不稳定。

### Task
需要一个可解释、可回归的岗位匹配模块。

### Action
设计硬门槛、软维度、三档结论，写成 `match_job.py`。

### Result
支持 Prompt + 规则双通路，对真实 JD 做回归验证。

### Reflection
纯 LLM 适合解释，规则代码适合兜底关键判断。
```

### 价值

面试时最重要的不是“我做了哪些文件”，而是能讲清：

```text
为什么这样做
遇到什么问题
如何取舍
结果如何
还有什么不足
```

---

## 2.6 Pipeline Integrity

### Career-Ops 的做法

Career-Ops 非常重视 pipeline integrity，包括：

- doctor
- verify
- normalize
- dedup
- merge
- sync-check
- liveness
- scan

这些命令能保证求职流程不是文件堆叠，而是可维护 pipeline。

### OfferClaw 已经做了什么

OfferClaw 已有：

- `doctor.py`
- `verify_pipeline.py`
- `eval_rag.py`
- pytest
- `docs/verification_report.md`

这是正确方向。

### 还可以借鉴什么

建议增加：

1. `normalize_applications.py`
   - 统一 applications 状态
   - 检查非法状态
   - 检查缺失字段

2. `dedup_jds.py`
   - 对 jd_candidates 和 applications 去重
   - 以公司 + 岗位 + URL 做 hash

3. `verify_docs.py`
   - 检查 README / verification_report / project_one_pager 指标是否一致

4. `check_liveness.py`
   - 检查 applications 中岗位 URL 是否仍可访问
   - 只访问公开 URL，不登录

### 优先级

当前最值得做的是：

```text
verify_docs.py
normalize_applications.py
```

因为你当前最怕的是指标口径不一致和投递状态混乱。

---

## 2.7 Human-in-the-loop 边界

### Career-Ops 的做法

Career-Ops 明确强调：

```text
AI evaluates and recommends, you decide and act.
The system never submits an application.
```

这是非常重要的边界。

### OfferClaw 应该怎么转化

OfferClaw 的边界应明确写入 README 和 `docs/ethical_use.md`：

```text
OfferClaw 可以：
- 分析画像
- 匹配 JD
- 生成计划
- 生成简历草稿
- 推荐下一步动作
- 维护投递状态

OfferClaw 不做：
- 自动投递
- 伪造经历
- 承诺录用概率
- 自动登录招聘平台
- 绕过平台规则
- 替用户确认投递
```

### 价值

这能避免项目被理解成“自动海投工具”，也能体现 AI 安全和真实业务边界意识。

---

## 2.8 项目 One-pager 与 Demo Pack

### Career-Ops 的做法

Career-Ops 的 `modes/project.md` 中，项目评估维度包括：

- 目标岗位信号
- 独特性
- Demo-ability
- 指标潜力
- MVP 时间
- STAR 故事潜力

并要求每个通过的项目都形成：

- One-pager
- Demo
- Postmortem

### OfferClaw 应该怎么转化

OfferClaw 已经有：

- `docs/project_one_pager.md`
- `docs/demo_script.md`
- `docs/postmortem.md`

但应进一步对齐 Career-Ops 的项目评估标准。

建议在 `docs/project_one_pager.md` 中增加一个“Portfolio Signal”小节：

```markdown
## Portfolio Signal

| 维度 | OfferClaw 表现 |
|---|---|
| Target-role signal | 直接面向 AI Agent / RAG / FastAPI 岗位 |
| Uniqueness | 结合求职成长、投递 tracker、RAG 和 Agent |
| Demo-ability | 本地 /ui 可演示 |
| Metrics | RAG Recall@5、pytest、doctor、verify_pipeline |
| MVP time | 2-3 周形成完整 V2 |
| STAR potential | 具备多条项目故事 |
```

---

## 3. 不应该学习 Career-Ops 的地方

---

## 3.1 不应照搬自动门户扫描

Career-Ops 的 Portal Scanner 面向大量公司招聘页和 Greenhouse / Ashby / Lever 等系统，是其核心能力之一。

但 OfferClaw 当前不应照搬。

### 原因

1. 你的目标岗位是 AI 应用 / Agent / RAG 工程，不是招聘爬虫工程
2. 大规模抓取会增加维护成本
3. 国内招聘平台登录、反爬和合规风险更高
4. 自动扫描会稀释你的主线技术叙事
5. 当前 JD 半自动抽取已经足够支撑简历项目

### 正确做法

只做：

```text
用户提供 URL
→ 抽取公开页面
→ 结构化 JD
→ 调用匹配
```

后续再做：

```text
根据用户画像生成搜索关键词
```

但不做自动遍历和批量爬虫。

---

## 3.2 不应照搬 ATS PDF 自动生成

Career-Ops 有 ATS PDF Generation 和 PDF 脚本，这是它的亮点之一。

OfferClaw 当前不应优先做。

### 原因

1. 你当前简历目标是证明 AI Agent 工程能力
2. PDF 生成主要是求职文档自动化，不是核心 AI 技术
3. Word / PDF 排版很容易占用大量时间
4. 当前更重要的是简历内容质量，不是 PDF 自动化

### 正确做法

先做：

```text
Markdown 简历草稿
```

后做：

```text
Word / PDF 导出
```

---

## 3.3 不应照搬 Go TUI Dashboard

Career-Ops 的 Dashboard TUI 很酷，但 OfferClaw 不适合现在做。

### 原因

1. 你当前主语言是 Python
2. 你的求职方向不是 Go / TUI
3. 你已经有 FastAPI + `/ui`
4. 继续优化 Web 控制台比做 TUI 更适合展示

### 正确做法

保留：

```text
FastAPI + static/index.html
```

后续如需更美观，可以再考虑：

```text
Streamlit / Gradio / React
```

而不是 Go TUI。

---

## 3.4 不应照搬批量并行评估

Career-Ops 支持批量评估多个岗位。

OfferClaw 当前不应优先做批处理。

### 原因

1. 你的当前目标是先做好少量高质量投递
2. 批量评估容易诱导海投
3. 你当前更需要补项目和技能，而不是扩大岗位量
4. 批处理对简历项目价值不如 Agent 主动规划和 RAG

### 正确做法

先支持：

```text
单个 JD 高质量分析
3-5 个 JD 横向对比
applications 状态管理
```

后续再考虑批量。

---

## 3.5 不应照搬“已有 CV 驱动”的假设

Career-Ops 默认用户已经有比较完整的 CV。

OfferClaw 的用户画像不同。

### 你的场景

```text
简历还不完整
项目正在建设
没有 AI 实习经历
需要通过 OfferClaw 项目本身补强经历
```

所以 OfferClaw 不应以“已有 CV 优化”为中心，而应以：

```text
不完整画像 → 补项目 / 补技能 → 形成简历 → 再投递
```

为主线。

这正是 OfferClaw 和 Career-Ops 最大差异化。

---

## 4. Career-Ops 思想转化为 OfferClaw 的方案

---

## 4.1 从 Auto-Pipeline 转化为 Career Flow

Career-Ops 的 Auto-Pipeline 是：

```text
URL → evaluation → PDF → tracker
```

OfferClaw 应转化为：

```text
Profile → JD → Match → Gap → Plan → Daily Action → Resume Draft → Application
```

对应模块：

| Career-Ops | OfferClaw 转化 |
|---|---|
| Auto-Pipeline | Career Flow |
| Evaluation | Job Match |
| PDF | Resume Draft |
| Tracker | Applications |
| Story Bank | Interview Story Bank |
| Doctor / Verify | Doctor / Verify Pipeline |
| Portal Scanner | Job Discovery Assistant |

---

## 4.2 从 CV Match 转化为 Profile + Growth Match

Career-Ops 主要比较 CV 与 JD。

OfferClaw 应比较：

```text
当前画像
+ 当前项目进度
+ 当前学习状态
+ 目标岗位要求
```

因此输出不只是“是否匹配”，还要输出：

```text
该补什么
多久补
今天做什么
简历怎么更新
是否进入投递池
```

---

## 4.3 从 Story Bank 转化为 Project Story Bank

Career-Ops 面试故事库更多服务已有职业经历。

OfferClaw 的故事库应围绕项目成长过程：

```text
1. 为什么做 OfferClaw
2. 如何定义需求
3. 如何搭建规则系统
4. 如何实现 Agent 工具调用
5. 如何引入 RAG
6. 如何用 LangGraph 管理流程
7. 如何做 FastAPI 服务化
8. 如何做验证和回归
```

---

## 4.4 从 Pipeline Integrity 转化为 Project Integrity

Career-Ops 的完整性检查主要面向投递 pipeline。

OfferClaw 的完整性检查应同时覆盖：

```text
1. 代码能否运行
2. API 能否启动
3. RAG 是否可检索
4. README 指标是否一致
5. applications 状态是否合法
6. JD 是否去重
7. 用户层和系统层是否混写
```

---

## 5. OfferClaw 当前应改进的点

按照优先级排序：

---

### P0：README 叙事重构

目标：

让 README 更像产品首页，而不是项目状态堆叠。

改进点：

1. 第一屏先讲问题和价值
2. 指标放到 Evaluation
3. 技术栈分组展示
4. 删除过密信息
5. 明确边界和限制

---

### P1：指标与证据一致性检查

目标：

保证 README、verification_report、PROJECT_STATUS、project_one_pager 口径一致。

建议新增：

```text
verify_docs.py
```

检查：

- Recall@5
- MRR
- chunks
- API routes
- pytest
- doctor
- verify_pipeline

---

### P2：applications 状态规范化

目标：

让投递 tracker 从“表格”变成“可信 pipeline”。

建议新增：

```text
normalize_applications.py
```

检查：

- 状态是否合法
- 必填字段是否缺失
- 同一岗位是否重复
- 下一步动作是否为空

---

### P3：Interview Story Bank 强化

目标：

让故事库真正服务面试。

新增内容：

1. 每条故事绑定一个技术主题
2. 每条故事绑定可回答的问题
3. 每条故事绑定相关文件
4. 每条故事写 Reflection

---

### P4：JD Discovery 边界强化

目标：

避免被理解为爬虫或自动投递工具。

改进：

1. README 明确“半自动抽取”
2. `docs/ethical_use.md` 强调不登录、不批量抓取
3. job_discovery 输出来源类型和可信度
4. applications 只在用户确认后写入

---

### P5：Resume Builder 分阶段升级

目标：

从项目段生成走向 Markdown 简历草稿。

阶段：

1. 项目段
2. 技能栏
3. 竞赛经历
4. 完整 Markdown 简历
5. Word / PDF 导出

当前只做到第 1-2 阶段即可。

---

## 6. 三阶段改进计划

---

## 阶段 A：README 与证据链收口

### 目标

让外部访问者 30 秒内理解项目，并相信项目真实可运行。

### 任务

1. 重构 README 第一屏
2. 移动详细指标到 Evaluation
3. 统一 verification_report
4. 新增或增强 verify_docs.py
5. 清理文档口径冲突

### 验收标准

1. README 第一屏清晰
2. 指标一致
3. 能看到 Quick Start
4. 能看到 Demo 链接
5. 能看到 Limitations

---

## 阶段 B：求职运营闭环强化

### 目标

让 OfferClaw 不只是技术 Demo，而是能支撑真实求职。

### 任务

1. applications 至少维护 5 条真实岗位
2. normalize_applications.py 检查状态
3. story bank 补 5 条 STAR+R
4. resume_builder 能生成 Markdown 项目段
5. career_agent 能根据 applications 输出今日建议

### 验收标准

1. /api/today 输出与 applications 状态有关
2. resume_builder 能基于某个 JD 输出定制项目段
3. story bank 能支撑 5 个面试问题

---

## 阶段 C：产品化体验增强

### 目标

让本地 `/ui` 成为可日常使用的求职控制台。

### 任务

1. 优化 6 卡片 UI
2. 增强今日建议横条
3. 增加 applications 预览
4. 增加简历草稿预览
5. 增加 RAG 查询结果来源展示
6. 增加 Demo 截图

### 验收标准

1. 页面能完成一次完整流程
2. 用户不需要命令行也能体验核心功能
3. 有截图和 1 分钟演示脚本

---

## 7. 不建议新增的内容

当前不建议：

1. 自动投递
2. 大规模招聘爬虫
3. PDF 自动生成作为主线
4. Go TUI
5. 批量岗位并行处理
6. 复杂多用户登录系统
7. React 重写前端
8. 新比赛方向

原因：

```text
这些会偏离你当前的 AI Agent / RAG / FastAPI / LangGraph 求职主线。
```

---

## 8. 最终改进路线

建议路线：

```text
README 重构
→ 指标一致性检查
→ applications 真实使用
→ story bank 强化
→ /ui 产品化
→ resume_builder 增强
→ job_discovery 边界化
→ 投递材料收口
```

不要反过来做。

---

## 9. 给 Claude 的下一步执行指令

```text
请基于当前 OfferClaw 仓库和 Career-Ops 的设计思想，执行下一步优化。

当前结论：
1. OfferClaw 不应照搬 Career-Ops。
2. 应学习 Career-Ops 的 README 叙事、数据契约、应用 tracker、story bank、pipeline integrity、human-in-the-loop。
3. 不应学习其自动门户扫描、批量投递、ATS PDF、Go TUI、批量并行评估。
4. 当前第一优先级是 README 重构和证据链统一。

本轮只做 README 优化方案，不写代码。

输出：
1. 当前 README 的问题
2. Career-Ops README 值得学习的点
3. OfferClaw README 新结构
4. 每一节应该写什么
5. 每一节应该删什么
6. 最后一版 README 初稿
```

---

## 10. 总结

Career-Ops 最值得 OfferClaw 学习的不是技术栈，而是：

```text
把求职过程做成可追踪、可复盘、可更新、可验证的工程系统。
```

OfferClaw 应该吸收它的系统思想，但保持自己的差异化：

```text
Career-Ops：已有 CV 候选人的投递运营系统
OfferClaw：非典型背景候选人的求职成长型 Agent
```

因此，OfferClaw 的下一步不是变成 Career-Ops 的 Python 复制版，而是：

```text
以 Career-Ops 的成熟运营结构为参考，
把 OfferClaw 打磨成一个更清晰、更可信、更可演示、更贴近 AI Agent 求职目标的个人主项目。
```
