# -*- coding: utf-8 -*-
"""career_flow.py — OfferClaw CareerFlow Orchestrator (产品级 Agent 化指导 §5)

把 ``profile_loader / match_job / career_agent / resume_builder`` 串成
一个 LangGraph 主流程，使 OfferClaw 不再是"功能函数集合"而是
具有真实编排意义的求职 Agent。

设计原则
========
1. **状态驱动**：所有节点只读 ``CareerState``，输出 patch；不写文件。
2. **可解释**：每个节点都把"做了什么 / 为什么 / 来源"写进 ``trace`` 列表。
3. **写入需确认**（§5.5）：任何写入意图都附加到 ``requires_confirmation``
   并标 ``confirm_required=True``，由用户在 UI 上点确认才落盘。
4. **LLM 可插拔**：默认 ``skip_llm=True``，简历节点只产骨架；
   设为 False 时调 ``resume_builder.build_resume_for_jd`` 走 LLM。
   这让测试 / doctor / verify_pipeline 全程不依赖 KEY。
5. **不引入新依赖**：复用项目已有的 ``langgraph``。
"""

from __future__ import annotations

import datetime
import os
import sys
from typing import Any, Optional, TypedDict

from langgraph.graph import END, StateGraph

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from profile_loader import load_profile  # noqa: E402


# =====================================================
# 状态结构
# =====================================================

class CareerState(TypedDict, total=False):
    # 输入
    jd_text: str
    jd_title: str
    skip_llm: bool

    # 中间结果
    profile: dict
    match_report: dict          # {status, direction, gap_list, summary}
    gaps: dict                  # gap_list 副本（方便单独取用）
    plan_outline: list          # 4 周计划骨架（标题 + 每周缺口对齐）
    today_advice: dict          # career_agent.get_today_advice()
    resume_skeleton: dict       # 简历段元信息（不写文件）
    application_suggestion: dict  # 是否建议加入 applications.md

    # 元信息
    trace: list                 # [(node, action, source)]
    requires_confirmation: list  # [{target_file, suggested_patch, reason}]
    errors: list                # [{node, message}]


# =====================================================
# 节点实现
# =====================================================

def _trace(state: CareerState, node: str, action: str, source: str = "") -> None:
    state.setdefault("trace", []).append({
        "node": node, "action": action, "source": source,
        "ts": datetime.datetime.now().strftime("%H:%M:%S"),
    })


def _err(state: CareerState, node: str, msg: str) -> None:
    state.setdefault("errors", []).append({"node": node, "message": msg})


def profile_node(state: CareerState) -> CareerState:
    """读真实 user_profile.md（已经在第一阶段去 DEMO_PROFILE 化）。"""
    p = load_profile()
    state["profile"] = p
    _trace(state, "profile", f"loaded {len(p)-1} fields", source=p.get("_source", ""))
    return state


def job_input_node(state: CareerState) -> CareerState:
    """规范化 JD 输入。当前只做 trim + 长度兜底；URL/抽取留给 job_discovery。"""
    jd = (state.get("jd_text") or "").strip()
    if len(jd) < 30:
        _err(state, "job_input", f"JD 文本过短（{len(jd)} chars），匹配可能不准")
    state["jd_text"] = jd
    state.setdefault("jd_title", "未命名 JD")
    _trace(state, "job_input", f"jd_chars={len(jd)}", source="user")
    return state


def match_node(state: CareerState) -> CareerState:
    """调用现有 ``match_job.run_match``，吐出三档结论 + 缺口。"""
    from match_job import format_report, run_match
    profile = state.get("profile") or load_profile()
    jd = state.get("jd_text", "")
    if not jd:
        _err(state, "match", "jd_text empty")
        state["match_report"] = {}
        return state
    report = run_match(profile, jd, jd_title=state.get("jd_title", "未命名 JD"))
    state["match_report"] = {
        "status": report.conclusion,
        "direction": report.direction,
        "summary": format_report(report),
        "gap_list": report.gap_list or {},
        "suggestions": report.suggestions or [],
    }
    state["gaps"] = report.gap_list or {}
    _trace(state, "match", f"conclusion={report.conclusion}", source="match_job.run_match")
    return state


def gap_node(state: CareerState) -> CareerState:
    """从 match_report 抽缺口，按致命度归档到三类（硬门槛 / 技能 / 经历）。"""
    gaps = state.get("gaps") or {}
    summary = {
        "硬门槛缺口": list(gaps.get("硬门槛缺口", [])),
        "技能缺口": list(gaps.get("技能缺口", [])),
        "经历缺口": list(gaps.get("经历缺口", [])),
    }
    summary["total"] = sum(len(v) for v in summary.values() if isinstance(v, list))
    state["gaps"] = summary
    _trace(state, "gap", f"total_gaps={summary['total']}", source="match_report.gap_list")
    return state


def plan_node(state: CareerState) -> CareerState:
    """4 周计划骨架（不调 LLM）。每周对齐一类缺口，给出可校验的产出物。

    full LLM 计划仍走 ``plan_gen.py``；这里只先给 stepper 用的轮廓。
    """
    gaps = state.get("gaps") or {}
    skill_gaps = gaps.get("技能缺口", [])
    exp_gaps = gaps.get("经历缺口", [])
    hard_gaps = gaps.get("硬门槛缺口", [])

    weeks = [
        {
            "week": 1,
            "focus": "硬门槛 / 高致命缺口收口",
            "items": (hard_gaps[:2] + skill_gaps[:2]) or ["确认 JD 关键技能 + 准备简历草稿"],
            "deliverable": "一份可投简历草稿 + 缺口表",
        },
        {
            "week": 2,
            "focus": "技能补强",
            "items": skill_gaps[:3] or ["巩固 JD 核心技术栈，产出 1 个最小 demo"],
            "deliverable": "1 个最小 demo / 1 篇学习笔记",
        },
        {
            "week": 3,
            "focus": "经历补强",
            "items": exp_gaps[:3] or ["把现有项目向 JD 方向收口（写一段定向项目描述）"],
            "deliverable": "1 个项目段（resume_builder 输出）",
        },
        {
            "week": 4,
            "focus": "投递与面试准备",
            "items": ["简历定稿", "面试故事整理", "准备 1 次模拟面"],
            "deliverable": "applications.md 至少 +1 条已投递",
        },
    ]
    state["plan_outline"] = weeks
    _trace(state, "plan", f"4 weeks · skill_gaps={len(skill_gaps)} exp_gaps={len(exp_gaps)}",
           source="gaps")
    return state


def today_node(state: CareerState) -> CareerState:
    """复用 career_agent.get_today_advice，再叠加"本次 JD 是否优先今天处理"。

    设计：如果本次 CareerFlow 跑出来的 match_report.status 含"适合"，
    则把本次 JD 顶到 headline，避免 Stepper 上"今天该做什么"与本次 JD 无关。
    """
    try:
        from career_agent import get_today_advice
        adv = get_today_advice()
        report = state.get("match_report") or {}
        jd_title = state.get("jd_title", "")
        if jd_title and "适合" in (report.get("status") or ""):
            adv = dict(adv)
            adv["headline"] = f"【本次 JD · {jd_title}】结论={report.get('status')}，建议今天定稿简历并投出"
            adv["next_action"] = (
                f"1) 按缺口清单做最后补强（{state.get('gaps', {}).get('total', 0)} 项）；"
                f"2) 在 /ui/console 确认 patch，写回 applications.md；"
                f"3) 复用 /api/resume/markdown 出一版 JD 定制简历草稿。"
            )
            adv["source"] = "career_flow.today_node (this-JD override)"
        state["today_advice"] = adv
        _trace(state, "today", adv.get("headline", "")[:60],
               source=adv.get("source", "career_agent"))
    except Exception as e:  # pragma: no cover
        _err(state, "today", str(e))
        state["today_advice"] = {}
    return state


def resume_node(state: CareerState) -> CareerState:
    """简历节点：默认产骨架（含命中关键词），skip_llm=False 时才调 LLM。"""
    skip_llm = state.get("skip_llm", True)
    profile = state.get("profile") or {}
    jd = state.get("jd_text", "")
    keywords = _extract_keywords(jd)
    skeleton = {
        "mode": "skeleton" if skip_llm else "llm",
        "keywords_hit": keywords,
        "must_emphasize": [
            k for k in keywords
            if any(k.lower() in s.lower() for s in
                   profile.get("熟练技能", []) + profile.get("会用技能", []))
        ],
        "headline": f"{profile.get('学历', '')} · {profile.get('专业', '')} · "
                    f"目标方向 {(profile.get('方向优先级') or ['未指定'])[0]}",
    }
    if not skip_llm and jd:
        try:
            from resume_builder import build_resume_for_jd
            out = build_resume_for_jd(jd)
            skeleton["llm_md"] = out.get("resume_md", "")
        except Exception as e:
            _err(state, "resume", f"LLM 生成失败：{e}")
            skeleton["llm_md"] = ""
    state["resume_skeleton"] = skeleton
    _trace(state, "resume", f"mode={skeleton['mode']} keywords={len(keywords)}",
           source="resume_builder" if not skip_llm else "deterministic")
    return state


def application_suggest_node(state: CareerState) -> CareerState:
    """根据匹配结论给出"是否加入 applications.md"建议；只产 patch，不写。"""
    report = state.get("match_report") or {}
    status = report.get("status", "")
    title = state.get("jd_title", "未命名 JD")
    suggest = "建议加入 applications.md（状态=待评估 / 投递准备）" if "适合" in status else \
              "暂不建议加入 applications.md（先修硬门槛或换方向）"
    patch = {
        "target_file": "applications.md",
        "suggested_patch": (
            f"\n| {datetime.date.today().isoformat()} | {title} | （公司）| "
            f"待评估 | CareerFlow 自动建议 |"
        ),
        "reason": f"匹配结论 = {status}",
    }
    state["application_suggestion"] = {
        "decision": suggest,
        "status": status,
        "reason": patch["reason"],
        "patch": patch,
    }
    if "适合" in status:
        state.setdefault("requires_confirmation", []).append(patch)
    _trace(state, "application_suggest", suggest, source="match_report.status")
    return state


# =====================================================
# 关键词抽取（极简）
# =====================================================

_KEYWORDS = [
    "python", "java", "fastapi", "langgraph", "langchain", "rag", "agent",
    "embedding", "chromadb", "prompt", "llm", "llamaindex", "mcp",
    "pytorch", "tensorflow", "sql", "mysql", "redis", "docker",
    "matlab", "deep learning", "nlp", "transformer",
    "rlhf", "ppo", "dpo", "sft", "fine-tuning", "微调", "强化学习",
    "coding agent", "代码生成", "工具调用", "多步推理",
    "kaggle", "leetcode", "算法", "数据结构",
]


def _extract_keywords(jd: str) -> list[str]:
    low = jd.lower()
    return [k for k in _KEYWORDS if k in low]


# =====================================================
# Graph 构建
# =====================================================

def build_graph():
    g = StateGraph(CareerState)
    g.add_node("profile", profile_node)
    g.add_node("job_input", job_input_node)
    g.add_node("match", match_node)
    g.add_node("gap", gap_node)
    g.add_node("plan", plan_node)
    g.add_node("today", today_node)
    g.add_node("resume", resume_node)
    g.add_node("application_suggest", application_suggest_node)

    g.set_entry_point("profile")
    g.add_edge("profile", "job_input")
    g.add_edge("job_input", "match")
    g.add_edge("match", "gap")
    g.add_edge("gap", "plan")
    g.add_edge("plan", "today")
    g.add_edge("today", "resume")
    g.add_edge("resume", "application_suggest")
    g.add_edge("application_suggest", END)
    return g.compile()


_COMPILED = None


def get_graph():
    global _COMPILED
    if _COMPILED is None:
        _COMPILED = build_graph()
    return _COMPILED


# =====================================================
# 顶层入口
# =====================================================

def run_career_flow(jd_text: str, *, jd_title: str = "未命名 JD",
                    skip_llm: bool = True) -> dict:
    """对一份 JD 跑完整 CareerFlow，返回最终 state（dict）。"""
    state: CareerState = {
        "jd_text": jd_text,
        "jd_title": jd_title,
        "skip_llm": skip_llm,
        "trace": [],
        "requires_confirmation": [],
        "errors": [],
    }
    final = get_graph().invoke(state)
    return dict(final)


if __name__ == "__main__":
    import json
    demo_jd = (
        "岗位名称：大模型应用开发实习生\n公司：示例\n工作地点：上海\n"
        "学历要求：本科及以上\n专业要求：计算机、人工智能\n经验要求：实习\n"
        "技术要求：Python / LangGraph / RAG / FastAPI / Embedding\n工作性质：实习\n"
    )
    out = run_career_flow(demo_jd, jd_title="DEMO 大模型应用实习")
    # 简化打印
    summary = {
        "status": out.get("match_report", {}).get("status"),
        "direction": out.get("match_report", {}).get("direction"),
        "gap_total": out.get("gaps", {}).get("total"),
        "plan_weeks": [w["focus"] for w in out.get("plan_outline", [])],
        "today": out.get("today_advice", {}).get("headline"),
        "resume_keywords": out.get("resume_skeleton", {}).get("keywords_hit"),
        "application": out.get("application_suggestion", {}).get("decision"),
        "confirm_pending": len(out.get("requires_confirmation", [])),
        "trace_steps": len(out.get("trace", [])),
        "errors": out.get("errors", []),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
