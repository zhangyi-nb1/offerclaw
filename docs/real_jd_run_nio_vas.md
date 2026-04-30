# 真实 JD 端到端验证：蔚来 NIO · 大模型应用开发实习生（VAS）

> 抓取时间：2026-04-30
> 来源：https://nio.jobs.feishu.cn/index/m/position/7249585265663641912/detail
> 来源类型：official · 可信度：A
> JD 抽取规模：677 字符（Playwright 渲染后）
> 注意：OfferClaw 仅做半自动抽取：不登录、不批量、不自动投递。最终录入 applications.md 需用户确认。

---

## 一、JD 关键信息（discover 抽取）

- **抓到的技能关键词**：Python, RAG, LangGraph, LlamaIndex, FastAPI, Embedding, LoRA, Prompt, MCP, Agent
- **职责段长度**：307 字
- **要求段长度**：302 字

> Feishu Jobs SPA 用文字段落而非"公司：xxx"键值结构，所以 company/title/location 字段为空，但 jd_text + skills_detected 已足够喂给 match_job。

---

## 二、CareerFlow 8 节点全 trace

| # | 节点 | 状态 |
|---|---|---|
| 1 | `profile` | ✅ done |
| 2 | `job_input` | ✅ done |
| 3 | `match` | ✅ done |
| 4 | `gap` | ✅ done |
| 5 | `plan` | ✅ done |
| 6 | `today` | ✅ done |
| 7 | `resume` | ✅ done |
| 8 | `application_suggest` | ✅ done |

---

## 三、匹配结论（关键）

| 字段 | 值 |
|---|---|
| **status** | **当前适合投递** |
| **direction** | **主方向** |
| **缺口总数** | 2 |
| **建议条数** | 2 |

### 缺口清单
- **技能缺口** (1)：JD 只命中 1 项：['Python']（profile §3）
- **经历缺口** (1)：profile §4/§7 存在经历条目，MVP 版暂不做语义匹配，保守估计为部分命中

### Match summary（前 800 字）

```
岗位：蔚来 NIO · 大模型应用开发实习生 (VAS)
方向判定：主方向

硬门槛：
  - 学历：✓（用户 硕士 ≥ JD 要求 本科（profile §1））
  - 专业：✓（通信工程 属于 AI 友好相关专业（profile §1 + JD '相关专业'））
  - 经验：✓（实习岗默认无硬性年限要求（JD 未列质性经验硬要求））
  - 语言：✓（JD 无特殊语言要求）
  - 地域：✓（JD 地点 上海 在用户可接受地域内（profile §1））
  - 技术主线：✓（JD 未强制要求用户排除的技术主线）

软性维度：
  - 技能重叠：部分命中（JD 只命中 1 项：['Python']（profile §3））
  - 方向一致度：命中（JD 出现主方向关键词 ['agent', 'llm', '大模型', 'prompt']（profile §2 主方向））
  - 项目契合：部分命中（profile §4/§7 存在经历条目，MVP 版暂不做语义匹配，保守估计为部分命中）
  - 工作性质：命中（profile §2 工作性质偏好为'不限'，JD 任意工作性质均可接受）
  - 薪资：部分命中（MVP 版暂不做薪资区间解析，需人工核对，保守估计为部分命中）
  - 地域匹配：命中（JD 地点 上海 在用户可接受地域内（profile §1））

结论：当前适合投递
一句话理由：硬门槛无未命中（信息不足 0 项），软性维度命中 3 项

缺口清单（喂给路线规划模块）：
  - 硬门槛缺口：
      * （无）
  - 技能缺口：
      * JD 只命中 1 项：['Python']（profile §3）
  - 经历缺口：
      * profile §4/§7 存在经历条目，MVP 版暂不做语义匹配，保守估计为部分命中

下一步建议（
```

---

## 四、4 周计划（plan_outline）

- **1**：硬门槛 / 高致命缺口收口
- **2**：技能补强
- **3**：经历补强
- **4**：投递与面试准备

---

## 五、今日建议（today_advice）

- **headline**：【[DEMO] Beta Agent Co · AI Agent 实习生】尽快定稿简历并投出
- **detail**：-

---

## 六、简历骨架（resume_skeleton，skip_llm=True）

- 模式：`skeleton`
- 命中关键词数：**0**
- 命中关键词：

---

## 七、投递建议 + 待确认 patch

- **decision**：建议加入 applications.md（状态=待评估 / 投递准备）
- **reason**：-
- **待确认 patch 数**：1

### Patch 1
```json
{
  "target_file": "applications.md",
  "suggested_patch": "\n| 2026-05-01 | 蔚来 NIO · 大模型应用开发实习生 (VAS) | （公司）| 待评估 | CareerFlow 自动建议 |",
  "reason": "匹配结论 = 当前适合投递"
}
```

---

## 八、结论

- ✅ V3 端到端在**真实公网 JD**上跑通（discover → CareerFlow 8 节点 → 投递建议）
- ✅ 状态驱动判断生效：profile 中"主方向 = AI / LLM 应用"匹配 JD → status=当前适合投递
- ✅ 主流程零落盘：所有写意图收在 `requires_confirmation`，等用户在 `/ui/console` 二次确认后再写入 `applications.md`
- ✅ 端到端无 LLM：`skip_llm=True`，不消耗 API 配额
