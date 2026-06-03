# OfferClaw V5 · 设计复盘与演进指导

> **定位**：本文档是 V4 完成后的一次设计复盘——对照项目的**原始设想**，拆解哪些做了、哪些没做、下一步怎么做。
> 不替代 PROJECT_STATUS.md（进度跟踪）和 README.md（对外展示），而是作为**后续开发的决策参照**。
>
> **创建时间**：2026-06-01
> **最近更新**：2026-06-02（新增 §八 OpenClaw 集成架构、已完成平台迁移）
> **当前版本**：V4（28 路由 / pytest 130 / RAG Recall@5=0.96 / OpenClaw skill 已就绪）

---

## 一、原始设想还原

OfferClaw 的初始设计目标（以下 8 点来自项目作者的完整描述）：

1. **用户画像 + 岗位匹配**：Agent 分析用户实际条件，与目标岗位匹配；差距大时给出风险提醒（学习量大、周期长等），用户自行决定是否继续
2. **岗位定向知识库**：提前根据岗位定位，从网上收集高质量的学习路线、经验贴、知识指南，构建知识库指导 Agent 的规划和建议
3. **OpenClaw 框架特性**：每日/每周定时推送任务、生成总结、进行反思，体现 OpenClaw 的养成式闭环
4. **任务推荐 + 用户导入**：任务由 Agent 从知识库推荐，但用户也可以自行导入；知识库未覆盖的内容及时更新
5. **学习留痕**：用户每天将学习进度留痕（上传文件、或在可访问平台记录后由 Agent 定时抓取）
6. **复盘→调整闭环**：Agent 根据用户实际完成情况，总结内容并给出次日建议，调整工作量或提醒补课
7. **知识库自动建立与维护**（后续优化）：根据用户选择的岗位方向，自动建立相关知识库并维护更新
8. **当前聚焦**：先定位"大模型应用工程师"一个方向，不做太大规模

---

## 二、逐点对照：已完成 vs 待完成

### 2.1 用户画像 + 岗位匹配 ✅ 已完成

**已做到的**：
- `match_job.py`：三层规则引擎（硬门槛 6 项 / 软性 6 项 / 三档结论），是项目最成熟的模块
- `job_match_prompt.md`：9 步 Prompt 契约，与规则版双通路互检
- `profile_loader.py`：13 字段画像 + `profile_schema.json` JSON Schema 校验
- `career_flow.py`：LangGraph 条件路由按匹配结果分 4 条路径（suitable / stretch / not_recommended / jd_too_short）
- `eval_match.py`：10 样本 × 3 档评估集，baseline status acc = 100%

**局限（可接受）**：
- 匹配基于关键词规则而非语义理解——但在当前规模下，规则版比纯 LLM 更可控、可回归，这是合理的设计取舍
- 风险提醒的颗粒度较粗（只有三档结论）——暂不需要更细的分级

**结论**：此模块不需要大改，后续只需随知识库扩展微调关键词列表。

---

### 2.2 岗位定向知识库 ❌ 核心缺口

**当前状态**：
- RAG 系统工程实现完善（自写分块 / LangGraph 4 节点 / ChromaDB / Recall@5=0.96）
- 但 160 chunks 全部来自项目自身文件（profile / log / system prompt / JD / 面试故事 / 项目文档）
- **完全没有外部岗位知识**——没有"大模型应用工程师学什么"、"RAG 学习路线"、"转 AI 经验分享"等内容

**问题本质**：
- RAG 的价值 = 检索能力 × 知识库质量
- 检索能力已验证（Recall@5=0.96），瓶颈 100% 在知识库内容

**三层推进计划**：

#### 第一层：手动策展（P0，1-2 天）

在项目根目录建立知识库目录，手动整理 10-20 篇高质量内容：

```
knowledge_base/
├── career_paths/                          # 岗位路线
│   ├── llm_app_engineer_roadmap.md        # 大模型应用工程师技能树与路线
│   ├── agent_engineer_skills.md           # Agent 工程师必备能力
│   └── rag_engineer_guide.md              # RAG 方向技术栈与学习顺序
├── experience_posts/                      # 经验贴（注明来源 URL + 抓取日期）
│   ├── exp_01_从零转AI应用开发.md
│   ├── exp_02_大模型实习面经.md
│   └── exp_03_Agent项目实战经验.md
└── learning_resources/                    # 学习资源清单
    ├── python_ml_foundations.md            # Python + ML 基础推荐资源
    ├── llm_api_and_prompt.md              # LLM API / Prompt Engineering 资源
    └── agent_framework_comparison.md      # Agent 框架对比（LangChain vs 手写 vs CrewAI 等）
```

**代码改动**：在 `rag_ingest.py` 的 `DEFAULT_FILES` 列表中追加这些文件，新增 source_type：

```python
# 新增 source_type
("knowledge_base/career_paths/llm_app_engineer_roadmap.md", "career_knowledge"),
("knowledge_base/career_paths/agent_engineer_skills.md", "career_knowledge"),
("knowledge_base/experience_posts/exp_01_从零转AI应用开发.md", "experience"),
("knowledge_base/learning_resources/python_ml_foundations.md", "resource"),
# ... 以此类推
```

**内容来源建议**（合法获取）：
- 掘金、知乎专栏中的原创技术路线文章（注明出处，仅供个人 RAG 使用）
- 各大公司公开的技术博客（如 Anthropic、OpenAI、LangChain 官方博客的中文翻译/总结）
- 自己整理的学习笔记（最有价值——因为是你真实走过的路）
- GitHub 上的公开 Awesome 列表（awesome-llm、awesome-agent 等）的精选摘要

**每篇文件建议格式**：
```markdown
---
source_url: https://xxx          # 原始来源（自己写的标 "original"）
crawl_date: 2026-06-01           # 收录日期
quality: A                       # 质量等级 A/B/C
target_role: 大模型应用工程师     # 适用岗位方向
tags: [RAG, 向量检索, 入门]       # 关键词标签
---

# 标题

正文内容...
```

#### 第二层：半自动采集工具（P4，2-3 天）

新建 `knowledge_crawler.py`：

```
输入：URL 列表（手动维护在 knowledge_base/sources.txt）
流程：
  1. 复用 job_discovery.py 的抓取逻辑（requests + Playwright 兜底）
  2. 正文提取 + 清洗（去广告、导航栏、评论区）
  3. LLM 打质量分（相关性 0-10 + 信息密度 0-10 + 时效性判断）
  4. 质量分 ≥ 7 的自动保存到 knowledge_base/ 对应子目录
  5. 质量分 < 7 的进入 knowledge_base/_pending/ 待人工审核
输出：每篇一个 .md 文件，带 metadata 头
```

#### 第三层：知识库维护机制（后续优化）

- 按 `crawl_date` 标记时效，超过 6 个月的自动标记 `stale`
- 定期重跑 `rag_ingest.py --rebuild` 刷新向量索引
- 新增 `POST /api/knowledge/ingest` 接口，支持在 UI 上直接提交 URL 入库

---

### 2.3 每日/每周定时任务 + 总结 + 反思 🟡 骨架有，运转不足

**已做到的**：
- `career_agent.py`：纯规则版 `get_today_advice()`（秒级返回，不依赖 LLM）
- `summary_tool.py`：单日/周度 LLM 复盘
- `plan_gen.py`：4 周计划生成
- JVS Claw 配了 3 条定时任务（早 09:00 / 晚 23:30 / 周日 21:30）

**缺失的**：
- 定时任务没有在本地持续运行的证据（JVS Claw 是云端，不易本地验证）
- 反思结论没有自动回写到次日计划（summary_tool 的输出是纯文本，不结构化）
- 4 周计划到每日任务没有自动拆解

**改进方案**：

1. **本地定时运行**（P3，1 天）
   - 新建 `scheduler.py`，用 Python `schedule` 库（或 APScheduler）实现：
     ```
     08:30  →  today_advice 生成 + 推送（终端通知 / 写文件）
     22:30  →  summary_tool 跑当日复盘
     周日 21:00  →  summary_tool --weekly
     ```
   - 也可用系统 crontab，但 Python 脚本更易跨平台

2. **复盘结构化输出**（纳入 2.6 一起做）

3. **计划自动拆解**（P2，0.5 天）
   - plan_gen 产出 4 周计划后，按周拆成 7 个 daily stub 写入 daily_log.md 的对应日期块
   - 每日 stub 只是建议框架（"今日主线：补 RAG 基础 / 建议耗时 2h"），用户可改

---

### 2.4 任务推荐 + 用户导入 🟡 推荐浅，导入缺

**已做到的**：
- `get_today_advice()` 做任务推荐，但纯规则、不查知识库
- plan_gen 的计划基于缺口清单，但缺口→学习资源的映射由 LLM 即兴生成

**缺失的**：
- plan_gen 不查 RAG 知识库——生成"学 RAG"的建议时不会引用知识库中已有的 RAG 学习路线
- 没有"用户导入自定义任务"的接口

**改进方案**：

1. **plan_gen 接入 RAG**（P1，0.5 天）——最高性价比改动
   - 在 plan_gen.py 生成计划前，先用缺口关键词查 RAG：
     ```python
     # 伪代码
     for gap in gap_list:
         hits = rag_query(gap["skill"], top_k=3, source_type="career_knowledge")
         gap["recommended_resources"] = hits
     ```
   - 把检索结果注入 prompt 上下文，让 LLM 基于真实资源推荐，而不是凭空编
   - 这样用户看到的计划里会出现"参考：《从零搭建 RAG 系统》- knowledge_base/..."

2. **任务导入接口**（P3，0.5 天）
   - 新增 `POST /api/task/import`：
     ```json
     {"date": "2026-06-02", "task": "看完 LangGraph 官方教程第 3 章", "tag": "补技能"}
     ```
   - 追加到 daily_log.md 对应日期块
   - 如果内容涉及知识库未覆盖的主题，提示"是否将相关资料加入知识库？"

---

### 2.5 学习留痕 🟡 有模板，缺交互入口

**已做到的**：
- daily_log.md 有完整留痕模板（主线标签 / 偏离度 / 明日建议）
- `POST /api/daily` 可以追加日志条目

**缺失的**：
- 输入方式只有"手动编辑 Markdown 文件"或"curl 调 API"，没有友好的 UI
- 没有从外部平台抓取学习记录的能力

**改进方案**：

| 方式 | 可行性 | 投入 | 优先级 |
|---|---|---|---|
| Web 表单（在 /ui 加"今日留痕"卡片） | ✅ 完全可行 | 1 天 | P3 |
| GitHub 抓取（读 commit/contribution） | ✅ 可行 | 2 天 | P4 |
| 文件上传（PDF/截图 + 文本提取） | ✅ 可行 | 2 天 | P4 |
| LeetCode/牛客抓取 | ⚠️ 有反爬风险 | 3 天 | 不建议 |
| 微信/飞书消息抓取 | ❌ 封闭生态 | — | 不做 |

**Web 表单设计**（P3）：
```
┌─────────────────────────────────────┐
│ 📝 今日学习留痕                       │
│                                     │
│ 今日主线标签：[补技能 ▼]              │
│                                     │
│ 完成的事：                           │
│ ┌─────────────────────────────────┐ │
│ │ （多行文本框）                    │ │
│ └─────────────────────────────────┘ │
│                                     │
│ 遇到的问题：                         │
│ ┌─────────────────────────────────┐ │
│ │                                 │ │
│ └─────────────────────────────────┘ │
│                                     │
│ 自评完成度：[██████░░░░ 60%]         │
│                                     │
│            [ 提交留痕 ]              │
└─────────────────────────────────────┘
```

提交后调 `POST /api/daily`，自动追加到 daily_log.md。

**GitHub 抓取**（P4）：
```python
# 新建 github_tracker.py
# 用 GitHub API (无需登录，public repo 免 token)
# GET https://api.github.com/users/{username}/events?per_page=30
# 筛选 PushEvent / CreateEvent，提取 commit message + 时间
# 每日定时跑一次，写入 daily_log.md
```

---

### 2.6 复盘→调整闭环 🟡 有复盘，缺自动调整

**已做到的**：
- `summary_tool.py` 产出"偏离度判断 + 明日建议"
- daily_log.md 有偏离度字段

**缺失的**：
- 复盘结论是纯文本，没有结构化回写到计划系统
- memory_layers.py 的三层架构搭好了但 `distill_to_semantic()` 是占位实现
- 没有"连续 N 天未完成 → 自动减量"的规则

**改进方案**（P2，1-2 天）：

1. **summary_tool 输出结构化**
   ```json
   {
     "date": "2026-06-01",
     "deviation_score": 40,
     "completed_tasks": ["看完 LangGraph 教程第 2 章", "写了 RAG 分块代码"],
     "incomplete_tasks": ["刷 LeetCode 2 题"],
     "blockers": ["LangGraph 条件边文档太少，耗时超预期"],
     "next_day_suggestion": {
       "adjust": "LeetCode 减到 1 题，LangGraph 增加 30 分钟",
       "priority": "继续 LangGraph，LeetCode 可延后"
     }
   }
   ```

2. **回写 memory_layers**
   - 每次复盘后，调 `EpisodicMemory.append()` 记录事件
   - 当连续 3 天某类任务未完成，`distill_to_semantic()` 写入偏好：`{"pattern": "leetcode_overload", "action": "reduce_to_1_per_day"}`
   - 当某个学习方法多次出现在"完成得好"的记录中，写入 Procedural 层作为 SOP

3. **today_advice 读取调整**
   - `get_today_advice()` 改为先查 Semantic 层的调整规则，再生成建议
   - 例如：发现 `leetcode_overload` 标记 → 建议里 LeetCode 只排 1 题

---

### 2.7 知识库自动建立与维护 ⚠️ 半可行

**结论**：初期必须人工策展，LLM 辅助筛选。完全自动化在当前阶段不现实也不必要。

| 环节 | 能否自动化 | 说明 |
|---|---|---|
| 搜索相关内容 | ✅ 可以 | 用搜索引擎 API（如 SerpAPI / Bing API）按岗位关键词搜索 |
| 抓取正文 | ✅ 可以 | 复用 job_discovery.py 的 requests + Playwright 兜底 |
| 质量筛选 | ⚠️ 半自动 | LLM 可做初筛（过滤广告/水文），但高质量判断仍需人工 |
| 去重 | ✅ 可以 | 按 URL + 内容 hash 去重 |
| 过期清理 | ⚠️ 需规则 | 按 crawl_date 标记，但"技术是否过时"需领域知识 |

**为什么不建议现在做全自动**：
- 你的目标方向只有"大模型应用工程师"一个，手动整理 10-20 篇就够用
- 全自动采集的最大风险是**低质量内容污染知识库**，反而让 Agent 的建议变差
- 投入产出比不高——花 5 天做自动采集，不如花 2 小时手动选 10 篇好文章

**后续可做的优化点**（V6+）：
- 用户在 UI 上一键提交 URL → Agent 自动抓取 + LLM 质量打分 → 分数高的直接入库，低的待审核
- 按岗位方向维护一个 `sources.yaml`，定期重抓检查是否有更新

---

### 2.8 聚焦"大模型应用工程师" ✅ 方向正确

当前 target_rules.md 已明确三个方向优先级：
1. Agent 应用工程
2. AI 应用开发
3. Prompt / Workflow 工程

**建议**：知识库的第一层手动策展就围绕这三个方向展开，不贪多。

---

## 三、技术层面深度分析

### 3.0 RAG 全面性能测试 + 优化结论（2026-06-03）

工具：`eval_rag.py`（内部文件 50Q）+ `eval_rag_domain.py`（分域诊断，tests/rag_domain_eval_set.json）。

**测量结果（605 chunks，4 大领域）：**

| 指标 | 结果 | 评价 |
|---|---|---|
| 分域召回 Recall@5 | llm_app/backend/algorithm/career 均 **100%** | ✅ 极好 |
| 跨域纯度（top-5 属本域占比） | **97%**（llm_app 93 / backend 100 / algo 100 / career 95） | ✅ 几乎不混淆 |
| in_kb 门槛准确率 | 负样本拒答 **5/5**、正样本命中 **5/5** | ✅ 满分 |
| 对抗负样本（Java/Docker/Linux/Go） | 全部正确拒答；Kafka 正确命中（MQ 章节含） | ✅ 鲁棒 |
| 内部文件 Recall@5（旧集50Q） | 0.84（fact 桶 0.706 偏弱） | 🟡 次要场景 |
| 延迟 | embedding 880ms · 检索 35ms · **LLM 合成 6.8s** · 未命中 0.9s | 瓶颈在合成 |

**对"分库 + LLM 路由"的结论：不做（数据不支持）。**
- 召回已 100%、跨域纯度已 97%——路由的天花板增益≈0（正确文档本就在 top-5 内）。
- LLM 路由会给每次查询再加 1~7s + 成本 + 一个失败点。embedding 已隐式完成"路由"且做得很好。
- 原则：KB 若未来涨到 10+ 领域 / 数千 chunks 致纯度下降，再用 `eval_rag_domain.py` 复测决定。

**实际做的优化（2026-06-03 全部落地）：**
- 词面救回上限 1.20 → **1.15**：挡掉"Git/仅被提及词"误命中，保住 react→ReAct。
- **RAG 合成换 qwen-turbo**（RAG_SYNTH_MODEL，原 qwen-plus）：grounded/兜底都够用，更快。
- **RAG 问答条改流式**：`/api/stream` 重写为走 rag_gate 的 gated_query_stream，
  UI ask() 改读流；首字 ~1.7s、来源 ~1.3s 即显示（原 6s 空白等待）。
- **门槛新原则（按用户要求改）**：命中→仅基于 KB 合成+标出处（mode=kb_grounded）；
  未命中→不再拒答，改用"通用知识 + 项目先验 + 弱相关片段"兜底，开头加"⚠️非知识库"标注
  （mode=general_fallback）。CLI / Web / 微信三入口一致。SKILL.md + AGENTS.md 已同步。
- 逻辑收口在 rag_gate.py：_retrieve_and_classify 共用，gated_query（非流式）/ gated_query_stream（流式）两入口。

### 3.1 RAG 系统：工程好，数据空（历史，已解决）

| 维度 | 当前状态 | 评价 |
|---|---|---|
| 检索精度 | Recall@5=0.96 | ✅ 优秀 |
| 向量模型 | 智谱 embedding-3 (2048 维) | ✅ 够用 |
| 分块策略 | RecursiveCharacterTextSplitter + 标题感知 | ✅ 合理 |
| 知识覆盖 | 160 chunks，全部内部文件 | ❌ 致命短板 |
| 知识时效 | 无自动更新机制 | ⚠️ 需补 |
| source_type 分类 | 9 类（profile/log/system/jd/story/...） | ✅ 体系有，但需扩展 |

**补充知识库后预期效果**：
- chunks 从 160 → 300-500（取决于策展内容量）
- 新增 3 个 source_type：`career_knowledge` / `experience` / `resource`
- plan_gen 的推荐将从"LLM 即兴编"变成"基于真实资源推荐"
- RAG 问答能回答"大模型应用工程师需要学什么"这类问题

### 3.2 Agent 编排：CareerFlow 够用，ReAct 偏浅

- CareerFlow（LangGraph 8 节点 + 4 条件路由）是项目的亮点，架构合理
- ReAct Agent 的 6 个 Tool 在 deterministic 模式下本质是 if/else 路由，LLM 模式需要 API KEY
- memory_layers 三层架构设计好但缺真实数据验证

**不需要大改**，重点是让已有架构跑起来、有真实数据流过。

### 3.3 前端：功能够用，体验粗糙

- 两套 UI（/ui 6 卡片 + /ui/console Stepper）都是纯 HTML 内嵌 FastAPI
- 缺少表单输入、文件上传等交互能力
- 不影响核心功能，但影响"用户真正愿意每天用"

---

## 四、优先级排序与行动路线

### 总原则

- 先补数据（知识库），再补闭环（复盘→调整），最后补交互（UI / 抓取）
- 每个阶段都应该能独立交付价值，不做"全做完才能用"的大包

### 路线图

```
P0 ─── 知识库手动策展 ✅ 已完成（2026-06-02）
  │    - 建 knowledge_base/ 目录结构 ✓
  │    - 策展 71 个文件（面试八股 RAG/Agent/Planner/Skills/Harness + 后端 + 算法 + 入门路线）✓
  │    - rag_ingest.py 加入新文件 + 新 source_type（career_knowledge/resource）✓
  │    - 重建向量索引：605 chunks（含图片噪音过滤 + 跨文件去重 + 断点续传）✓
  │    - 附带：迁移到百炼 text-embedding-v4（1024 维），LLM 切 qwen-plus ✓
  │
P1 ─── plan_gen 接入 RAG ✅ 已完成（2026-06-02）
  │    - retrieve_learning_resources()：逐条缺口 multi-query 检索 + 去重 ✓
  │    - prepare_plan_messages()：读依赖+检索+组装的统一入口，CLI/API 三路径共用 ✓
  │    - 检索结果注入 prompt 上下文（build_messages resources_block）✓
  │    - append_resources_appendix()：确定性追加参考资源附录（LLM 引用不稳定，代码兜底）✓
  │    - 片段清理：去 frontmatter/目录/图片，文件级标题指示性 ✓
  │    - 三路径一致：CLI + /api/plan + /api/plan/stream 都接入 RAG（流式把附录作末段推送）✓
  │    - 9 个离线单元测试（tests/test_plan_gen_rag.py）✓
  │    - 验证：CLI 与 API 输出都必含 6 份知识库资源引用 ✓
  │
P2 ─── 复盘→调整闭环 ✅ 已完成（2026-06-02）
  │    - summary_tool 输出结构化复盘（LLM JSON 块 + 确定性兜底解析 _parse_log_block）✓
  │    - record_reflection() 写入 Episodic；distill_reflections_to_semantic() 真实沉淀逻辑 ✓
  │    - 两类调整规则：high_deviation_streak（连续高偏离）+ recurring_incomplete（反复未完成）✓
  │    - today_advice 读 Semantic 调整规则 → adjustments 字段 + next_actions「复盘调整」✓
  │    - /api/today 增 adjustments 字段；TodayResponse 同步 ✓
  │    - 11 个离线单元测试（tests/test_reflection_loop.py）✓
  │    - 端到端验证：真实 LLM 复盘→记忆→沉淀→今日建议全链路跑通 ✓
  │
P2.5 ─ KB 问答门槛 + 微信路由修复 ✅ 已完成（2026-06-02）
  │    - 问题：微信问"什么是react"由 OpenClaw 底座模型直接抢答，没走知识库
  │    - cmd_query 混合相关性门槛：强向量(≤0.92) + 词面救回(≤1.20 且关键词字面命中)
  │      解决 "react" 与库内 "ReAct" 向量距离偏大但字面一致的语义鸿沟 ✓
  │    - 命中→基于 KB 合成答案 + 标注来源；未命中→坦白"知识库暂无"（不杜撰）✓
  │    - 双触发机制：skill description 强化 + AGENTS.md 硬路由规则（always-loaded）✓
  │    - 5 个混合门槛单元测试（tests/test_plan_gen_rag.py）✓
  │    - 微信真机复测通过（react→ReAct 正确）✓
  │    - 【2026-06-03 统一】门槛逻辑抽到 rag_gate.gated_query，CLI 与 Web /api/query 共用：
  │      Web 路径不再走老 rag_agent（靠 LLM 自判），改为同一硬门槛；
  │      QueryResponse 增 in_kb/sources/matched_by；/ui 问答条显示"命中知识库·来源"或"未命中"✓
  │      两入口行为完全一致：什么是react→ReAct(lexical_rescue) / Spring→坦白暂无 ✓
  │
P3 ─── 留痕全通路 + 定时任务 ✅ 已完成（2026-06-03）
  │    微信侧：
  │    - 结构化 log 命令 + review 命令（复盘触发）✓
  │    - 字段对齐：cmd_log / daily_log 模板 / summary_tool._section 统一 已完成/未完成 ✓
  │    Web 表单侧（原计划，已补做）：
  │    - /ui 每日卡片升级为结构化表单（主线标签 + 已完成 + 未完成 + 笔记）✓
  │    - POST /api/daily/log 结构化端点；与 CLI 共用 append_structured_daily_log 写入器 ✓
  │    GitHub 抓取（原计划，已补做）：
  │    - github_tracker.py：preview/sync，公开 commit → daily_log（主线=补项目）✓
  │    - 复用同一写入器，留痕格式统一；7 个解析单元测试 ✓
  │    定时任务：
  │    - 3 个 OpenClaw cron 脚本 scripts/setup_openclaw_cron.sh（需面板批准权限后跑）✓
  │    - SKILL.md 暴露 log/review/github sync；共 +13 单元测试
  │    - 验证：Web 表单→/api/daily/log→P2 解析对齐；GitHub 真账号 fetch 65 事件解析正常
  │
P4 ─── 半自动知识采集 ✅ 已完成 + 实战验证（2026-06-03）
  │    双轨架构（两轨共用同一质量门 + 审核流水线）：
  │    - 轨道1 crawl：公开页(GitHub/博客) requests+Playwright 抓取
  │    - 轨道2 from-text：登录态/反爬页(飞书/知乎/CSDN) 用浏览器插件(doc2kb/Claude-in-Chrome)
  │      读已渲染正文 → 存文件 → 接入同一打分/落盘（_score_and_save 共用）✓
  │    - LLM 质量门：grade(A/B/C/reject)+relevance/density；reject 自动丢弃不落盘 ✓
  │    - promote：人工确认后提升到正式库，修正 review_status/source_type ✓
  │    - 13 个离线单元测试；端到端实战：5 候选抓取
  │      → 2 知乎被反爬正确判 REJECT、3 GitHub 教程 grade A ✓
  │    - 实战发现并修复：①REJECT 不落盘 ②文件名加 URL 哈希防碰撞
  │      ③记录限制：知乎/CSDN 反爬(403)，经验贴需走轨道2(浏览器插件)
  │      ④记录限制：LLM 评分按主题相关打分，不惩罚"链接堆砌"(llm-action 57%链接拿A但RAG价值低)→ 加行级链接密度辅助人工判断
  │    - 已入库 #1 logan-zou 教程：612 chunks，去重自动跳过1近重复块(无冲突)，分域召回仍100% ✓
  │    - 【2026-06-03 审核界面增强】crawl/from-text 输出显式带 source_url（来源链接判质量）
  │      + saved_abs（本地绝对路径开文件验采集完整性）+ stats（字/行/链接占比/图片）+ preview（头尾）；
  │      新增 review/list 命令作为正式审核界面；list 过滤 doc2kb 工具产物只列真实候选。SKILL.md 已同步。
  │    - 【2026-06-03 关键修复：GitHub 只抓 README 的 bug】之前给仓库链接只抓到 README 简介(2.5KB)，
  │      漏掉真正章节内容。新增 crawl_repo：GitHub API 列树 → 抓 docs/notebook 下章节(.md/.ipynb，
  │      ipynb 提取 md+code 单元) → 拼成完整文档。cmd_crawl 自动识别仓库/README URL 改走整仓采集。
  │      重抓 logan-zou：29 章节/164KB(原 2.5KB，64×)；深层内容(调用智谱embedding/向量库/Bad Case)
  │      现可检索；861 chunks，分域召回仍 100%。+4 GitHub 单测，共 189 测试绿。
  │    - 【2026-06-03 图片显示修复】仓库内 .md 用相对图片路径(../figures/x.png)，采集后失效。
  │      新增 rewrite_image_links：相对路径按文件目录解析(含..)重写为 raw 绝对 URL；md+html img 都处理。
  │      重抓 logan-zou 后 0 相对路径，抽查图片 URL 全 HTTP200 image/png。+4 单测，共 193 测试绿。
  │
P5 ─── 端到端验证（1 天）
       - 用自己真实使用 1 周，产出完整的 daily_log 数据
       - 验证：知识库推荐 → 每日任务 → 留痕 → 复盘 → 调整 → 次日计划
       - 完整闭环跑通后更新 README / verification_report
```

### 时间估算

| 阶段 | 投入 | 累计 | 交付物 |
|---|---|---|---|
| P0 知识库策展 | 1-2 天 | 2 天 | knowledge_base/ 目录 + 重建后的 RAG 索引 |
| P1 plan_gen 接入 RAG | 0.5 天 | 2.5 天 | plan_gen 输出引用知识库资源 |
| P2 复盘闭环 | 1-2 天 | 4.5 天 | 结构化复盘 + memory 驱动的次日调整 |
| P3 留痕 UI | 1-2 天 | 6.5 天 | 可用的 Web 表单 + 任务导入 API |
| P4 半自动采集 | 2-3 天 | 9.5 天 | knowledge_crawler.py + GitHub 抓取 |
| P5 端到端验证 | 1 天 | 10.5 天 | 完整闭环运行证据 |

**P0 + P1 合计 2.5 天，即可让项目从"知识空心的 Agent"变成"能基于真实知识推荐学习路线的 Agent"。** 这是最高优先级。

---

## 五、不做的事（明确排除）

| 想法 | 不做的原因 |
|---|---|
| LeetCode / 牛客自动抓取 | 反爬风险高，账号可能被封，且留痕可以用更简单的方式实现 |
| 微信/飞书消息抓取 | 封闭生态，无公开 API，违反平台规则 |
| 全自动知识库建设（无人工参与） | 低质量内容会污染知识库，让 Agent 建议变差；当前只有一个岗位方向，手动够用 |
| 多用户 / 多租户 | 个人作品集项目，不需要 |
| 复杂前端框架（React/Vue 重写） | 投入产出比不高，当前 HTML 够用 |
| 自动投递简历 | 违反项目伦理边界（SOUL.md 硬边界） |

---

## 六、OpenClaw 集成架构（2026-06-02 已完成）

### 6.1 平台迁移

项目已从 JVS Claw（云端）迁移至本地 OpenClaw。所有 Python 代码和文档中的 "JVS Claw" 引用已清理。

**改动文件**：`rag_agent.py` · `rag_graph.py` · `agent_demo.py` · `SOUL.md` · `daily_log.md` · `user_profile.md` · `PROJECT_STATUS.md`

### 6.2 双入口架构

OfferClaw 有两个独立的用户入口，互不依赖：

```
入口 A：浏览器 UI（需手动启动 FastAPI）
  浏览器 → http://127.0.0.1:8000/ui → FastAPI (rag_api.py) → Python 模块
  适用场景：完整控制台、Stepper 流程、Swagger API 调试
  启动方式：.venv/bin/python -m uvicorn rag_api:app --port 8000

入口 B：微信（通过 OpenClaw，无需后台进程）
  微信 → OpenClaw → 触发 🦞 offerclaw skill → python offerclaw_cli.py → JSON → 微信
  适用场景：日常查询、留痕、匹配 JD、随时随地使用
  无需启动任何服务，每次调用跑一次脚本即结束
```

### 6.3 关键文件

| 文件 | 位置 | 作用 |
|---|---|---|
| `offerclaw_cli.py` | 项目根目录 | CLI 入口，8 个子命令（today/profile/match/query/daily/log/health/doctor），输出 JSON |
| `SKILL.md` | `~/.openclaw/workspace/skills/offerclaw/` | OpenClaw skill 定义，告诉 AI 何时触发、跑什么命令 |

### 6.4 CLI 命令速查

```bash
PYTHON=/Users/zhangronglei/Desktop/XIANGMU/offerclaw/.venv/bin/python
CLI=/Users/zhangronglei/Desktop/XIANGMU/offerclaw/offerclaw_cli.py

$PYTHON $CLI today                    # 今日建议
$PYTHON $CLI profile                  # 用户画像
$PYTHON $CLI match '某段 JD 原文'      # JD 匹配（三档结论 + 缺口）
$PYTHON $CLI query '某个问题'          # RAG 知识库问答
$PYTHON $CLI daily                    # 最近日志
$PYTHON $CLI log '今天学了 XXX'        # 追加留痕
$PYTHON $CLI health                   # ChromaDB 健康检查
$PYTHON $CLI doctor                   # 完整工程体检
```

### 6.5 定时任务（通过 OpenClaw cron）

| 时间 | 任务 | 触发方式 |
|---|---|---|
| 工作日 09:00 | 推送今日建议 | OpenClaw cron → `offerclaw_cli.py today` → 发到微信 |
| 每日 23:00 | 提醒留痕 | OpenClaw cron → 检查是否有当日 log，无则提醒 |
| 周日 21:00 | 周度回顾 | OpenClaw cron → `offerclaw_cli.py daily` → 总结本周 |

### 6.6 设计决策记录

- **为什么不通过 FastAPI 中转？** OpenClaw 直接调 Python 脚本即可，走 HTTP 需要后台常驻 FastAPI 进程，增加复杂度但不增加价值
- **为什么保留 FastAPI？** 浏览器 UI（6 卡片 + Stepper）仍需要 HTTP 服务，但只在需要时手动启动
- **CLI 和 FastAPI 共享什么？** 共享底层模块（career_agent / match_job / profile_loader / rag_tools 等），CLI 不经过 FastAPI 直接调用这些模块

---

## 七、代码改动点速查（含 OpenClaw 集成新增）

后续开发时可直接按此表定位需要修改的文件：

| 改动 | 涉及文件 | 改动类型 |
|---|---|---|
| 新增知识库目录 | `knowledge_base/` (新建) | 新建目录+文件 |
| RAG 索引扩展 | `rag_ingest.py` → `DEFAULT_FILES` 列表 | 追加条目 |
| plan_gen 接入 RAG | `plan_gen.py` | 在组装 prompt 前插入 RAG 检索 |
| 复盘结构化输出 | `summary_tool.py` | 输出格式从纯文本改为 JSON |
| memory distill 真实逻辑 | `memory_layers.py` → `distill_to_semantic()` | 替换占位实现 |
| today_advice 读 memory | `career_agent.py` → `get_today_advice()` | 增加 SemanticMemory 读取 |
| 留痕 UI 表单 | `rag_api.py` 的 `/ui` HTML 模板 | 追加表单 HTML + JS |
| 任务导入 API | `rag_api.py` | 新增 `POST /api/task/import` 路由 |
| 本地定时任务 | `scheduler.py` (新建) | 新文件 |
| 知识采集工具 | `knowledge_crawler.py` (新建) | 新文件 |
| GitHub 抓取 | `github_tracker.py` (新建) | 新文件 |
| OpenClaw CLI 入口 | `offerclaw_cli.py` | ✅ 已完成 |
| OpenClaw skill | `~/.openclaw/workspace/skills/offerclaw/SKILL.md` | ✅ 已完成 |

---

## 八、验收标准

每个阶段完成后的验收方式：

| 阶段 | 验收标准 |
|---|---|
| P0 | `python rag_ingest.py --rebuild` 后 chunks > 250；`POST /api/query {"query": "大模型应用工程师需要学什么"}` 返回知识库内容而非"未找到相关信息" |
| P1 | `python plan_gen.py` 的输出中出现 knowledge_base 中的资源引用 |
| P2 | `python summary_tool.py` 输出 JSON；连续模拟 3 天后 `semantic.json` 中出现调整规则；`GET /api/today` 的建议体现调整 |
| P3 | 浏览器打开 `/ui`，能通过表单提交留痕并在 daily_log.md 中看到新条目 |
| P4 | `python knowledge_crawler.py --urls sources.txt` 自动入库 ≥ 5 篇 |
| P5 | 连续 5 天的 daily_log 数据 + 每天的 today_advice 能看到基于前一天复盘的调整 |

---

## 九、增量 RAG + 项目先验 + 计划微信推送（2026-06-03）

按用户"理想 OfferClaw"诉求做的三项改造：

### 9.1 RAG 增量更新（不重建、不破坏原有、自动添加先确认）
- `rag_ingest.py --add <file>`：增量加单文件到现有 collection，**不重建、不动已有内容**。
- `knowledge_crawler.py promote --to X --ingest`：审核通过 → 移入正式库 → 增量入库，立即可检索。
- **自动添加先确认**：模型想补资料 → 先问用户 → 同意才 crawl → 落 _pending → 用户审核 → promote。
- 配置漂移检测（doctor）：换了 embedding 模型却没重建索引时，明确告警（解决换模型静默指向空库）。

### 9.2 换模型策略（应对免费额度耗尽频繁切换）
- **换 LLM = 零成本**（改 .env.local 即可）；**换 embedding = 必须重建索引**（向量空间不兼容）。
- 每个 provider/model/dim 独立 collection：切回旧模型若 collection 还在则**免重建**。
- 当前：v4 额度耗尽 → 已用 v3 重建（861 chunks），v4 collection 保留备切回。
- 长期建议：embedding 换本地模型（bge 等）根治额度问题（留待用户决定，需 torch）。

### 9.3 项目先验 + 只读边界
- `knowledge_base/project_context/`（新 source_type=project_context）：放用户已有项目现状。
  已建 `localflow.md`（基于真实 README：定位/技术栈/已完成模块/进度/学习主题对应）。
- `plan_gen.load_project_context()` 注入规划：实战缺口**优先编排为"在 LocalFlow 上推进的下一步"**，
  不让用户从零重造；措辞"建议你…"。**硬边界**：OfferClaw 对实战项目只读，绝不代为编码/改文件/提交。
- 也支持"从零搭新项目学习"（用户明确要求时）。SOUL.md 已写入只读硬边界。
- 验证：重跑 plan，计划已从"重造 RAG"改为"在 LocalFlow 加 RAG recipe/MCP工具/完善 verify-rollback"。

### 9.4 计划生成/更新推送微信
- `offerclaw_cli.py plan ['缺口/调整']`：生成 4 周计划（接 RAG + 项目先验），返回 `wechat_summary`
  （每周主题 + 资源数 + 完整计划路径）+ `saved_path` + `full_plan`。
- SKILL.md：生成/更新计划后**把 wechat_summary 推送给用户**；模型主动改进或用户要求调整后，
  重新生成并再次推送，让用户直观看到改动。

测试：共 203 passed；doctor 12 OK。

## 十、本地向量模型 + 图转文多模态 RAG（2026-06-03）

针对"稳定向量模型 + 图片/公式支持"诉求：

### 10.1 本地 embedding（根治额度，稳定）
- rag_tools 新增 `local` provider（sentence-transformers），别名 bge/st/hf 等。
- 默认 **BAAI/bge-base-zh-v1.5**（768维，~400MB）；加载优先 ModelScope（国内快、已缓存秒回），
  退 HuggingFace。bge-m3（2.3GB）可选但国内下载慢，留作升级项。
- 切到本地后：**永久免费、无额度、无网络**。已重建索引（867 chunks，本地 collection）。
- 模型相关阈值：rag_gate `_thresholds()` 按 provider 标定（本地 bge strong=0.85；百炼 0.92），
  env 可覆盖。换模型自动用对应阈值，不会再用错尺度。
- 公式：算法章节本就是 LaTeX 文本，text embedding 正常处理。
- 验证：本地 bge 分域召回 100%、纯度 91%、门槛 5/5+5/5；react→ReAct 变为原生向量命中(0.64)。

### 10.2 图转文（图片/图片版公式进 RAG）
- image_caption.py：ingest 前用 **qwen-vl**(VL_MODEL) 把 `![](img)` → `[图: 描述+OCR]`，
  按图片身份缓存到 _image_captions.json（重建复用，不重复调用）。
- 本地图 base64、http 图直传；失败/缺失降级删图（不杜撰）。`IMAGE_CAPTION=1` 开启。
- split 改为保留 `[图: …]` 描述（之前会被剥离）。
- 验证：LoRA 重参数化图被正确转文（含 W∈R^{d×d}、A=N(0,σ²) 等公式 OCR）。
- 注：全量 390 图转文需一次性 qwen-vl 调用（较慢/耗额度），按需开启 IMAGE_CAPTION=1 重建。

### 10.3 换模型须知（沉淀）
- **换 LLM 零成本**；**换 embedding 必须重建索引**（向量空间不兼容），各模型独立 collection。
- doctor 有配置漂移告警；本地 embedding 是最省心的稳定选择。

测试：共 210 passed；doctor 12 OK。

---

**本文档是活文件**。每完成一个 P 级阶段，回来更新对应状态。
