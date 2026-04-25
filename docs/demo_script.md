# OfferClaw · 1 分钟 Demo 演示脚本

> 面试自带笔记本现场演示用。固定一条演示链：  
> **profile → JD URL 抽取 → match → plan → daily task → resume draft**

---

## 演示前准备（30 秒）

```powershell
cd C:\Users\13513\Desktop\XIAGMU
python -m uvicorn rag_api:app --host 127.0.0.1 --port 8765
# 浏览器打开 http://127.0.0.1:8765/ui
```

---

## 演示流程（60 秒口述 + 操作）

### 第 0 秒：开场（5s）
> "我打开 OfferClaw 的本地 UI——这是我自研的求职作战 Agent，每天我自己在用。  
> 顶部黑色这条是 `/api/today` 顶层 Orchestrator 主动给我的今日建议。"

→ 指向页面顶部 **"今日建议"** 黑色横条

---

### 第 5 秒：①用户画像（5s）
> "左上角是我的画像，从 `user_profile.md` 实时读出——硕士、通信、AI 应用方向，
> 已经接了画像层去硬编码改造（V2 阶段一）。"

→ 滚动到 **卡片①**

---

### 第 10 秒：②JD 抽取（自动渲染）（15s）
> "现在我粘一个字节跳动的真实招聘 URL——这是 React 单页应用，普通爬虫拿不到。  
> 我后台用 Playwright 无头 Chromium 自动渲染，20 秒内拿到完整 JD。"

→ 在 **卡片② URL 输入框** 粘贴：  
`https://jobs.bytedance.com/experienced/position/7571365864895072517/detail`  
→ 点 **"从 URL 抽取"** 按钮

> （等 ~20 秒，JD 文本框自动填充）  
> "已抽取：字节 · AI Agent 研发 · 北京 · RAG / LangChain / LangGraph / MCP 全部命中。"

---

### 第 25 秒：③缺口匹配（5s）
> "点开始匹配——`match_job.py` 走规则双通路，硬门槛 6 项 + 软维度 6 项。  
> 输出三档结论 + 结构化缺口清单。"

→ 点 **"开始匹配"** 按钮，3 秒返回结论 + 卡片③缺口清单

---

### 第 30 秒：④计划生成（流式 SSE）（10s）
> "基于③缺口直接生成 4 周计划——这里是 SSE 流式，首 token 1 秒内出现，
> 边生成边显示，最终落盘到 `plans/plan_<时间戳>.md`。"

→ 点卡片④ **"基于③缺口生成计划"**，文字一行行流出来

---

### 第 40 秒：⑥简历定制（流式 SSE）（10s）
> "再针对这份 JD 生成定制简历段——后端有事实清单防止 LLM 幻觉，
> 输出 bullet 版 + 段落版 + 命中分析三段式。"

→ 点卡片⑥ **"针对②JD 生成项目段"**，流式输出

---

### 第 50 秒：⑤每日复盘（5s）
> "卡片⑤是每日执行追踪，写一行就追加到 `daily_log.md`，  
> 顶层 Orchestrator 下次打开会读它来推今日建议——形成闭环。"

→ 在卡片⑤ 输入框写 `完成 LangGraph rerank 实验`，点 **"追加到今日"**

---

### 第 55 秒：收尾（5s）
> "整套系统：**19 个 FastAPI 接口、160 chunks RAG、Recall@5 = 0.96、pytest 37/37**。  
> GitHub 上完整开源（zhangyi-nb1/offerclaw），  
> 这就是我求职用的真实生产工具。"

---

## 演示中可能被问的问题（备答）

| 问题 | 准备好的答案 |
|------|------------|
| 为什么用 LangGraph 而不是 Chain？ | "把控制流显式建模成状态机，便于条件分支与回放调试" |
| 评估集才 50 题不够吧？ | "自建小规模评估集，明确标注非公开 benchmark；下一步是扩到 200 题 + LLM rerank" |
| Playwright 不是太重了吗？ | "首先 requests 快速抓，<300 字才回退 Playwright，对静态页是 1 秒返回" |
| 怎么防 LLM 编造简历？ | "事实清单 + 系统 prompt 强约束，明确列出'不允许说的内容'（无 React/Vue/数据库/自动投递）" |
| 多用户怎么处理？ | "profiles/p*.json 三类 persona 已做参数化回归，docs/persona_compare_report.md 有对比" |

---

## 一行口述备份（30 秒精简版，电话面试用）

> "OfferClaw 是我自研的本地求职 Agent。LangGraph + RAG + FastAPI 全栈打通，
> 19 个接口、160 chunks 知识库、自建 50 题评估集 Recall@5 0.96、pytest 37/37。
> 输入字节这种 SPA 招聘 URL，Playwright 自动渲染，再调智谱 GLM-4 出定制简历段——
> 我每天自己用它选岗位、定计划、做复盘，是我求职过程里最严肃的一份生产系统。"
