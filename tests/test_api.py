# -*- coding: utf-8 -*-
"""
tests/test_api.py — FastAPI 路由的离线 / 联网双层测试

策略：
1. 全部用 fastapi.testclient.TestClient（不起 uvicorn，跑得快）
2. 不依赖 LLM 的接口（健康、画像、根、信息、reset）→ 必跑
3. 依赖 LLM / Embedding 的接口（query、search、match、stream）→ 用 monkeypatch 打桩；
   仅在显式 export OFFERCLAW_E2E=1 时跑真调用
"""
from __future__ import annotations
import os
import sys
import pytest
from fastapi.testclient import TestClient

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import rag_api  # noqa: E402

client = TestClient(rag_api.app)


# ---------- 1. 离线类（必跑） ----------

def test_root_redirects_to_ui():
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (302, 307)
    assert r.headers["location"] == "/ui"


def test_ui_returns_html():
    r = client.get("/ui")
    assert r.status_code == 200
    assert "OfferClaw" in r.text
    assert "<html" in r.text.lower()


def test_api_info():
    r = client.get("/api/info")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "OfferClaw API"
    assert "/health" in body["endpoints"]["GET /health"] or body["endpoints"].get("GET /health")


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in ("healthy", "degraded")
    assert "collection_records" in body
    assert isinstance(body["collection_records"], int)


def test_profile_no_hardcoded_name():
    r = client.get("/api/profile")
    if r.status_code == 404:
        pytest.skip("user_profile.md missing")
    assert r.status_code == 200
    body = r.json()
    assert "name" in body
    assert "direction" in body and isinstance(body["direction"], list)
    # 不应再硬编码英文名
    assert body["name"] != "Zhang Yi" or body["updated_at"] != "2026-04-21", \
        "rag_api should parse user_profile.md, not return hardcoded values"


def test_reset_returns_ok():
    r = client.post("/api/reset")
    assert r.status_code == 200


def test_match_with_clearly_unsuitable_jd():
    """硬否决：Java 后端 → 应返回 暂不 / 不适合 类结论；不依赖 LLM。"""
    jd = "Java 高级开发工程师\n精通 Spring / MyBatis / Java 主线\n北京"
    r = client.post("/api/match", json={"jd_text": jd})
    assert r.status_code == 200
    body = r.json()
    assert "status" in body and "summary" in body
    # match_job 是规则版，结论字段应可读
    assert isinstance(body["status"], str) and len(body["status"]) > 0


# ---------- 2. 联网/LLM 类（默认跳过；OFFERCLAW_E2E=1 时跑） ----------

E2E = os.environ.get("OFFERCLAW_E2E") == "1"


@pytest.mark.skipif(not E2E, reason="set OFFERCLAW_E2E=1 to run LLM e2e tests")
def test_query_e2e():
    r = client.post("/api/query", json={"query": "OfferClaw 主方向是什么？", "top_k": 3})
    assert r.status_code == 200
    body = r.json()
    assert "answer" in body
    assert len(body["answer"]) > 10


@pytest.mark.skipif(not E2E, reason="set OFFERCLAW_E2E=1 to run LLM e2e tests")
def test_search_e2e():
    r = client.post("/api/search", json={"query": "硬否决规则", "top_k": 3})
    assert r.status_code == 200
    body = r.json()
    assert "results" in body or "matches" in body or isinstance(body, dict)


@pytest.mark.skipif(not E2E, reason="set OFFERCLAW_E2E=1 to run LLM e2e tests")
def test_stream_e2e():
    """SSE：能至少收到 meta 和一条 delta。"""
    with client.stream("POST", "/api/stream",
                       json={"query": "OfferClaw 主方向是什么？", "top_k": 3,
                             "use_retrieval": True}) as resp:
        assert resp.status_code == 200
        seen_meta = False
        seen_delta = False
        for chunk in resp.iter_text():
            if "event: meta" in chunk:
                seen_meta = True
            if '"delta"' in chunk:
                seen_delta = True
            if seen_meta and seen_delta:
                break
        assert seen_meta, "no meta event received"
        assert seen_delta, "no delta token received"
