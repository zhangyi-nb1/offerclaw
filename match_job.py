# -*- coding: utf-8 -*-
"""
OfferClaw · 岗位匹配最小规则版 (match_job.py)

作用：
    V1 比赛版的最小可运行岗位匹配脚本。与 job_match_prompt.md 共用同一套
    输出契约（来自 target_rules.md §6），保证 Prompt 版与 Python 版逻辑一致。

原则：
    - 只做规则式判断，禁止玄学综合打分
    - 三层逻辑：硬门槛 → 软性维度 → 三档结论 + 缺口清单
    - 无数据库、无爬虫、无复杂评分模型、无第三方依赖

使用：
    直接运行：
        python match_job.py
    输出会打印一份完整匹配报告（DEMO_PROFILE + DEMO_JD）。
    测试别的 JD：修改本文件底部的 DEMO_JD 字符串即可。
"""

import re
import sys
from dataclasses import dataclass, field
from typing import List, Dict, Optional


# =====================================================
# 常量：与 target_rules.md §3 / §4 一一对应
# =====================================================

# 学历数值：越大越高
EDU_LEVEL = {"专科": 1, "本科": 2, "学士": 2, "硕士": 3, "博士": 4}

# OfferClaw 主方向关键词（profile §2 主方向）
MAIN_DIRECTION_KWS = [
    "agent", "llm", "大模型", "prompt", "workflow",
    "ai 应用", "智能体", "ai应用",
]

# 派生方向关键词（profile §2 派生方向）
SUB_DIRECTION_KWS = ["python 后端", "数据处理", "算法落地"]

# AI 应用友好专业（当 JD 写"相关专业"时的扩展集合）
AI_FRIENDLY_MAJORS = [
    "计算机", "软件", "通信", "电子", "信息",
    "人工智能", "数据", "自动化",
]

# 常见城市列表（用于地域识别，MVP 版手写，后续可扩）
COMMON_CITIES = [
    "北京", "上海", "深圳", "广州", "杭州",
    "成都", "南京", "武汉", "西安", "苏州", "天津",
]

# 质性经验要求关键词（JD 不给具体 N 年，但显式要求项目/实习/工程经验）
# 当 JD 出现这类关键词 且 profile §4/§7 为空时，判硬门槛 ✗
# 发现来源：JD #6（蔚来 VAS）"在校期间有相关项目经验"——旧版仅匹配 "N 年" 模式会漏掉
QUALITATIVE_EXP_KEYWORDS = [
    "项目经验", "相关经验", "落地经验", "实战经验",
    "开发经验", "工程经验", "应用经验", "相关项目",
    "项目落地", "应用落地",
]

# 出现在关键词后方 30 字符内的"软化词"——会把"质性要求"降级为"加分项"而非硬要求
# 例如 "有项目经验者优先" 的 "优先" 命中软化词 → 判加分项，不触发硬门槛 ✗
SOFTEN_HINTS = ["优先", "加分", "bonus", "更佳", "为佳", "者优先"]


# =====================================================
# 数据结构
# =====================================================

@dataclass
class CheckResult:
    """单项检查结果。
    status 取值：
      - 硬门槛：'✓' / '✗' / '?'
      - 软性维度：'命中' / '部分命中' / '未命中' / '?'
    reason 必须引用 profile 章节或说明"信息不足"。
    """
    name: str
    status: str
    reason: str


@dataclass
class MatchReport:
    jd_title: str
    direction: str
    hard_gate: List[CheckResult] = field(default_factory=list)
    soft_dims: List[CheckResult] = field(default_factory=list)
    conclusion: str = ""
    conclusion_reason: str = ""
    gap_list: Dict[str, List[str]] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)


# =====================================================
# 硬门槛检查（6 项）
# =====================================================

def check_education(profile: dict, jd: str) -> CheckResult:
    """学历：JD 要求 vs profile §1 学历层次。"""
    user_edu = profile.get("学历")
    user_level = EDU_LEVEL.get(user_edu, 0)

    # 取 JD 中最低可接受学历（最宽松的那一档）
    if "本科" in jd or "学士" in jd:
        required, req_name = 2, "本科"
    elif "硕士" in jd:
        required, req_name = 3, "硕士"
    elif "博士" in jd:
        required, req_name = 4, "博士"
    else:
        return CheckResult("学历", "?", "JD 未明确学历要求")

    if user_level == 0:
        return CheckResult("学历", "?", "profile §1 学历层次未填")
    if user_level >= required:
        return CheckResult(
            "学历", "✓",
            f"用户 {user_edu} ≥ JD 要求 {req_name}（profile §1）"
        )
    return CheckResult(
        "学历", "✗",
        f"用户 {user_edu} 低于 JD 要求 {req_name}（profile §1）"
    )


def check_major(profile: dict, jd: str) -> CheckResult:
    """专业：JD 列出的专业范围 vs profile §1 专业。"""
    user_major = profile.get("专业") or ""
    if not user_major:
        return CheckResult("专业", "?", "profile §1 专业未填")

    if "不限专业" in jd or "专业不限" in jd:
        return CheckResult("专业", "✓", "JD 明确不限专业")

    # 用户专业字面量直接出现
    if user_major in jd:
        return CheckResult(
            "专业", "✓",
            f"JD 中直接提及 {user_major}（profile §1）"
        )

    # JD 说"相关专业"，且用户专业属于 AI 友好专业集合
    if "相关专业" in jd or "相关方向" in jd:
        for m in AI_FRIENDLY_MAJORS:
            if m in user_major:
                return CheckResult(
                    "专业", "✓",
                    f"{user_major} 属于 AI 友好相关专业（profile §1 + JD '相关专业'）"
                )

    return CheckResult(
        "专业", "?",
        f"JD 未明确是否接受 {user_major}"
    )


def _scan_qualitative_exp(jd: str) -> Optional[str]:
    """扫描 JD 是否存在'真正的硬门槛型'质性经验要求。

    判定规则：
    - 关键词命中 QUALITATIVE_EXP_KEYWORDS 列表
    - 且关键词后方 30 字符窗口内不包含 SOFTEN_HINTS（优先/加分等）
    - 同时满足以上两条 → 视为硬门槛

    返回：命中的关键词字符串；未命中返回 None。
    """
    for kw in QUALITATIVE_EXP_KEYWORDS:
        idx = jd.find(kw)
        if idx == -1:
            continue
        window = jd[idx: idx + len(kw) + 30]
        if any(s in window for s in SOFTEN_HINTS):
            continue  # 命中软化词 → 判为加分项，不算硬门槛
        return kw
    return None


def check_experience(profile: dict, jd: str) -> CheckResult:
    """经验要求：JD 要求 vs profile §4 / §7。

    判断优先级（从高到低）：
      1. 实习岗 + 显式宽松词（不强制 / 不要求） → ✓
      2. 质性经验硬要求（如"相关项目经验"且非加分项）+ profile §4/§7 为空 → ✗
      3. "N 年" 年限匹配 → 按年限与 profile 对比判定
      4. 无年限 + 实习岗 → ✓（宽松默认）
      5. 其他 → ?

    V1 回归来源：JD #6（蔚来 VAS）暴露旧版仅匹配"N 年"模式的盲区，
    导致"在校期间有相关项目经验"被误判为 ✓。本版本通过分支 (2) 修复。
    """
    user_proj = profile.get("项目数量", 0) or 0
    user_intern = profile.get("实习数量", 0) or 0
    user_exp = user_proj + user_intern

    # (1) 实习岗 + 显式宽松词 → 直接 ✓
    if "实习" in jd and ("不强制" in jd or "不要求" in jd):
        return CheckResult("经验", "✓", "JD 明确实习不强制经验要求")

    # (2) 质性经验硬要求（JD 写"相关项目经验"等且非加分项）
    qual_hit = _scan_qualitative_exp(jd)
    if qual_hit and user_exp == 0:
        return CheckResult(
            "经验", "✗",
            f"JD 任职要求显式包含'{qual_hit}'（非加分项），"
            f"profile §4/§7 均为空，无可证明的相关经验"
        )

    # (3) "N 年" 年限匹配
    m = re.search(r"(\d+)\s*年", jd)
    if m:
        required = int(m.group(1))
        if required == 0:
            return CheckResult("经验", "✓", "JD 显式无经验年限要求")
        if user_exp == 0:
            return CheckResult(
                "经验", "✗",
                f"JD 要求 {required} 年经验，profile §4/§7 暂无可证明经验"
            )
        return CheckResult(
            "经验", "?",
            f"JD 要求 {required} 年，用户实际年限需人工核对"
        )

    # (4) 无显式年限 + 实习岗 → 宽松默认 ✓
    if "实习" in jd:
        return CheckResult(
            "经验", "✓",
            "实习岗默认无硬性年限要求（JD 未列质性经验硬要求）"
        )

    # (5) 其他情况
    return CheckResult("经验", "?", "JD 未明确经验要求")


def check_language(profile: dict, jd: str) -> CheckResult:
    """语言：JD 要求 vs profile §9 英语读写 自评。"""
    english_req = any(k in jd for k in [
        "英语", "english", "cet", "托福", "雅思"
    ])
    if not english_req:
        return CheckResult("语言", "✓", "JD 无特殊语言要求")

    user_en = profile.get("英语自评")
    if user_en is None:
        return CheckResult("语言", "?", "profile §9 英语读写 自评未填")

    try:
        lvl = int(user_en)
    except (TypeError, ValueError):
        return CheckResult("语言", "?", "profile §9 英语自评格式异常")

    if lvl >= 3:
        return CheckResult(
            "语言", "✓",
            f"英语自评 {lvl}/5 可覆盖 JD 的阅读/沟通要求（profile §9）"
        )
    return CheckResult(
        "语言", "✗",
        f"英语自评 {lvl}/5 不足以覆盖 JD 要求（profile §9）"
    )


def check_location(profile: dict, jd: str) -> CheckResult:
    """地域：JD 所在地 vs profile §1 所在地 / 可接受工作地域。"""
    user_areas = profile.get("可接受地域") or []
    jd_cities = [c for c in COMMON_CITIES if c in jd]

    if not jd_cities:
        if "远程" in jd:
            return CheckResult("地域", "✓", "JD 支持远程")
        return CheckResult("地域", "?", "JD 未明确工作地点")

    if not user_areas:
        return CheckResult(
            "地域", "?",
            f"profile §1 可接受工作地域未填（JD 地点：{jd_cities}）"
        )

    for c in jd_cities:
        if c in user_areas:
            return CheckResult(
                "地域", "✓",
                f"JD 地点 {c} 在用户可接受地域内（profile §1）"
            )
    return CheckResult(
        "地域", "✗",
        f"JD 地点 {jd_cities} 不在用户可接受地域 {user_areas}（profile §1）"
    )


def check_tech_mainline(profile: dict, jd: str) -> CheckResult:
    """技术主线：JD 是否强制要求用户明确不做的技术栈。"""
    banned = profile.get("明确不做") or []
    if not banned:
        return CheckResult("技术主线", "?", "profile §2 明确不做方向未填")

    jd_lower = jd.lower()
    for b in banned:
        # 取关键词的头部（例：'java 后端' → 'java'）
        key = b.split()[0].lower() if b else ""
        if not key:
            continue
        if key not in jd_lower:
            continue
        # 只有当 JD 把它列为强要求时才算未命中
        strong_hints = [
            f"精通 {key}", f"熟练 {key}", f"{key} 为主",
            f"{key} 开发", f"资深 {key}",
        ]
        if any(h in jd_lower for h in strong_hints):
            return CheckResult(
                "技术主线", "✗",
                f"JD 强制 {b} 主线，与 profile §2 明确不做方向冲突"
            )
    return CheckResult(
        "技术主线", "✓",
        "JD 未强制要求用户排除的技术主线"
    )


# =====================================================
# 软性维度分析（6 项）
# =====================================================

def soft_skill_overlap(profile: dict, jd: str) -> CheckResult:
    """技能重叠：JD 要求技能 vs profile §3 技能清单。"""
    skills = (profile.get("熟练技能") or []) + (profile.get("会用技能") or [])
    if not skills:
        return CheckResult("技能重叠", "?", "profile §3 技能清单为空")

    jd_lower = jd.lower()
    hit = [s for s in skills if s.lower() in jd_lower]
    if len(hit) >= 2:
        return CheckResult(
            "技能重叠", "命中",
            f"JD 命中 {hit}（profile §3）"
        )
    if len(hit) == 1:
        return CheckResult(
            "技能重叠", "部分命中",
            f"JD 只命中 1 项：{hit}（profile §3）"
        )
    return CheckResult(
        "技能重叠", "未命中",
        "profile §3 中的技能在 JD 中均未出现"
    )


def soft_direction(profile: dict, jd: str) -> CheckResult:
    """方向一致度：JD 所属方向 vs profile §2 目标方向。"""
    jd_lower = jd.lower()
    main_hit = [k for k in MAIN_DIRECTION_KWS if k in jd_lower]
    if main_hit:
        return CheckResult(
            "方向一致度", "命中",
            f"JD 出现主方向关键词 {main_hit}（profile §2 主方向）"
        )
    sub_hit = [k for k in SUB_DIRECTION_KWS if k in jd_lower]
    if sub_hit:
        return CheckResult(
            "方向一致度", "部分命中",
            f"JD 出现派生方向关键词 {sub_hit}（profile §2 派生）"
        )
    return CheckResult(
        "方向一致度", "未命中",
        "JD 与 profile §2 求职方向不一致"
    )


def soft_project_fit(profile: dict, jd: str) -> CheckResult:
    """项目契合：profile §4 项目经历 / §7 实习。
    契约：只允许 '命中 / 部分命中 / 未命中' 三值（target_rules.md §4）。
    """
    has_proj = (profile.get("项目数量", 0) or 0) > 0
    has_intern = (profile.get("实习数量", 0) or 0) > 0
    if not has_proj and not has_intern:
        return CheckResult(
            "项目契合", "未命中",
            "profile §4/§7 当前无项目或实习可对标"
        )
    # 有项目或实习但 MVP 不做语义契合度判断，保守给部分命中
    return CheckResult(
        "项目契合", "部分命中",
        "profile §4/§7 存在经历条目，MVP 版暂不做语义匹配，保守估计为部分命中"
    )


def soft_work_mode(profile: dict, jd: str) -> CheckResult:
    """工作性质：JD vs profile §2 工作性质偏好。
    契约：只允许 '命中 / 部分命中 / 未命中' 三值。
    """
    pref = profile.get("工作性质偏好")
    if not pref:
        return CheckResult(
            "工作性质", "部分命中",
            "profile §2 工作性质偏好未填，保守估计为部分命中"
        )
    # 用户明确'不限'时直接命中
    if "不限" in str(pref):
        return CheckResult(
            "工作性质", "命中",
            "profile §2 工作性质偏好为'不限'，JD 任意工作性质均可接受"
        )
    if str(pref) in jd:
        return CheckResult(
            "工作性质", "命中",
            f"JD 符合偏好：{pref}（profile §2）"
        )
    return CheckResult(
        "工作性质", "未命中",
        f"JD 与偏好 {pref} 不一致（profile §2）"
    )


def soft_salary(profile: dict, jd: str) -> CheckResult:
    """薪资：MVP 版不做区间解析。
    契约：只允许 '命中 / 部分命中 / 未命中' 三值。
    MVP 版对薪资一律保守给部分命中，理由中区分'未填'与'未解析'两种情况。
    """
    if not profile.get("期望薪资"):
        return CheckResult(
            "薪资", "部分命中",
            "profile §2 期望薪资未填，MVP 版无法判断匹配度，保守估计为部分命中"
        )
    return CheckResult(
        "薪资", "部分命中",
        "MVP 版暂不做薪资区间解析，需人工核对，保守估计为部分命中"
    )


def soft_location(profile: dict, jd: str) -> CheckResult:
    """地域匹配：复用硬门槛地域检查的结论，映射到软性三值契约。
    硬门槛的 '?' 在软性层映射为 '部分命中'（保守策略）。
    """
    r = check_location(profile, jd)
    status_map = {"✓": "命中", "✗": "未命中", "?": "部分命中"}
    return CheckResult(
        "地域匹配",
        status_map.get(r.status, "部分命中"),
        r.reason,
    )


# =====================================================
# 三档结论与缺口清单
# =====================================================

def decide(hard: List[CheckResult], soft: List[CheckResult]) -> tuple:
    """返回 (conclusion, one_line_reason)。
    规则（target_rules.md §5）：
      - 任一硬门槛 ✗ → 当前暂不建议投递
      - 硬门槛 ? ≤ 1 且软性命中 ≥ 3 → 当前适合投递
      - 软性未命中 ≥ 3 → 当前暂不建议投递
      - 其他 → 中长期可转向
    """
    hard_fail = [r for r in hard if r.status == "✗"]
    hard_unknown = sum(1 for r in hard if r.status == "?")
    soft_hit = sum(1 for r in soft if r.status == "命中")
    soft_fail = sum(1 for r in soft if r.status == "未命中")

    if hard_fail:
        return (
            "当前暂不建议投递",
            f"硬门槛存在 {len(hard_fail)} 项未命中："
            + "；".join(r.name for r in hard_fail),
        )

    if hard_unknown <= 1 and soft_hit >= 3:
        return (
            "当前适合投递",
            f"硬门槛无未命中（信息不足 {hard_unknown} 项），"
            f"软性维度命中 {soft_hit} 项",
        )

    if soft_fail >= 3:
        return (
            "当前暂不建议投递",
            f"软性维度未命中达 {soft_fail} 项，差距较大",
        )

    return (
        "中长期可转向",
        f"硬门槛信息不足 {hard_unknown} 项 / 软性命中 {soft_hit} 项，"
        "建议补齐画像或积累项目后再评估",
    )


def build_gap_list(
    hard: List[CheckResult],
    soft: List[CheckResult],
    profile: dict,
) -> Dict[str, List[str]]:
    gaps = {
        "硬门槛缺口": [],
        "技能缺口": [],
        "经历缺口": [],
    }
    for r in hard:
        if r.status == "✗":
            gaps["硬门槛缺口"].append(f"{r.name}：{r.reason}")
        elif r.status == "?":
            gaps["硬门槛缺口"].append(f"[信息不足] {r.name}：{r.reason}")

    for r in soft:
        if r.status in ("未命中", "部分命中"):
            if r.name == "技能重叠":
                gaps["技能缺口"].append(r.reason)
            elif r.name == "项目契合":
                gaps["经历缺口"].append(r.reason)

    # 画像级硬事实：§4 项目为空直接进经历缺口
    if (profile.get("项目数量", 0) or 0) == 0:
        gaps["经历缺口"].append(
            "profile §4 项目经历为空，需尽快形成 1-2 个可投递项目"
        )
    return gaps


def judge_direction(profile: dict, jd: str) -> str:
    jd_lower = jd.lower()
    if any(k in jd_lower for k in MAIN_DIRECTION_KWS):
        return "主方向"
    if any(k in jd_lower for k in SUB_DIRECTION_KWS):
        return "派生方向"
    return "不考虑"


def build_suggestions(
    report: MatchReport,
    profile: dict,
) -> List[str]:
    """最多 3 条，每条带主线标签。"""
    out = []
    if report.conclusion == "当前适合投递":
        out.append(
            "[投递准备] 准备简历 / 项目概述 / 自我介绍，按缺口清单做最后补强"
        )
    elif report.conclusion == "中长期可转向":
        out.append(
            "[补项目] 将缺口清单转成 daily_log.md 核心任务，"
            "1-2 周内补齐关键经历后再评估"
        )
    else:
        out.append(
            "[岗位调研] 暂不投递，优先修正硬门槛或改换目标方向"
        )

    # 画像级固定建议
    if (profile.get("项目数量", 0) or 0) == 0:
        out.append(
            "[补项目] 在 2026-05-01 前形成至少 1 个可投递项目（profile §4）"
        )

    # 如果技能缺口非空，追加一条补技能
    if report.gap_list.get("技能缺口"):
        out.append(
            "[补技能] 针对技能缺口安排当周学习任务，"
            "每项缺口对应 1 个可交付小产出"
        )

    return out[:3]


# =====================================================
# 主流程
# =====================================================

def run_match(
    profile: dict,
    jd_text: str,
    jd_title: str = "未命名 JD",
) -> MatchReport:
    jd = jd_text  # 保持原文大小写做人读展示
    hard = [
        check_education(profile, jd),
        check_major(profile, jd),
        check_experience(profile, jd),
        check_language(profile, jd),
        check_location(profile, jd),
        check_tech_mainline(profile, jd),
    ]
    soft = [
        soft_skill_overlap(profile, jd),
        soft_direction(profile, jd),
        soft_project_fit(profile, jd),
        soft_work_mode(profile, jd),
        soft_salary(profile, jd),
        soft_location(profile, jd),
    ]
    report = MatchReport(
        jd_title=jd_title,
        direction=judge_direction(profile, jd),
        hard_gate=hard,
        soft_dims=soft,
    )
    report.conclusion, report.conclusion_reason = decide(hard, soft)
    report.gap_list = build_gap_list(hard, soft, profile)
    report.suggestions = build_suggestions(report, profile)
    return report


def format_report(report: MatchReport) -> str:
    """输出结构严格对齐 target_rules.md §6 与 job_match_prompt.md 第 8 步。"""
    lines = []
    lines.append(f"岗位：{report.jd_title}")
    lines.append(f"方向判定：{report.direction}")
    lines.append("")
    lines.append("硬门槛：")
    for r in report.hard_gate:
        lines.append(f"  - {r.name}：{r.status}（{r.reason}）")
    lines.append("")
    lines.append("软性维度：")
    for r in report.soft_dims:
        lines.append(f"  - {r.name}：{r.status}（{r.reason}）")
    lines.append("")
    lines.append(f"结论：{report.conclusion}")
    lines.append(f"一句话理由：{report.conclusion_reason}")
    lines.append("")
    lines.append("缺口清单（喂给路线规划模块）：")
    for category, items in report.gap_list.items():
        lines.append(f"  - {category}：")
        if not items:
            lines.append("      * （无）")
        else:
            for it in items:
                lines.append(f"      * {it}")
    lines.append("")
    lines.append("下一步建议（最多 3 条，每条带主线标签）：")
    for s in report.suggestions:
        lines.append(f"  - {s}")
    return "\n".join(lines)


# =====================================================
# 演示数据（可替换）
# =====================================================

# 对应 user_profile.md 的简化字典镜像。MVP 版手工维护，
# 不做 Markdown 解析（那是 V1.5 工作）。
DEMO_PROFILE = {
    # §1
    "学历": "硕士",
    "专业": "通信工程",
    "所在地": "南京",
    "可接受地域": ["上海", "南京", "苏州", "无锡", "南通", "远程"],
    # §2
    "方向优先级": [
        "Agent 应用工程",
        "AI 应用开发",
        "Prompt / Workflow 工程",
    ],
    # 只放能被 check_tech_mainline 的 b.split()[0].lower() 机制使用的干净 token。
    # profile §2 的第二条 "和目前大模型主线出入大的" 是 meta 规则，
    # 无法转成单 token，在 MVP 规则版里不纳入机读列表，留在 user_profile.md 作人读。
    "明确不做": ["java"],
    "工作性质偏好": "不限",
    "期望薪资": "月薪底薪 3 万，上不封顶（校招口径；实习另档，见 profile §2）",
    # §3
    "熟练技能": ["MATLAB"],
    "会用技能": ["Python"],
    # §4 / §7
    "项目数量": 0,
    "实习数量": 0,
    # §9
    "英语自评": 2,
}


DEMO_JD = """
岗位名称：AI 应用开发工程师（实习）
公司：示例公司
工作地点：北京
学历要求：本科及以上
专业要求：计算机、软件、通信、电子信息等相关专业
经验要求：有 LLM / Agent / Prompt 相关项目经验者优先，实习生不强制要求年限
语言要求：能阅读英文技术文档
技术要求：
  - 熟悉 Python
  - 了解 Prompt 工程 / LangChain / Agent 工作流
  - 加分：有开源项目或个人作品集
工作性质：驻场
"""


def main():
    # Windows 控制台默认 GBK 无法输出 ✓ / ✗，这里显式切到 UTF-8。
    # Python 3.7+ 支持 reconfigure；失败则静默回退（例如被重定向到管道时）。
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    report = run_match(
        DEMO_PROFILE,
        DEMO_JD,
        jd_title="AI 应用开发工程师（实习）",
    )
    print(format_report(report))


if __name__ == "__main__":
    main()
