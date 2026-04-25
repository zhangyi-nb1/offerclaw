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


if __name__ == "__main__":
    import json, sys
    jd = sys.stdin.read() if not sys.stdin.isatty() else "公司：测试\n岗位：LLM Agent 实习\n要求：Python / RAG / FastAPI / LangGraph"
    print(json.dumps(build_resume_for_jd(jd), ensure_ascii=False, indent=2))
