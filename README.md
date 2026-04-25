# OfferClaw

> 一个**长期运行、带状态、围绕单个求职者成长的执行型 AI Agent**。
> 核心闭环：**画像 → 匹配 → 规划 → 执行 → 复盘 → 回到画像更新**。

📚 **快速链接**：[架构图](docs/architecture.md) · [演示流程](docs/demo.md) · [简历介绍](docs/resume_pitch.md) · [面试问答卡](docs/interview_qa.md)

🔢 **当前指标**：RAG Recall@5 = **0.75** · MRR = **0.69** · pytest **17/18** · 6 FastAPI 接口（含 SSE 流式）· 50 chunks 知识库

OfferClaw 不是岗位推荐机器人，也不是简历生成工具。它把求职过程当成一个 *持续运行的工程项目*：用 Prompt 契约定义每一步的输入输出，用规则代码兜底关键判断，用 JVS Claw 的定时任务承载长期执行，用 daily_log 沉淀真实数据并反向修正画像与计划。

当前样本用户：Zhang Yi（东南大学通信工程硕士，2027-07 毕业）。系统设计上面向通用求职者。

---

## 架构总览

```
┌─────────────────────────────────────────────────────────────┐
│  身份与规则层（不变契约）                                     │
│  SOUL.md · target_rules.md · source_policy.md               │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐    ┌──────────────┐
│ ① 画像层      │   │ ② 匹配层      │    │ ③ 规划层      │
│ user_profile │   │ job_match_   │    │ plan_prompt  │
│ onboarding   │   │ prompt + .py │    │ + plan_gen   │
└──────────────┘   └──────────────┘    └──────────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            ▼
                ┌──────────────────────┐
                │ ④ 执行 / ⑤ 复盘层     │
                │ daily_log.md         │
                │ summary_prompt.md    │
                │ （由 JVS Claw 定时任务驱动）│
                └──────────────────────┘
                            │
                            ▼
                ┌──────────────────────┐
                │ 代码实现层            │
                │ agent_demo.py        │
                │ tools.py             │
                │ match_job.py         │
                └──────────────────────┘
```

---

## 五大核心模块

| 模块 | 状态 | 关键文件 |
|---|---|---|
| ① 渐进式用户画像 | ✅ | `user_profile.md` · `onboarding_prompt.md` |
| ② 岗位匹配（双通路：Prompt + 规则） | ✅ | `job_match_prompt.md` · `match_job.py` · `jd_candidates.md` |
| ③ 学习与求职路线规划 | ✅ | `plan_prompt.md` · `plan_gen.py` |
| ④ 执行推进与提醒（JVS Claw 定时） | 🟡 90% | `daily_log.md` |
| ⑤ 学习留痕复盘 | ✅ | `summary_prompt.md` · `source_policy.md` |
| 代码实现（Agent Demo） | ✅ | `agent_demo.py` · `tools.py` · [`AGENT_DEMO.md`](AGENT_DEMO.md) |
| JVS Claw 部署 | 🟡 90% | `deployment.md` |

---

## 技术栈

- **语言**：Python 3.10+
- **LLM**：智谱 GLM-4-Flash（OpenAI 兼容 function calling）
- **依赖**：仅 `requests`，无 LangChain / LlamaIndex / LangGraph
- **认证**：手写 JWT（HS256），纯标准库
- **运行平台**：JVS Claw（文件空间 + 定时任务 + 对话交互）
- **本地命令行**：`python agent_demo.py`

---

## 仓库结构

### Prompt 契约层（`.md`）
- `SOUL.md` — Agent 身份与硬边界
- `target_rules.md` — 求职方向、6 项硬门槛、6 项软性维度、三档结论规则
- `source_policy.md` — 信息源 A/B/C 证据等级
- `onboarding_prompt.md` — 首次启动 6 步流程（双模式写回）
- `job_match_prompt.md` — JD 匹配 9 步契约 + 缺口元数据
- `plan_prompt.md` — 4 周路线规划契约（缺口清单 → 周/日两层计划）
- `summary_prompt.md` — 每日 / 每周复盘契约 + 偏离度判断

### 用户运行时数据
- `user_profile.md` — 12 节画像（实样本 ≈ 75% 完成度）
- `daily_log.md` — 每日计划 / 执行 / 复盘 / 学习留痕
- `jd_candidates.md` — JD 候选池（7 份，用作回归测试）

### 代码实现
- `agent_demo.py` — Agent 主入口（LLM 调用 / 工具循环 / 跨会话 memory）
- `tools.py` — 4 个工具（time / calculator / echo / simple_profile_lookup）
- `match_job.py` — 规则版 JD 匹配引擎
- `plan_gen.py` — 路线规划生成器
- `day1_api_starter.py` — LLM API 调用起点

### 部署 & 项目状态
- [`deployment.md`](deployment.md) — JVS Claw 部署文档
- [`PROJECT_STATUS.md`](PROJECT_STATUS.md) — 项目进度单一事实来源
- [`AGENT_DEMO.md`](AGENT_DEMO.md) — Agent Demo 详细说明（架构图 / 4 级阶梯测试 / 安全设计）

---

## 快速开始

### 本地跑 Agent Demo

```bash
git clone https://github.com/zhangyi-nb1/offerclaw.git
cd offerclaw
pip install requests

# 创建 .env.local（已被 .gitignore 忽略）
echo "ZHIPU_API_KEY=你的智谱密钥" > .env.local

python agent_demo.py
```

详细使用与 4 级阶梯测试见 [`AGENT_DEMO.md`](AGENT_DEMO.md)。

### 在 JVS Claw 上跑

把仓库内所有 `.md` 上传到 JVS Claw 工作空间，配 system prompt = `SOUL.md`，详见 [`deployment.md`](deployment.md)。

---

## 设计亮点（简历向）

- **不依赖 Agent 框架**：无 LangChain / LlamaIndex / LangGraph，从零实现 LLM 调用 + 工具路由 + 多轮对话 + 工具调用循环
- **Prompt + 代码双通路**：核心模块（如 JD 匹配）同时有 Prompt 契约版和规则代码版，互相验证、互为兜底
- **契约式 Prompt 工程**：每个 Prompt 文件都明确定义输入 / 步骤 / 输出 / 禁止条款，可像 API 一样回归测试
- **长期运行**：跨会话 memory（`memory.json`）+ JVS Claw 定时任务承载日维度执行
- **可解释**：所有 JD 匹配判断带 `[致命度]` `[短期性]` 元数据；复盘带"偏离度判断"

---

## 项目状态

详见 [`PROJECT_STATUS.md`](PROJECT_STATUS.md)。

- 项目目标截止日：**2026-05-01**
- 当前阶段：阶段 B 收尾（JVS Claw 部署）→ 阶段 C 启动（GitHub 公开化 + 简历）

---

## License

本仓库为个人作品集项目，未配置开源许可。如需引用或参考，请在 issue 中联系。
