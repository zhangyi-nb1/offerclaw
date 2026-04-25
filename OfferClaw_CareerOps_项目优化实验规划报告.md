OfferClaw 当前实验规划方案

一、当前基准判断

OfferClaw 当前已经具备“可放进简历”的项目基础，但还没有完全达到你最初设想中的“本地可交互 AI 求职网站 / 智能求职作战官”。

当前项目已经具备：
1. 长期状态型 Agent 的项目定位
2. 用户画像、岗位匹配、规划、复盘的基础闭环
3. RAG、LangGraph、FastAPI、Function Calling、测试、验证报告等工程模块
4. DATA_CONTRACT、applications、verification_report 等项目治理文件
5. GitHub 公开仓库和基本展示材料

当前仓库 README 仍将 OfferClaw 定义为“长期运行、带状态、围绕单个求职者成长的执行型 AI Agent”，核心闭环是“画像 → 匹配 → 规划 → 执行 → 复盘 → 回到画像更新”。:contentReference[oaicite:0]{index=0}  
仓库也已经具备 RAG、API、规划、工具、用户画像等代码和配置文件，例如 plan_gen、rag_agent、rag_api、rag_graph、rag_ingest、rag_tools、tools、user_profile 等。:contentReference[oaicite:1]{index=1}  
此外，DATA_CONTRACT 已经明确把资产划分为 User Layer、System Layer、Runtime / Secrets，并强调用户层负责“我是谁、我做了什么”，系统层负责“OfferClaw 是什么、怎么做”。:contentReference[oaicite:2]{index=2}  
applications.md 也已经建立真实投递追踪表，并明确它和 jd_candidates.md 的区别：前者是前台投递池，后者是 JD 测试池。:contentReference[oaicite:3]{index=3}  
verification_report.md 已经固化 doctor、verify_pipeline、pytest、eval_rag、FastAPI 等验证命令与现场证据，说明项目开始具备工程验证意识。:contentReference[oaicite:4]{index=4}

但从你的最初目标看，当前项目仍然存在明显差距：

1. 还不像一个“每天打开就能使用”的本地 AI 网站
2. 还不够主动，更多是模块化工具集合，而不是自主推进求职任务的 Agent
3. JD 推荐 / 发现能力不足，仍主要依赖用户粘贴 JD
4. 简历从 0 到 1 生成链路还没有形成核心功能
5. RAG 主要围绕项目文档，知识域还偏窄
6. 前端交互还不够统一、美观和产品化
7. Agent 的规划能力、状态更新能力、任务推进能力还不明显
8. 部分指标、README、验证文档和实际代码之间仍可能存在口径不一致风险

所以当前最准确的阶段定义是：

OfferClaw 已经是“简历可展示的 AI Agent 工程项目”，但还不是“成熟的智能求职执行产品”。

二、你的最初项目预期

你理想中的 OfferClaw 应该做到：

1. 在本地打开一个页面
2. 用户提交非完整简历式个人信息
3. 系统分析用户画像
4. 系统推荐适合的 JD，或允许用户自行粘贴 JD
5. 系统分析岗位匹配度和技能缺口
6. 系统生成个人求职规划
7. 系统推动每日执行和每周复盘
8. 系统根据执行记录更新用户画像和路线
9. 系统逐步生成简历草稿
10. 系统辅助真实投递岗位
11. 系统在整个过程中体现智能 Agent 的主动性，而不是只做问答和检索

你的核心担心是：

1. 当前系统仍然围绕你个人样本，泛化不足
2. 当前计划像是你预先给定的，不像 Agent 智能生成
3. 当前 Agent 特征不够明显
4. 当前 RAG 像是只在有限文件中搜索，不够丰富
5. 当前 UI 交互还不像一个真正的 AI 网站
6. 当前项目虽然有技术栈，但使用体验仍偏死板
7. 当前系统还没有真正从“分析”走向“推动求职结果”

这些担心是成立的。

三、实验总目标

接下来的实验不应再以“继续堆技术栈”为目标，而应转为：

把 OfferClaw 从“功能模块齐全的 AI Agent 工程项目”
推进为
“本地可交互、能主动推进求职流程、能生成简历和投递闭环的求职执行 Agent”。

实验总路线：

阶段 1：收口可信度
阶段 2：强化本地交互
阶段 3：强化 Agent 主动性
阶段 4：引入 JD 发现与推荐
阶段 5：形成简历生成和投递闭环
阶段 6：扩展 RAG 知识域
阶段 7：做多用户与泛化验证
阶段 8：形成最终简历展示版本

四、当前核心问题拆解

问题一：项目已经能展示，但还不像产品

表现：
1. 虽然有 FastAPI 和 /ui，但整体页面还没有形成完整求职控制台
2. 用户不能在一个页面自然完成画像填写、JD 分析、计划生成、复盘和简历生成
3. 模块之间还像分散工具，而不是统一产品流程

解决方向：
1. 将 /ui 重构为本地求职控制台
2. 页面分成六个功能区：
   - 用户画像区
   - JD 分析区
   - 缺口分析区
   - 计划生成区
   - 每日执行区
   - 简历生成区
3. 优先使用现有 FastAPI + static/index.html，不急着上 React
4. 保持本地运行、低依赖、好演示

问题二：Agent 主动性不足

表现：
1. 当前更像用户提问，系统回答
2. 系统不会主动判断“今天应该做什么”
3. 系统不会基于 applications、daily_log、user_profile 自动推进下一步
4. 系统没有统一的求职作战控制器

解决方向：
新增或重构一个顶层 Agent Orchestrator。

建议模块：
career_agent.py 或 career_flow.py

建议工作流：
profile_node
→ job_discovery_node
→ job_match_node
→ gap_analysis_node
→ plan_node
→ daily_action_node
→ weekly_review_node
→ resume_draft_node
→ application_update_node

目标：
每次打开系统时，它能基于当前状态主动输出：
1. 你当前最接近哪个岗位
2. 今天最应该补什么
3. 哪个 JD 值得投
4. 哪个计划需要调整
5. 简历还缺哪一段

问题三：JD 推荐能力不足

表现：
1. 目前主要支持用户自行粘贴 JD
2. jd_candidates 更像测试池
3. applications 是投递池，但真实投递记录较少
4. 系统不能主动发现 JD

解决方向：
新增 Job Discovery 能力，但不做高风险爬虫。

推荐分三步：
1. V1：用户提供公司官网或招聘页 URL，系统抽取 JD 摘要
2. V2：系统根据用户画像生成搜索关键词，并检索公开官方招聘页
3. V3：支持多个 JD 横向排序，但仍不自动投递

不做：
1. 自动登录招聘网站
2. 自动海投
3. 绕过平台规则
4. 批量骚扰 HR

建议新增模块：
job_discovery.py

建议输出：
1. JD 标题
2. 公司
3. 地点
4. 技术关键词
5. 岗位方向
6. 是否进入 applications
7. 推荐理由

问题四：简历从 0 到 1 生成能力不足

表现：
1. 目前有 resume_pitch 和 story bank，但还不像一个简历生成模块
2. 系统不能自动从 user_profile、projects、daily_log、applications 中生成简历初稿
3. 简历还依赖人工整理

解决方向：
新增 resume_builder.py。

输入：
1. user_profile.md
2. interview_story_bank.md
3. PROJECT_STATUS.md
4. applications.md
5. daily_log.md
6. docs/resume_pitch.md

输出：
1. 简历技能栏草稿
2. 项目经历草稿
3. 竞赛经历草稿
4. 求职方向摘要
5. 针对某份 JD 的定制版项目描述

注意：
系统只能生成草稿，不能伪造经历。
所有简历内容必须由用户确认。

问题五：RAG 知识域偏窄

表现：
1. 当前 RAG 技术链路已经成立
2. 但知识库主要围绕项目文件
3. 对求职执行的支撑还不够强
4. 没有充分接入 JD、applications、daily_log、story bank、学习资料

解决方向：
扩展 RAG 知识域，而不是先换模型或堆指标。

优先纳入：
1. jd_candidates.md
2. applications.md
3. daily_log.md
4. interview_story_bank.md
5. resume_pitch.md
6. project_one_pager.md
7. 技术学习笔记
8. 岗位技能要求总结

RAG 下一阶段目标：
不是单纯回答“项目是什么”，而是回答：
1. 我当前最适合哪类岗位？
2. 哪些 JD 和我的画像最接近？
3. 我当前最大的三项缺口是什么？
4. 最近一周执行是否偏离目标？
5. 简历应该重点突出哪段经历？
6. 哪些面试故事适合某个 JD？

问题六：当前项目仍偏单用户样本

表现：
1. 主流程仍以 Zhang Yi 为样本
2. profiles 只是测试数据，还没有真正驱动完整链路
3. /api/profile 之前也存在硬编码风险
4. 泛化能力还需要验证

解决方向：
做 Persona 回归测试。

至少支持三类 persona：
1. 非计算机转 AI 应用
2. 计算机本科无 LLM 项目
3. 有 Agent 项目但工程基础弱

验证：
同一 JD 在不同 persona 下，系统给出的匹配结论、缺口清单和计划应明显不同。

五、实验阶段规划

阶段一：可信度收口

目标：
确保 GitHub、README、指标、验证报告、applications 和 data contract 口径一致。

任务：
1. 统一 README 中当前指标
2. 统一 project_one_pager 中指标
3. 清理根目录临时文件
4. 检查 verification_report 与 README 是否一致
5. 确认 DATA_CONTRACT 与实际文件结构一致
6. applications 至少保留 3 条不同状态的真实候选岗位

验收标准：
1. README 不再出现新旧指标冲突
2. GitHub 根目录没有明显临时文件
3. verification_report 可作为项目证据链
4. applications 不只是模板，而是有真实状态样例
5. DATA_CONTRACT 能解释所有主要文件归属

阶段二：本地前端控制台实验

目标：
让 OfferClaw 从“脚本项目”变成“本地 AI 求职网站”。

任务：
1. 重构 /ui 页面布局
2. 增加用户画像输入卡片
3. 增加 JD 粘贴与分析卡片
4. 增加缺口清单显示卡片
5. 增加计划生成卡片
6. 增加 daily_log 写入或预览卡片
7. 增加简历草稿生成入口

技术：
1. FastAPI
2. static/index.html
3. Vanilla JS
4. CSS 卡片布局
5. fetch API
6. SSE 保留

暂不引入：
1. React
2. Vue
3. 登录系统
4. 数据库

验收标准：
本地打开 http://127.0.0.1:8000/ui 后，可以完成：
1. 查看用户画像
2. 粘贴 JD
3. 生成匹配结果
4. 生成计划
5. 查看 RAG 回答
6. 生成简历草稿入口

阶段三：Agent 主动规划实验

目标：
让 OfferClaw 不只是被动问答，而是能主动判断下一步。

任务：
1. 新增 career_agent.py 或 career_flow.py
2. 定义全局状态：
   - profile
   - jd_pool
   - applications
   - gaps
   - plan
   - daily_log
   - resume_draft
3. 设计节点：
   - analyze_profile
   - discover_or_import_jd
   - match_job
   - analyze_gap
   - generate_plan
   - generate_daily_task
   - weekly_review
   - update_resume_draft
4. 每次运行输出“今日建议”

验收标准：
系统能主动输出：
1. 今天最该做什么
2. 为什么做这个
3. 对应哪个岗位缺口
4. 是否写入 daily_log
5. 是否更新 applications

阶段四：JD 发现与推荐实验

目标：
让系统从“用户粘贴 JD”升级为“用户可粘贴 JD，也可由系统发现 JD”。

任务：
1. 新增 job_discovery.py
2. 用户输入目标岗位方向和城市
3. 生成搜索关键词
4. 支持用户输入官方招聘页 URL
5. 抽取岗位标题、地点、要求、技术关键词
6. 写入 jd_candidates 或 applications
7. 调用 match_job 进行初筛
8. 生成推荐排序

第一版范围：
半自动，不做全网爬虫。

验收标准：
用户提供 3 个官方招聘链接后，系统能：
1. 抽取 JD 基本字段
2. 判断是否符合地域和方向
3. 给出是否推荐进入 applications
4. 输出排序和理由

阶段五：简历生成闭环实验

目标：
实现从 user_profile 到简历草稿的 0-1 生成。

任务：
1. 新增 resume_builder.py
2. 读取 user_profile
3. 读取 project_one_pager
4. 读取 interview_story_bank
5. 读取 applications 中目标 JD
6. 生成简历草稿
7. 支持针对不同 JD 改写项目描述
8. 输出 Markdown 简历片段

输出：
1. 技能栏
2. 项目经历
3. 竞赛经历
4. 求职摘要
5. JD 定制版项目描述

验收标准：
输入某个目标 JD 后，系统能生成：
1. 一段项目经历
2. 一段技能描述
3. 一段匹配该 JD 的自我介绍
4. 且不编造不存在的经历

阶段六：RAG 知识域扩展实验

目标：
让 RAG 真正服务求职执行，而不是只问项目文档。

任务：
1. 把 applications 纳入 RAG
2. 把 daily_log 纳入 RAG
3. 把 interview_story_bank 纳入 RAG
4. 把 resume_pitch 纳入 RAG
5. 把项目学习笔记纳入 RAG
6. 设置不同知识源标签
7. 检索结果返回 source_type

知识源标签：
1. profile
2. jd
3. application
4. log
5. story
6. resume
7. project_doc
8. learning_note

验收标准：
系统能回答：
1. 我最近一周做了什么？
2. 我还差哪些投递材料？
3. 哪个岗位最值得投？
4. 哪个项目故事适合某份 JD？
5. 我简历中最该强调什么？

阶段七：多用户泛化验证实验

目标：
证明 OfferClaw 不只是为你个人硬编码。

任务：
1. 完成 3 个 persona profile
2. 同一批 JD 在 3 个 persona 上跑
3. 对比匹配结论
4. 对比计划差异
5. 对比简历生成差异

验收标准：
1. 不同 persona 结果明显不同
2. 系统不依赖 Zhang Yi 固定字段
3. applications 可以分用户或分 profile 管理
4. profile API 不硬编码

阶段八：投递材料最终收口

目标：
让 OfferClaw 成为正式简历主项目。

任务：
1. 更新 README
2. 更新 verification_report
3. 更新 resume_pitch
4. 更新 interview_qa
5. 生成 1 分钟 Demo 脚本
6. 生成一版可投递简历项目描述
7. 固定一条演示链：
   profile → JD discovery → match → plan → daily task → resume draft

验收标准：
1. 简历能写
2. GitHub 能看
3. Demo 能跑
4. 面试能讲
5. 后续规划清晰

六、优先级排序

第一优先级：
1. 统一指标口径
2. 清理 GitHub 仓库
3. 修 /api/profile 去硬编码
4. 优化 /ui 为求职控制台

第二优先级：
1. career_agent.py / career_flow.py
2. job_discovery.py
3. resume_builder.py

第三优先级：
1. RAG 知识源扩展
2. persona 回归测试
3. applications 真实投递数据积累

第四优先级：
1. React 或更复杂前端
2. 自动搜索全网 JD
3. Docker / CI/CD 深度工程化
4. 多用户账户系统

七、当前立刻该做什么

当前不要直接开 JD discovery，也不要先做 resume_builder。

最先做：

1. 修 /api/profile 去硬编码
2. 把 /ui 改成清晰的求职控制台
3. 固定本地页面的主流程：
   profile → JD 粘贴 → match → plan → daily task → resume draft 占位

原因：
你现在最大的落差不是没有新算法，而是打开页面后不像一个真正“属于你的智能求职系统”。

八、给 Claude 的下一步指令

你可以直接发给 Claude：

请基于当前 OfferClaw 仓库继续推进下一阶段优化。

当前项目判断：
OfferClaw 已经具备简历项目基础，但还没有完全达到“本地 AI 求职网站 / 主动求职 Agent”的理想形态。
当前问题不是缺少 RAG、LangGraph 或 FastAPI，而是：
1. 本地 UI 不够像产品
2. Agent 主动规划不足
3. JD 推荐能力不足
4. 简历从 0 到 1 生成不足
5. RAG 知识域偏窄
6. 当前系统仍偏单用户样本

本轮只做第一阶段实验：
“/api/profile 去硬编码 + /ui 求职控制台化”。

任务一：
检查 rag_api.py 中 /api/profile 是否仍有硬编码字段。
如果有，改成从 user_profile.md 或 profiles/*.json 读取。
不做复杂 parser，先做最小可靠解析。

任务二：
检查 static/index.html。
把 /ui 页面重构为六个卡片区：
1. 用户画像
2. JD 分析
3. 缺口清单
4. 计划生成
5. 每日执行
6. 简历草稿

任务三：
每个卡片先接已有 API 或占位按钮：
1. /api/profile
2. /api/match
3. /api/query
4. 后续 plan / summary / resume 可先占位

任务四：
不要引入 React，不要加登录，不要做数据库，不要写自动爬虫。

输出：
1. 修改方案
2. 涉及文件
3. 每个文件怎么改
4. 最小代码实现
5. 本地运行验证步骤

九、最终判断

OfferClaw 目前不是失败，也不是“问题很大”。
它的问题是：

技术模块已经超过雏形，
但产品体验和主动智能还停留在雏形。

所以后续重点不是再证明“我会 RAG / LangGraph / FastAPI”，而是证明：

我能把这些技术组织成一个真正推动求职流程的智能系统。