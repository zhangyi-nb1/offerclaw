"""产品级 Agent 化指导 §7-§10 验收测试。

覆盖：
- Phase 4: query_builder + rank_candidates (job_discovery)
- Phase 5: build_resume_markdown (resume_builder)
- Phase 6: rag_ingest 配置含 verification source_type
- Phase 7: CareerFlow 能回答 4 个真实使用核心问题
- 新端点：/api/jd/queries, /api/jd/rank, /api/resume/markdown, /ui/console
"""

from __future__ import annotations

import os
import sys

import pytest
from fastapi.testclient import TestClient

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


JD_AI = (
    "岗位名称：大模型应用开发实习生\n公司：示例\n工作地点：上海\n"
    "学历要求：本科及以上\n专业要求：计算机、人工智能\n经验要求：实习\n"
    "技术要求：Python / LangGraph / RAG / FastAPI / Embedding\n工作性质：实习\n"
)
JD_JAVA = (
    "岗位名称：Java 后端开发实习生\n公司：示例\n工作地点：上海\n"
    "学历要求：本科及以上\n经验要求：实习\n"
    "技术要求：精通 Java / SpringBoot / MySQL\n工作性质：日常实习\n"
)


# ============== Phase 4 ==============

def test_phase4_build_search_queries():
    from job_discovery import build_search_queries
    from profile_loader import load_profile
    qs = build_search_queries(load_profile())
    assert 1 <= len(qs) <= 6
    assert all(isinstance(q, str) and q.strip() for q in qs)
    assert any("实习" in q or "校招" in q for q in qs), qs


def test_phase4_rank_candidates_orders_by_status():
    from job_discovery import rank_candidates
    out = rank_candidates([
        {"title": "Java 后端", "jd_text": JD_JAVA},
        {"title": "AI 应用开发", "jd_text": JD_AI},
    ])
    assert len(out) == 2
    assert out[0]["score"] >= out[1]["score"]
    titles = [r["title"] for r in out]
    assert titles[0] == "AI 应用开发", f"AI JD 应排在 Java 之前：{out}"


# ============== Phase 5 ==============

def test_phase5_build_resume_markdown_skip_llm(monkeypatch):
    monkeypatch.delenv("ZHIPU_API_KEY", raising=False)
    from resume_builder import build_resume_markdown
    out = build_resume_markdown(jd_text="", skip_llm=True)
    md = out["resume_md"]
    for must in ("## 求职摘要", "## 技能栏", "## 项目经历", "## 竞赛经历", "## 科研经历"):
        assert must in md, f"简历草稿缺：{must}"
    assert out["sections"] == ["summary", "skills", "project", "competition", "research", "jd_tailored"]
    assert out["skip_llm"] is True


# ============== Phase 6 ==============

def test_phase6_rag_ingest_has_verification_source_type():
    from rag_ingest import DEFAULT_FILES
    paths = {p for p, _ in DEFAULT_FILES}
    types = {t for _, t in DEFAULT_FILES}
    assert "docs/verification_report.md" in paths
    for needed in ("profile", "log", "application", "story", "jd",
                   "resume", "verification"):
        assert needed in types, f"DEFAULT_FILES 缺 source_type={needed}"


# ============== Phase 7：4 个核心问题 ==============

def test_phase7_careerflow_answers_4_core_questions():
    """指导文档 §10.3 验收：CareerFlow 能回答 4 个真实使用问题。"""
    from career_flow import run_career_flow
    out = run_career_flow(JD_AI, jd_title="Phase7 验收 AI", skip_llm=True)

    # Q1: 过去一周做了什么？ → today_advice 应能引用 daily_log / applications
    today = out["today_advice"]
    assert today and (today.get("headline") or today.get("detail") or today.get("next_action"))

    # Q2: 哪个岗位现在最值得投？ → match_report 给三档结论 + direction
    mr = out["match_report"]
    assert mr["status"] in {
        "当前适合投递", "中长期可转向",
        "信息不足，建议补充后再判断", "当前暂不建议投递"}
    assert mr["direction"]

    # Q3: 我今天最该做什么？ → today_advice.headline + 计划首周
    plan = out["plan_outline"]
    assert plan and len(plan) >= 1

    # Q4: 我的简历还缺哪一段？ → gaps + resume_skeleton
    gaps = out["gaps"]
    resume = out["resume_skeleton"]
    assert isinstance(gaps, dict)
    assert resume["mode"] == "skeleton"


# ============== 新端点 e2e ==============

@pytest.fixture(scope="module")
def client():
    from rag_api import app
    return TestClient(app)


def test_endpoint_jd_queries(client):
    r = client.get("/api/jd/queries")
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body["queries"], list) and len(body["queries"]) >= 1
    assert isinstance(body["profile_cities"], list)


def test_endpoint_jd_rank(client):
    r = client.post("/api/jd/rank", json={"candidates": [
        {"title": "Java 后端", "jd_text": JD_JAVA},
        {"title": "AI 应用开发", "jd_text": JD_AI},
    ]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 2
    assert body["ranked"][0]["title"] == "AI 应用开发"


def test_endpoint_resume_markdown(client):
    r = client.post("/api/resume/markdown", json={"jd_text": "", "skip_llm": True})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "## 求职摘要" in body["resume_md"]
    assert body["skip_llm"] is True
    assert body["llm_used"] is False
    assert len(body["sections"]) == 6


def test_endpoint_ui_console(client):
    r = client.get("/ui/console")
    assert r.status_code == 200
    assert b"CareerFlow Stepper" in r.content
    assert b"/api/flow/run" in r.content
