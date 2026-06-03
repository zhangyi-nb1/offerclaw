import rag_tools


def test_bailian_embedding_collection_name(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "bailian")
    monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-v4")
    monkeypatch.setenv("EMBEDDING_DIMENSIONS", "1024")
    monkeypatch.delenv("RAG_COLLECTION_NAME", raising=False)

    assert rag_tools.get_collection_name() == "offerclaw_bailian_text_embedding_v4_1024"


def test_legacy_zhipu_collection_name(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "zhipu")
    monkeypatch.setenv("EMBEDDING_MODEL", "embedding-3")
    monkeypatch.delenv("RAG_COLLECTION_NAME", raising=False)

    assert rag_tools.get_collection_name() == "offerclaw_docs"


def test_fake_embedding_uses_configured_dimension(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "bailian")
    monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-v4")
    monkeypatch.setenv("EMBEDDING_DIMENSIONS", "1024")

    vec = rag_tools.fake_embedding("hello")

    assert len(vec) == 1024
