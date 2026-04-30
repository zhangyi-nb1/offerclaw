# Real JD Reflow — NIO VAS LLM Intern (v2, V3 audit)

- 抓取来源：https://nio.jobs.feishu.cn/index/m/position/7249585265663641912/detail
- 运行时间：2026-05-01
- 入口：/api/flow/run（TestClient in-process）
- skip_llm: True（不依赖 ZHIPU_API_KEY）

## 8 节点 trace
```json
[
  {
    "node": "profile",
    "action": "loaded 13 fields",
    "source": "user_profile.md",
    "ts": "03:42:40"
  },
  {
    "node": "job_input",
    "action": "jd_chars=608",
    "source": "user",
    "ts": "03:42:40"
  },
  {
    "node": "match",
    "action": "conclusion=当前适合投递",
    "source": "match_job.run_match",
    "ts": "03:42:40"
  },
  {
    "node": "gap",
    "action": "total_gaps=2",
    "source": "match_report.gap_list",
    "ts": "03:42:40"
  },
  {
    "node": "plan",
    "action": "4 weeks · skill_gaps=1 exp_gaps=1",
    "source": "gaps",
    "ts": "03:42:40"
  },
  {
    "node": "today",
    "action": "【本次 JD · NIO VAS LLM Intern】结论=当前适合投递，建议今天定稿简历并投出",
    "source": "career_flow.today_node (this-JD override)",
    "ts": "03:42:40"
  },
  {
    "node": "resume",
    "action": "mode=skeleton keywords=12",
    "source": "deterministic",
    "ts": "03:42:40"
  },
  {
    "node": "application_suggest",
    "action": "建议加入 applications.md（状态=待评估 / 投递准备）",
    "source": "match_report.status",
    "ts": "03:42:40"
  }
]
```
## match_report
```json
{
  "status": "当前适合投递",
  "direction": "主方向",
  "summary": "岗位：NIO VAS LLM Intern\n方向判定：主方向\n\n硬门槛：\n  - 学历：✓（用户 硕士 ≥ JD 要求 本科（profile §1））\n  - 专业：✓（通信工程 属于 AI 友好相关专业（profile §1 + JD '相关专业'））\n  - 经验：✓（实习岗默认无硬性年限要求（JD 未列质性经验硬要求））\n  - 语言：✓（JD 无特殊语言要求）\n  - 地域：✓（JD 地点 上海 在用户可接受地域内（profile §1））\n  - 技术主线：✓（JD 未强制要求用户排除的技术主线）\n\n软性维度：\n  - 技能重叠：部分命中（JD 只命中 1 项：['Python']（profile §3））\n  - 方向一致度：命中（JD 出现主方向关键词 ['agent', 'llm', '大模型', 'prompt']（profile §2 主方向））\n  - 项目契合：部分命中（profile §4/§7 存在经历条目，MVP 版暂不做语义匹配，保守估计为部分命中）\n  - 工作性质：命中（profile §2 工作性质偏好为'不限'，JD 任意工作性质均可接受）\n  - 薪资：部分命中（MVP 版暂不做薪资区间解析，需人工核对，保守估计为部分命中）\n  - 地域匹配：命中（JD 地点 上海 在用户可接受地域内（profile §1））\n\n结论：当前适合投递\n一句话理由：硬门槛无未命中（信息不足 0 项），软性维度命中 3 项\n\n缺口清单（喂给路线规划模块）：\n  - 硬门槛缺口：\n      * （无）\n  - 技能缺口：\n      * JD 只命中 1 项：['Python']（profile §3）\n  - 经历缺口：\n      * profile §4/§7 存在经历条目，MVP 版暂不做语义匹配，保守估计为部分命中\n\n下一步建议（最多 3 条，每条带主线标签）：\n  - [投递准备] 准备简历 / 项目概述 / 自我介绍，按缺口清单做最后补强\n  - [补技能] 针对技能缺口安排当周学习任务，每项缺口对应 1 个可交付小产出",
  "gap_list": {
    "硬门槛缺口": [],
    "技能缺口": [
      "JD 只命中 1 项：['Python']（profile §3）"
    ],
    "经历缺口": [
      "profile §4/§7 存在经历条目，MVP 版暂不做语义匹配，保守估计为部分命中"
    ]
  },
  "suggestions": [
    "[投递准备] 准备简历 / 项目概述 / 自我介绍，按缺口清单做最后补强",
    "[补技能] 针对技能缺口安排当周学习任务，每项缺口对应 1 个可交付小产出"
  ]
}
```
## gaps
```json
{
  "硬门槛缺口": [],
  "技能缺口": [
    "JD 只命中 1 项：['Python']（profile §3）"
  ],
  "经历缺口": [
    "profile §4/§7 存在经历条目，MVP 版暂不做语义匹配，保守估计为部分命中"
  ],
  "total": 2
}
```
## today_actions
```json
[]
```
## requires_confirmation
```json
[
  {
    "target_file": "applications.md",
    "suggested_patch": "\n| 2026-05-01 | NIO VAS LLM Intern | （公司）| 待评估 | CareerFlow 自动建议 |",
    "reason": "匹配结论 = 当前适合投递"
  }
]
```
