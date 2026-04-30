# -*- coding: utf-8 -*-
"""
OfferClaw · JD 定制简历项目段生成器 (resume_builder.py)

V2 阶段五职责：
    输入一份 JD（最好已 discover 抽过），调 LLM 生成针对该 JD 的
    OfferClaw 项目段 markdown（命中关键词 + 量化指标 + STAR 结构）。

设计取舍：
    - 系统 prompt 把"OfferClaw 项目事实清单"完整喂给 LLM（避免幻觉新功能）
    - 用户 prompt 给 JD 关键字段，让 LLM 重排重点（不是重写新项目）
    - 输出两份：resume_bullet（3-5 条简历 bullet） + resume_paragraph（段落式）
    - 复用 plan_gen 的智谱 LLM 通道
"""

import os
from typing import Dict

from plan_gen import call_llm_plain  # 复用智谱 chat 通道


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _read(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


_PROJECT_FACTS = """\
========== OfferClaw 项目事实清单（必须严格基于这些事实，不得新增功能/数字）==========

定位：本地长期运行的求职作战 AI Agent（不是 to-C 产品 / 不是 SaaS）

技术栈（严格命名）：
- Python 3.13 / FastAPI / Pydantic
- 智谱 GLM-4 系列 LLM（chat + tools）
- Embedding：bge-small-zh
- 向量库：ChromaDB（本地持久化，118 chunks）
- 工作流：LangGraph（state machine）
- 评估：自建 50 题 RAG 评估集（自评，非公开 benchmark）

核心能力（已落地的）：
1. Prompt 契约层：source_policy / target_rules / plan_prompt / summary_prompt
2. 用户画像层：user_profile.md + /api/profile（已去硬编码）
3. 双通路岗位匹配：规则 (match_job.py) + LLM (plan_gen.py)
4. 4 周路线规划 / 每日复盘 / 周复盘
5. RAG + ChromaDB（118 chunks，Recall@5 = 0.96 / MRR = 0.74）
6. LangGraph 工作流编排
7. FastAPI 服务（15 路由 含 SSE 流式）
8. 6 卡片本地求职控制台（/ui）
9. 顶层 Orchestrator（career_agent.py），状态机驱动"今日建议"
10. 半自动 JD 抽取（job_discovery.py，规则 + 关键字命中，禁自动爬虫）

工程健康：
- pytest 37/37 通过
- doctor.py 8 项检查 / verify_pipeline.py 6/6
- 自定义 e2e（覆盖 14 路由 → 现 15 路由）

不允许编造的内容：
- 不得说"用户上千人"或"线上服务"
- 不得说"对接了 LinkedIn / 智联 / Boss" 等爬虫
- 不得说"自动投递 / 自动跟进"
- 不得说用了 React / Vue / 数据库 / 登录系统
"""


def build_messages(jd_summary: str, profile: str) -> list:
    system = (
        "你是 OfferClaw 的 简历定制 助手。\n"
        "你只能基于下面给出的【项目事实清单】来重写项目段，不得编造新功能。\n"
        "你的任务：根据这份 JD，重排和强调对该岗位最相关的能力，生成简历项目段。\n\n"
        + _PROJECT_FACTS +
        "\n========== 候选人画像（user_profile.md 节选）==========\n"
        + profile[:3000]
    )
    user = (
        "请根据下面这份 JD 关键信息，输出针对此 JD 的 OfferClaw 项目段。\n"
        "输出格式（严格 markdown）：\n\n"
        "## 简历 bullet 版（3-5 条，每条 ≤ 50 字，命中 JD 关键词）\n"
        "- ...\n\n"
        "## 简历段落版（一段话 ≤ 300 字，含量化指标 + 技术栈）\n"
        "...\n\n"
        "## 命中分析\n"
        "- 命中的 JD 关键词：...\n"
        "- 主动强调的项目能力：...\n"
        "- 刻意弱化的能力（与该 JD 无关）：...\n\n"
        "========== JD 关键信息 ==========\n"
        f"{jd_summary}\n"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def build_resume_for_jd(jd_summary: str, profile_path: str = None) -> Dict[str, str]:
    """生成 JD 定制简历项目段。"""
    api_key = os.getenv("ZHIPU_API_KEY")
    if not api_key:
        raise RuntimeError("ZHIPU_API_KEY 未配置（.env.local 或环境变量）")
    profile = _read(profile_path or os.path.join(BASE_DIR, "user_profile.md"))
    messages = build_messages(jd_summary=jd_summary, profile=profile)
    md = call_llm_plain(messages, api_key, max_tokens=2000)
    return {"resume_md": md, "jd_summary_chars": len(jd_summary)}


# =====================================================================
# Phase 5：Resume Builder 完整化 —— Markdown 简历草稿（无 LLM 也能跑）
# =====================================================================

def _grab_section(text: str, header_pattern: str, max_chars: int = 1500) -> str:
    """从 markdown 中按"## 头"截取一段，截到下一个同级标题。"""
    import re
    m = re.search(rf"(^|\n)#{{1,3}}\s*{header_pattern}[^\n]*\n([\s\S]*?)(?=\n#{{1,3}}\s|\Z)",
                  text, re.IGNORECASE)
    if not m:
        return ""
    body = m.group(2).strip()
    return body[:max_chars]


def build_skill_section(profile: dict) -> str:
    skilled = profile.get("熟练技能") or []
    used = profile.get("会用技能") or []
    out = ["## 技能栏"]
    if skilled:
        out.append("- **熟练**：" + " · ".join(skilled))
    if used:
        out.append("- **会用**：" + " · ".join(used))
    if not skilled and not used:
        out.append("- *待补充*")
    return "\n".join(out)


def build_summary_section(profile: dict) -> str:
    name = profile.get("姓名") or "候选人"
    school = profile.get("学校") or ""
    major = profile.get("专业") or ""
    grad = profile.get("毕业时间") or ""
    direction = "/".join(profile.get("方向优先级") or []) or "AI / LLM 应用方向"
    cities = "/".join(profile.get("可接受地域") or []) or ""
    line = f"{name}，{school}{major}（{grad}）。求职方向：{direction}"
    if cities:
        line += f"，可工作地：{cities}"
    return f"## 求职摘要\n{line}。"


def build_project_section(text_project_status: str, text_one_pager: str) -> str:
    """从 PROJECT_STATUS.md / docs/project_one_pager.md 提取 OfferClaw 项目段。"""
    section = _grab_section(text_one_pager, r"(项目|核心能力|Project)", max_chars=1200)
    if not section:
        section = _grab_section(text_project_status, r"(已完成|当前进度|核心能力|项目)", max_chars=1200)
    body = section or "*未在 PROJECT_STATUS.md / project_one_pager.md 中找到可用段落，请先填写。*"
    return "## 项目经历 — OfferClaw\n" + body


def build_competition_section(text_profile: str) -> str:
    section = _grab_section(text_profile, r"(竞赛|比赛|Competition)")
    return "## 竞赛经历\n" + (section or "*暂无 — 在 user_profile.md 增加 `## 竞赛` 章节即可被识别。*")


def build_research_section(text_profile: str) -> str:
    section = _grab_section(text_profile, r"(科研|Research|论文|Publication)")
    return "## 科研经历\n" + (section or "*暂无 — 在 user_profile.md 增加 `## 科研` 章节即可被识别。*")


def build_jd_tailored_section(jd_summary: str = "") -> str:
    """JD 定制项目段：skip_llm=True 时返回结构骨架。"""
    if not jd_summary.strip():
        return "## JD 定制项目段（占位）\n*未提供 JD，跳过定制段。可调用 `/api/resume/build` 走 LLM 生成。*"
    return ("## JD 定制项目段（骨架）\n"
            "- 候选 JD 关键词命中：参见 `/api/match`\n"
            "- 建议用 `/api/resume/build`（需 ZHIPU_API_KEY）生成 STAR 段落。\n"
            f"- JD 摘要长度：{len(jd_summary)} 字符。")


def build_resume_markdown(jd_text: str = "", profile_path: str | None = None,
                          skip_llm: bool = True) -> dict:
    """聚合生成一份完整 Markdown 简历草稿（默认无 LLM）。"""
    from profile_loader import load_profile
    profile = load_profile(profile_path)
    text_profile = _read(profile_path or os.path.join(BASE_DIR, "user_profile.md"))
    text_status = _read(os.path.join(BASE_DIR, "PROJECT_STATUS.md"))
    text_one_pager = _read(os.path.join(BASE_DIR, "docs", "project_one_pager.md"))

    sections = [
        build_summary_section(profile),
        build_skill_section(profile),
        build_project_section(text_status, text_one_pager),
        build_competition_section(text_profile),
        build_research_section(text_profile),
        build_jd_tailored_section(jd_text),
    ]
    md = "\n\n".join(sections) + "\n"

    out = {
        "resume_md": md,
        "sections": ["summary", "skills", "project", "competition", "research", "jd_tailored"],
        "skip_llm": skip_llm,
        "jd_chars": len(jd_text or ""),
    }
    if not skip_llm and jd_text.strip() and os.getenv("ZHIPU_API_KEY"):
        try:
            tailored = build_resume_for_jd(jd_text, profile_path=profile_path)
            out["resume_md"] = md + "\n\n## JD 定制项目段（LLM 生成）\n" + tailored.get("resume_md", "")
            out["llm_used"] = True
        except Exception as e:
            out["llm_error"] = str(e)
            out["llm_used"] = False
    return out


if __name__ == "__main__":
    import json, sys
    if len(sys.argv) > 1 and sys.argv[1] == "markdown":
        print(build_resume_markdown(skip_llm=True)["resume_md"])
    else:
        jd = sys.stdin.read() if not sys.stdin.isatty() else "公司：测试\n岗位：LLM Agent 实习\n要求：Python / RAG / FastAPI / LangGraph"
        print(json.dumps(build_resume_for_jd(jd), ensure_ascii=False, indent=2))
