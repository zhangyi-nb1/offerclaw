# OfferClaw · JVS Claw 部署文档  
  
> 本文档记录在 JVS Claw（openclaw-control-ui）平台上完成 OfferClaw 部署的全过程，  
> 用于回放、复用和写进简历。  
  
---  
  
## 0. 平台基础信息  
  
- **平台名**：JVS Claw（UI 显示 `openclaw-control-ui`，智能体名 `jarvis`）  
- **版本**：智能客服 · 严谨专业版  
- **基础模型**：gateway/jarvis（会话 runtime 字段确认）  
- **上下文长度**：约 13.1k tokens（截图显示 13.1k，输入 1792 / 输出 22.2k）  
- **部署日期**：2026-04-15（onboarding 首次执行）  
- **部署人**：Zhang Yi（OfferClaw 后台搭建者 + 前端验证者）  
  
---  
  
## 1. 账号与工作空间初始化（B1 · 已完成）  
  
- **注册路径**：JVS Claw 平台（(https://jvsclaw.aliyun.com/chat)）  
- **工作空间名**：/home/admin/openclaw/workspace/offerclaw/（项目文件目录）  
- **计费 / 配额**：单日调用上限（qwen3.6plus2.5× 每月1600积分）  
  
---  
  
## 2. 文件上传清单（B1 · 已完成）  
  
| 类别 | 文件 | 用途 | 上传状态 |  
|---|---|---|---|  
| 身份层 | SOUL.md | system prompt 来源 | ✅ 已上传 |  
| 规则层 | target_rules.md | 匹配规则 + 输出结构 | ✅ 已上传 |  
| 规则层 | source_policy.md | 证据等级与信息源规则 | ✅ 已上传 |  
| 数据层 | user_profile.md | 用户画像（核心状态文件） | ✅ 已上传（持续更新中） |  
| 数据层 | daily_log.md | 每日执行与复盘留痕 | ✅ 已上传 |  
| 工作流 | onboarding_prompt.md | 首次启动 / 画像初始化 | ✅ 已上传 |  
| 工作流 | job_match_prompt.md | 岗位匹配分析 | ✅ 已上传 |  
| 工作流 | plan_prompt.md | 路线规划（4 周计划） | ✅ 已上传 |  
| 工作流 | summary_prompt.md | 学习留痕 / 晚间复盘 | ✅ 已上传 |  
| 代码层 | match_job.py | 岗位匹配最小规则版（Python） | ✅ 已上传 |  
  
**上传方式**：用户通过 JVS Claw 对话界面以附件形式拖拽/上传，OfferClaw 在对话中读取后写入 offerclaw/ 工作目录  
  
---  
  
## 3. System Prompt 配置（B2 · 已完成）  
  
把 `SOUL.md` 全文粘贴进 system prompt 配置框。  
  
- **配置入口**：JVS Claw 智能体设置页 → system prompt 配置区（用户侧操作，具体菜单路径待用户截图补充）  
- **字数限制**：待补充  
- **是否支持文件引用替代粘贴**：待测试（当前做法：SOUL.md 作为工作空间文件由 OpenClaw 注入系统提示，而非手动粘贴）  
  
---  
  
## 4. 文件引用语法  
  
OfferClaw 在对话里要引用其他 .md 文件时，使用的语法：  
  
- **经测试可工作的写法**：直接写文件名（如 `请执行 onboarding_prompt.md`），模型通过工作空间文件自动读取  
  → 来源：2026-04-15 首次 onboarding 执行验证通过  
- **是否支持 `@filename`**：待测试  
- **是否支持 `{{filename}}`**：待测试  
- **文件改动后是否需要手动刷新**：待测试（OpenClaw 工作空间文件为实时加载，但具体刷新机制待确认）  
  
---  
  
## 5. 端到端验证（B3）  
  
### 5.1 onboarding 流程 ✅  
- **验证日期**：2026-04-15  
- **触发指令**：`执行 onboarding_prompt.md`  
- **输出验证**：6 步全部执行 ✅  
  - 第 1 步：5 个核心文件读取确认 ✅  
  - 第 2 步：已填字段清单 / 待补字段清单 / 画像完整度 45% ✅  
  - 第 3 步：5 个追问（Q1 项目进展、Q2 Python 边界、Q3 投递时间线、Q4 实习经历、Q5 时间分布）✅  
  - 第 4 步：岗位方向初筛（主方向 = Agent 应用工程）✅  
  - 第 5 步：起步建议 + 文件写入提示 ✅  
  - 第 6 步：Mode A 自动写回 user_profile.md ✅  
- **截图**：待用户补充  
  
### 5.2 job_match 流程 ✅  
- **验证日期**：2026-04-21  
- **触发指令**：`按 job_match_prompt.md 执行一次完整的岗位匹配分析`  
- **测试 JD**：  
  1. ByteIntern 大模型应用开发实习生-TikTok用户增长（北京）  
  2. 蔚来汽车 大模型应用开发实习生-VAS（上海）  
- **输出验证**：  
  - 硬门槛 6 项 ✓/✗/? 判定 ✅  
  - 软性维度 6 项 命中/部分命中/未命中 判定 ✅  
  - 5.1 三档结论 + 一句话理由 ✅  
  - 5.2 样本定位（能力上限测试样本 / 短期可投样本）✅  
  - 缺口清单带 [致命度: 高/中/低] + [短期性: 可补/不可补] ✅  
  - 下一步建议（3 条带主线标签）✅  
- **截图**：待用户补充  
  
### 5.3 plan 流程 ⏳ 待执行  
- **触发指令**：`请按 plan_prompt.md 执行路线规划。缺口清单如下：[粘贴上一步缺口段]`  
- **输出验证**：4 周周计划 / Week 1 7 天日计划 / 长期跟进 / 风险监控  
- **状态**：plan_prompt.md 已上传，尚未执行端到端验证  
  
### 5.4 summary 流程 ⏳ 待执行  
- **触发指令**：`请按 summary_prompt.md 复盘 2026-04-21`  
- **输出验证**：留痕 A/B/C 分类 / 偏离度（三档） / 方向对齐（四档） / 风险与亮点 / 明日建议  
- **状态**：summary_prompt.md 已上传，尚未执行端到端验证  
  
### 5.5 Agent Demo 代码验证 ✅  
- **验证日期**：2026-04-16  
- **文件**：agent_demo.py + tools.py  
- **测试内容**：4 级阶梯测试全部通过  
  - 阶梯 1：无工具闲聊 ✅  
  - 阶梯 2：单工具调用 ✅  
  - 阶梯 3：带参数工具调用 ✅  
  - 阶梯 4：多工具链式调用（get_current_time + calculator 串联完成"现在到某日期还剩几天"）✅  
- **安全验证**：Python ast 白名单解析阻止 `__import__` 代码注入 ✅  
- **截图**：待用户补充  
  
---  
  
## 6. 定时任务配置（B4）  
  
| 触发时间 | 指令 | 写回文件 | 配置状态 |  
|---|---|---|---|  
| 每日 09:00 | `请按 daily_log.md 模板生成今日计划，主线标签依据最近一次 /plan 的 Week 1 排期` | daily_log.md 当日"今日计划"区块 | ⏳ 待配置 |  
| 每日 21:00 | `请按 summary_prompt.md 复盘今天` | daily_log.md 当日"偏离度判断 / 明日建议"区块 | ⏳ 待配置 |  
| 每周日 21:30 | `请按 summary_prompt.md 跑本周复盘` | daily_log.md 追加周度复盘块 | ⏳ 待配置 |  
  
- **配置入口**：待补充（截图）  
- **时区**：Asia/Shanghai（JVS Claw 会话时区已确认）  
  
---  
  
## 7. 已知限制 / 踩坑  
  
- **工作空间文件写入**：首次 `write` 工具调用未生效（目录创建成功但文件为空），重新 `write` 后正常  
- **edit 工具匹配**：oldText 必须与原文完全一致（包括空格、换行），否则匹配失败。遇到部分 edit 失败时，改用完整文件 `write` 覆盖解决  
- **上下文窗口**：约 13.1k tokens，长对话后需压缩 / 开启新 session  
- **定时任务**：当前未配置（cron jobs 列表为空），需用户在 JVS Claw UI 侧手动设置  
- **match_job.py 已知小 bug（已修复）**：`check_language()` 关键词漏了"英文"，已修复  
- **match_job.py 已知待优化（V1.5）**：`soft_work_mode()` 未处理"不限"短路逻辑  
- **DEMO_PROFILE 与 user_profile.md 不同步**：MVP 版手工维护字典，V1.5 需实现 Markdown 解析自动同步  
  
---  
  
## 8. 写进简历的关键要点  
  
> 把 OfferClaw 写进简历的项目栏时可强调：  
>  
> - **完整闭环**：画像 → 匹配 → 规划 → 执行 → 复盘 五大模块全部交付  
> - **工程严谨**：每个模块都有 Prompt 契约（.md）+ 代码实现（.py）+ 测试验证  
> - **平台落地**：在 JVS Claw 平台真实部署，含文件空间 + 定时任务 + 对话交互  
> - **可解释性**：所有匹配结论引用 user_profile.md 具体章节，无玄学综合分，无录用概率判断  
> - **Agent 工程能力**：从零实现 AI Agent 完整链路（用户提问 → LLM 判断是否调工具 → 工具执行 → LLM 整合结果 → 回复），走通 function calling / tool loop / 多轮对话记忆 / 安全沙箱（ast 白名单解析）  
> - **Prompt 工程**：设计 4 个 Prompt 契约文件（onboarding / job_match / plan / summary），含硬性约束、输出结构模板、三档结论规则、证据等级制度  
