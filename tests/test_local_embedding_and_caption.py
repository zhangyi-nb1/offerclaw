# -*- coding: utf-8 -*-
"""本地 embedding provider + 模型相关阈值 + 图转文 纯逻辑离线测试。"""
import os, sys
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
import rag_tools, rag_gate, image_caption as ic


def test_local_provider_config(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "local")
    monkeypatch.setenv("EMBEDDING_MODEL", "BAAI/bge-base-zh-v1.5")
    monkeypatch.setenv("EMBEDDING_DIMENSIONS", "768")
    monkeypatch.delenv("RAG_COLLECTION_NAME", raising=False)
    cfg = rag_tools.get_embedding_config()
    assert cfg["provider"] == "local"
    assert cfg["dimensions"] == 768
    # local 无需 API key
    assert rag_tools.has_embedding_api_key() is True
    assert "local" in rag_tools.get_collection_name()


def test_provider_alias_local():
    assert rag_tools._normalise_provider("bge") == "local"
    assert rag_tools._normalise_provider("sentence-transformers") == "local"


def test_thresholds_per_model(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "local")
    monkeypatch.delenv("RAG_RELEVANCE_MAX_DIST", raising=False)
    th = rag_gate._thresholds()
    assert th["strong"] == 0.85   # 本地 bge 标定
    monkeypatch.setenv("EMBEDDING_PROVIDER", "bailian")
    th2 = rag_gate._thresholds()
    assert th2["strong"] == 0.92   # 百炼标定


def test_thresholds_env_override(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "local")
    monkeypatch.setenv("RAG_RELEVANCE_MAX_DIST", "0.70")
    assert rag_gate._thresholds()["strong"] == 0.70


def test_resolve_image_http_passthrough():
    kind, val, key = ic._resolve_image("https://x.com/a.png", "docs/a.md")
    assert kind == "url" and val == "https://x.com/a.png"


def test_resolve_image_missing_local():
    kind, val, key = ic._resolve_image("不存在.png", "docs/a.md")
    assert kind is None


def test_caption_enabled_off_by_default(monkeypatch):
    monkeypatch.delenv("IMAGE_CAPTION", raising=False)
    assert ic.caption_enabled() is False
