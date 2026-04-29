# OfferClaw 当前问题整理与下一步技术方案报告

> 版本：V1.0  
> 目标：基于当前 GitHub 仓库状态、用户反馈与项目最初需求，整理 OfferClaw 当前进度、主要问题、对应技术方案和下一步推进路线。  
> 项目地址：https://github.com/zhangyi-nb1/offerclaw  
> 适用场景：后续项目收口、功能优化、简历投递准备、Claude 协作开发输入文档。

---

## 1. 当前核心结论

OfferClaw 当前已经不是早期原型，而是进入了：

> **V2 功能主体基本完成，准备进行投递前真实性验证与产品体验收口的阶段。**

项目目前已经具备较完整的技术栈和业务闭环，包括：

- 用户画像
- 岗位匹配
- 缺口分析
- 学习规划
- 每日执行
- 周期复盘
- RAG 检索增强
- LangGraph 工作流
- FastAPI 接口
- SSE 流式响应
- 本地 `/ui` 控制台
- JD 半自动抽取
- 简历项目段生成
- 投递状态追踪
- 数据契约
- 工程验证报告
- 多 Persona 回归

但是，项目距离用户最初理想中的“真正每天可用、能主动推进求职的本地 AI 求职网站”仍有差距。

当前主要问题不是“缺少更多技术名词”，而是：

```text
功能链条已经搭出，但真实使用验证、产品交互体验、主动 Agent 能力、JD 推荐、简历生成闭环和证据链一致性还需要加强。
```

---

## 2. 最初项目需求回顾

OfferClaw 最初目标不是单纯参加比赛，也不是单纯堆技术栈，而是：

> 用一个真实可运行的 AI Agent 项目，弥补没有计算机相关实习和工程项目经验的短板，在 5 月 1 日前形成可写入简历、可用于投递 AI 应用 / Agent 实习岗的主项目。

理想中的 OfferClaw 应具备以下流程：

```text
在本地页面提交个人信息
→ 系统分析用户画像
→ 系统推荐或导入 JD
→ 分析岗位匹配度
→ 识别技能与项目缺口
→ 生成个人求职规划
→ 推动每日落实
→ 进行每周复盘
→ 从 0 到 1 生成简历材料
→ 辅助投递实习 / 正式岗位
```

因此，后续优化必须围绕三个最终用途：

| 用途 | 说明 |
|---|---|
| 简历主项目 | 弥补无 AI/CS 实习经历的短板 |
| 投递材料展示 | 证明具备 AI 应用 / Agent 工程能力 |
| 面试讲解素材 | 讲清 RAG、Agent、FastAPI、LangGraph、工具调用、状态管理等技术实践 |

---

## 3. 当前项目进度总结

### 3.1 当前已具备的能力

根据当前仓库 README 与文件结构，OfferClaw 已形成四层能力。

#### 第一层：求职业务闭环

- 用户画像
- 岗位匹配
- 缺口分析
- 学习规划
- 每日执行
- 周期复盘
- 状态更新

#### 第二层：Agent / RAG 工程能力

- LLM API 调用
- Function Calling
- 工具调用循环
- RAG 检索增强
- ChromaDB
- 智谱 `embedding-3`
- LangGraph 状态图
- FastAPI 接口
- SSE 流式输出

#### 第三层：本地产品化能力

- `/ui` 本地控制台
- 6 卡片布局
- 今日建议横条
- JD 匹配区
- 计划生成区
- 每日执行区
- 简历草稿区

#### 第四层：求职运营材料

- `DATA_CONTRACT.md`
- `applications.md`
- `interview_story_bank.md`
- `docs/project_one_pager.md`
- `docs/postmortem.md`
- `docs/ethical_use.md`
- `docs/resume_pitch.md`
- `docs/interview_qa.md`
- `docs/verification_report.md`

---

### 3.2 当前 README 展示指标

当前 README 展示的 V2 指标包括：

| 指标 | README 当前展示 |
|---|---|
| RAG Recall@5 | 0.96 |
| cross_doc | 1.00 |
| MRR | 0.67 |
| pytest | 37/37（+3 e2e skip） |
| FastAPI 接口 | 19 |
| SSE | 2 条 |
| 知识库 chunks | 160 |
| source_type | 8 类 |
| doctor | 8 OK |
| verify_pipeline | 6/6 |
| persona 回归 | 3 persona |

这些指标已经达到简历展示水平，但仍需确保 README、`verification_report.md`、`PROJECT_STATUS.md`、`project_one_pager.md` 的口径完全一致。

---

## 4. 用户当前关注的核心问题

用户当前主要关注以下三类问题。

---

### 4.1 问题一：当前本地运行是否真的能实现最初设想？

理想目标是：

```text
本地页面提交信息
→ 画像分析
→ JD 推荐 / 导入
→ 岗位匹配
→ 技能缺口分析
→ 求职规划
→ 每日执行
→ 每周复盘
→ 简历生成
→ 投递辅助
```

当前实现程度如下：

| 功能 | 当前状态 | 判断 |
|---|---|---|
| 用户画像 | 已具备 | 可用 |
| JD 粘贴分析 | 已具备 | 可用 |
| JD URL 半自动抽取 | 已具备雏形 | 可用但不成熟 |
| 岗位匹配 | 已具备 | 可用 |
| 缺口分析 | 已具备 | 可用 |
| 计划生成 | 已具备 | 需真实使用验证 |
| 每日执行 | 有 `daily_log` 和 `/api/daily` | 需真实数据积累 |
| 每周复盘 | 有 summary 机制 | 需真实数据积累 |
| 简历生成 | 有 JD 定制项目段 | 还不是完整简历生成器 |
| 投递辅助 | 有 applications tracker | 样本不足 |
| 本地页面 | 有 6 卡片控制台 | 需截图和演示验证 |
| Agent 主动性 | 有 `/api/today` 与 `career_agent.py` | 需真实数据验证 |

结论：

> 当前已经搭出理想系统的大部分能力链条，但尚未完全产品化，仍需要通过真实使用数据证明它能主动推进用户接近目标岗位。

---

### 4.2 问题二：能否做成更易交互、更美观的前端页面？

答案：可以，而且当前已经有基础。

当前项目已经有：

- FastAPI
- `/ui`
- `static/index.html`
- 6 卡片控制台
- 今日建议横条
- 多个 API 入口

因此当前不需要立刻引入 React。

推荐路线：

```text
V1：继续完善 static/index.html + Vanilla JS
V2：如需展示增强，可引入 Streamlit / Gradio
V3：只有明确需要前端工程能力时再考虑 React
```

原因：

1. 用户目标是 AI 应用 / Agent 岗，不是前端岗
2. 现有 FastAPI + 静态页面足够支撑本地 AI 网站
3. 零依赖前端更易维护
4. 简历应突出 Agent / RAG / FastAPI / LangGraph，而不是前端框架

---

### 4.3 问题三：JD 推荐、Agent 和 RAG 是否还不够强？

答案：当前确实仍有提升空间，但不能混淆“雏形”和“缺失”。

#### JD 推荐

当前 `job_discovery.py` 更准确地说是：

```text
半自动 JD 抽取与结构化模块
```

而不是：

```text
全自动 JD 推荐系统
```

当前可以支持：

- 粘贴 JD 原文
- 输入 JD URL
- 抽取公司、岗位、地点、技能关键词、职责和要求
- Playwright 回退处理部分 SPA 页面

但还不能完整做到：

```text
根据用户画像自动生成搜索关键词
→ 主动检索多个岗位
→ 去重
→ 排序
→ 写入 applications
→ 给出推荐理由
```

#### Agent 主动性

当前已有：

- `career_agent.py`
- `/api/today`
- applications / daily_log / user_profile 状态读取

但还需要真实数据验证它是否能输出有价值的今日建议。

真正的 Agent 应做到：

```text
读取当前画像、投递状态、执行日志和缺口
→ 判断今天最该做什么
→ 解释为什么
→ 指出关联岗位缺口
→ 建议是否写入 daily_log
```

#### RAG

当前 RAG 技术链路已经成立，但知识域仍需更贴近求职执行。

当前应继续扩展：

- `applications.md`
- `daily_log.md`
- `interview_story_bank.md`
- `resume_pitch.md`
- `project_one_pager.md`
- 学习笔记
- 目标 JD 池

---

## 5. 当前主要不足与对应技术方案

---

## 5.1 不足一：指标口径仍有不一致风险

### 表现

README、`docs/verification_report.md`、`PROJECT_STATUS.md`、`docs/project_one_pager.md` 之间可能存在指标不一致，例如：

- chunks 数量不一致
- routes 数量不一致
- doctor OK 数不一致
- RAG MRR 不一致
- README 与验证报告部分输出不一致

### 影响

这会削弱项目可信度。  
面试官不怕项目还在迭代，但会担心项目状态自己都说不清。

### 技术方案

重新运行并统一以下输出：

```bash
python doctor.py
python verify_pipeline.py
python -m pytest --tb=short
python eval_rag.py --k 5
python -m uvicorn rag_api:app --host 127.0.0.1 --port 8000
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/info
```

需要统一的字段：

- Recall@5
- cross_doc
- MRR
- pytest
- FastAPI routes
- SSE 数
- chunks
- source_type
- doctor OK
- verify_pipeline
- persona 回归状态

---

## 5.2 不足二：UI 缺少真实演示证据

### 表现

README 已说明 `/ui` 存在 6 卡片控制台，但仍需要真实截图和演示链证明它可用。

### 技术方案

新增或完善：

```text
docs/demo_assets/
docs/demo_script.md
docs/verification_report.md
```

需要截图：

1. `/ui` 首页
2. 今日建议横条
3. 用户画像卡片
4. JD 匹配卡片
5. 缺口分析卡片
6. 计划生成卡片
7. 每日执行卡片
8. 简历草稿卡片
9. Swagger `/docs`
10. doctor / pytest / RAG eval 终端输出

验收标准：

> 不是 README 说有 UI，而是真的有截图和演示链证明。

---

## 5.3 不足三：Agent 主动性仍需真实状态验证

### 表现

虽然已有 `career_agent.py` 和 `/api/today`，但需要验证它能否基于真实数据给出合理建议。

### 技术方案

1. 在 `applications.md` 中至少维护 3 条真实岗位：
   - 已评估
   - 准备投递
   - 不投递
2. 在 `daily_log.md` 中维护至少 3 天真实执行记录
3. 调用 `/api/today`
4. 判断输出是否基于实际状态而不是模板
5. 将结果写入验证报告或演示文档

验收标准：

```text
打开 /ui 后，顶部今日建议能基于 applications 和 daily_log 输出合理行动。
```

---

## 5.4 不足四：JD 推荐仍是半自动抽取，不是完整推荐系统

### 表现

当前 `job_discovery.py` 主要完成 JD 抽取，不是全自动推荐。

### 技术方案

分三层增强：

#### 第一层：Query Builder

根据用户画像生成搜索关键词，例如：

```text
AI 应用开发 实习 上海 Python Agent RAG
大模型应用开发 实习 南京 FastAPI Agent
```

#### 第二层：JD Fetcher

支持：

- 用户提供官方招聘页 URL
- 公开页面抽取
- Playwright 回退

#### 第三层：JD Ranker

调用现有 `match_job.py` 对候选 JD 进行排序，输出：

- 推荐等级
- 推荐理由
- 缺口
- 是否写入 applications

不做：

- 自动登录
- 自动投递
- 大规模爬虫
- 绕过平台规则

---

## 5.5 不足五：简历生成还不是完整简历系统

### 表现

当前 `resume_builder.py` 更偏 JD 定制项目段生成，不是完整简历生成器。

### 技术方案

阶段化增强：

#### V1：JD 定制项目段

当前已具备或接近具备。

#### V2：Markdown 简历草稿

新增函数：

```text
build_skill_section()
build_project_section()
build_competition_section()
build_resume_markdown()
```

#### V3：导出能力

后续再考虑：

- PDF
- Word
- HTML

约束：

- 不伪造经历
- 不夸大结果
- 所有简历内容需用户确认

---

## 5.6 不足六：RAG 知识域仍需扩展

### 表现

当前 RAG 指标已较好，但应进一步覆盖求职执行链。

### 技术方案

扩展 source_type：

```text
profile
jd
application
log
story
resume
project_doc
learning_note
```

优先加入：

- `applications.md`
- `daily_log.md`
- `interview_story_bank.md`
- `docs/resume_pitch.md`
- `docs/project_one_pager.md`
- `docs/verification_report.md`
- 学习笔记

目标查询：

```text
我最近一周做了什么？
我当前投递进展如何？
哪个 JD 最值得投？
哪个项目故事适合某份 JD？
我简历应该突出什么？
```

---

## 5.7 不足七：当前仍偏单用户样本

### 表现

当前系统虽然有 persona，但主流程仍以 Zhang Yi 为核心样本。

### 技术方案

完善 Persona 回归：

至少覆盖：

1. 非计算机转 AI 应用
2. 计算机本科无 LLM 项目
3. 有 Agent 项目但工程基础弱
4. 有实习但 AI 弱

验证同一 JD 在不同 persona 下输出：

- 不同匹配结论
- 不同缺口
- 不同计划
- 不同简历重点

---

## 6. 下一步实验推进路线

---

### 阶段 1：指标与证据链统一

目标：确保所有公开文档的指标一致。

任务：

1. 重跑 doctor
2. 重跑 verify_pipeline
3. 重跑 pytest
4. 重跑 eval_rag
5. 重查 `/health`
6. 重查 `/api/info`
7. 更新 verification_report
8. 更新 README
9. 更新 PROJECT_STATUS
10. 更新 project_one_pager

验收标准：

```text
所有文档中的 Recall@5、MRR、chunks、routes、doctor、pytest、verify_pipeline 完全一致。
```

---

### 阶段 2：UI 真实演示验证

目标：证明 `/ui` 是真实可用的求职控制台。

任务：

1. 启动 FastAPI
2. 打开 `/ui`
3. 截图 6 卡片
4. 跑一次 JD 匹配
5. 跑一次计划生成
6. 跑一次简历草稿
7. 跑一次 RAG 查询
8. 存入 `docs/demo_assets/`

验收标准：

1. 页面正常打开
2. 六个区块能显示
3. 至少三个区块能产生真实输出
4. 截图可用于 README 或 demo 文档

---

### 阶段 3：真实投递闭环验证

目标：证明 OfferClaw 不只是分析岗位，还能维护真实投递状态。

任务：

1. `applications.md` 补 3 条真实岗位
2. 每条给不同状态
3. 调用 `/api/today`
4. 检查 `career_agent.py` 建议是否合理
5. 用 `daily_log.md` 记录一天真实执行

验收标准：

1. applications 不再是空表
2. `/api/today` 输出基于真实状态
3. daily_log 有真实执行数据
4. 今日建议不是模板化空话

---

### 阶段 4：Agent 主动性增强

目标：让系统从被动工具变成主动求职作战官。

任务：

1. 优化 `career_agent.py`
2. 明确全局状态：
   - profile
   - applications
   - daily_log
   - gaps
   - plan
   - resume_draft
3. 每日生成：
   - 今日最重要任务
   - 原因
   - 对应岗位缺口
   - 是否写入 daily_log
4. UI 顶部展示今日建议

验收标准：

用户打开页面后，系统直接告诉用户：

```text
今天最该做什么
为什么
做完后更新哪里
```

---

### 阶段 5：JD 推荐能力增强

目标：从 JD 粘贴分析升级到半自动 JD 发现与推荐。

任务：

1. 优化 `job_discovery.py`
2. 增加画像关键词生成
3. 增强 URL 抽取稳定性
4. 增加 JD 去重
5. 增加推荐排序
6. 写入 applications 或 jd_candidates

验收标准：

用户输入目标方向和城市后，系统能给出：

1. 推荐搜索关键词
2. 候选 JD
3. 匹配排序
4. 推荐理由

---

### 阶段 6：简历生成闭环增强

目标：从项目段生成升级到简历草稿生成。

任务：

1. 增加技能栏生成
2. 增加项目经历生成
3. 增加竞赛经历生成
4. 增加 JD 定制版摘要
5. 输出 Markdown 简历草稿

验收标准：

输入一个 JD 后，系统能生成：

1. 技能栏
2. 项目经历
3. 求职摘要
4. JD 定制项目描述

且不编造事实。

---

### 阶段 7：RAG 知识域扩展

目标：让 RAG 服务完整求职执行链。

任务：

1. 加入 applications
2. 加入 daily_log
3. 加入 interview_story_bank
4. 加入 resume_pitch
5. 加入 learning notes
6. 重建索引
7. 扩展评估集

验收标准：

RAG 能回答：

1. 我最近投递了什么？
2. 我这周做了什么？
3. 我最适合哪份 JD？
4. 哪个故事适合某次面试？
5. 简历应该突出什么？

---

## 7. 优先级排序

### 第一优先级

1. 统一指标口径
2. 更新验证报告
3. 截图验证 UI
4. applications 补真实岗位
5. `/api/today` 主动建议验证

### 第二优先级

1. 增强 `career_agent.py`
2. 增强 `job_discovery.py`
3. 增强 `resume_builder.py`

### 第三优先级

1. 扩展 RAG 知识域
2. 增强 persona 回归
3. 补充更多真实 daily_log 样本

### 暂不做

1. 新比赛
2. 新框架
3. 重写前端
4. 自动投递
5. 大规模爬虫
6. 多用户账户系统

---

## 8. 下一步给 Claude 的执行指令

```text
请基于当前 OfferClaw 仓库继续推进：

https://github.com/zhangyi-nb1/offerclaw

当前判断固定如下：

1. OfferClaw 已经进入 V2 功能主体完成阶段。
2. 当前不是缺 RAG / LangGraph / FastAPI，而是需要投递前真实性验证与产品体验收口。
3. 当前需要重点解决：
   - README / verification_report / PROJECT_STATUS 指标口径统一
   - /ui 真实演示截图
   - applications 真实投递样本
   - /api/today 主动建议验证
   - 简历与面试材料最终化

本轮不要写新功能。
只做第一阶段：指标与证据链统一。

任务：
1. 读取 README.md、docs/verification_report.md、PROJECT_STATUS.md、docs/project_one_pager.md
2. 找出所有指标不一致
3. 以最新实际命令输出为准，给出统一口径
4. 输出需要修改的文件清单
5. 每个文件只给最小修改建议
6. 不要重写全文

必须统一的指标：
- Recall@5
- cross_doc
- MRR
- pytest
- FastAPI routes
- SSE 数
- chunks
- source_type
- doctor OK
- verify_pipeline
- persona 回归状态

输出结构：
1. 当前不一致清单
2. 统一后的指标表
3. README 修改建议
4. verification_report 修改建议
5. PROJECT_STATUS 修改建议
6. project_one_pager 修改建议
7. 下一步执行命令
```

---

## 9. 当前唯一立刻执行动作

```text
先统一 README、verification_report、PROJECT_STATUS、project_one_pager 的指标口径。
```

原因：

```text
当前功能已经足够强，但如果公开文档中的事实链不一致，会直接削弱项目可信度。
```

只有先把事实链校准，后续 UI 演示、applications 真实投递、简历最终版才有可信基础。
