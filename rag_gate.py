# -*- coding: utf-8 -*-
"""rag_gate.py — 知识库优先的「带门槛」RAG 问答（CLI 与 Web 共用）

把"命中才答、未命中坦白"的硬门槛逻辑收口到一处，供：
  - offerclaw_cli.py query（微信路径）
  - rag_api.py /api/query（Web UI 路径）
两条入口共用，保证行为完全一致。

门槛策略（基于 text-embedding-v4 标定）：
  - 强向量命中：最近邻距离 <= STRONG → in_kb
  - 词面救回：STRONG < dist <= RESCUE 且查询关键词在片段里字面出现 → in_kb
    （解决 "react" 与库内 "ReAct" 向量距离偏大但字面一致的语义鸿沟）
  - 否则 → in_kb=False，坦白"知识库暂无"，绝不用通用知识杜撰
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

RAG_RELEVANCE_MAX_DIST = float(os.environ.get("RAG_RELEVANCE_MAX_DIST", "0.92"))
# 词面救回上限：1.15（标定后收紧，原 1.20）。
# 理由：真需要救回的"react→ReAct"在 1.0155；负样本（Vue3/Spring/Git 仅被提及）在 1.16+。
# 1.15 落在两者之间，既保住 react，又挡掉"Git"这类仅被提及词的误命中。
RAG_LEXICAL_RESCUE_DIST = float(os.environ.get("RAG_LEXICAL_RESCUE_DIST", "1.15"))
# 弱相关上限：未命中但 dist 在此内的片段，作为"可能相关背景"喂给兜底回答；
# 超过则视为完全无关，兜底走纯通用知识。
RAG_WEAK_CONTEXT_DIST = float(os.environ.get("RAG_WEAK_CONTEXT_DIST", "1.30"))
# RAG 合成用更快的模型（grounded 总结/兜底都够用），默认 qwen-turbo；可用 RAG_SYNTH_MODEL 覆盖。
RAG_SYNTH_MODEL = os.environ.get("RAG_SYNTH_MODEL", "qwen-turbo")

FALLBACK_LABEL = "⚠️ 此问题知识库未直接覆盖，以下为通用知识回答（未经知识库验证，仅供参考）：\n\n"


def query_keywords(question: str) -> list:
    """抽取区分性英文/数字 token（len>=3）用于词面救回；中文交给向量。"""
    import re
    stop = {"什么", "怎么", "如何", "为什么", "the", "and", "what", "how", "why", "is", "are"}
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9]{2,}", question)
    return [t.lower() for t in tokens if t.lower() not in stop]


def lexical_hit(keywords: list, chunks: list) -> bool:
    if not keywords:
        return False
    blob = " ".join(chunks).lower()
    return any(kw in blob for kw in keywords)


def _chat(messages: list, max_tokens: int = 800):
    """用 RAG 合成模型（默认 qwen-turbo，更快）调一次 LLM；无 key 返回 None。"""
    import requests
    from day1_api_starter import get_llm_config, build_zhipu_jwt, load_local_env
    load_local_env()
    cfg = get_llm_config()
    api_key = cfg["api_key"]
    if not api_key:
        return None
    bearer = build_zhipu_jwt(api_key) if cfg["is_zhipu"] else api_key
    model = cfg["model"] if cfg.get("is_zhipu") else RAG_SYNTH_MODEL  # 智谱用其默认，其它用快模型
    payload = {"model": model, "messages": messages, "temperature": 0.2, "max_tokens": max_tokens}
    if cfg.get("reasoning_effort"):
        payload["reasoning_effort"] = cfg["reasoning_effort"]
    resp = requests.post(
        f"{cfg['api_base']}/chat/completions",
        headers={"Authorization": f"Bearer {bearer}", "Content-Type": "application/json"},
        json=payload, timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"].get("content", "") or ""


def synthesize_grounded_answer(question: str, chunks: list):
    """命中知识库：**仅基于检索片段**合成答案（不得用资料外知识）。无 key 返回 None。"""
    return _chat(_grounded_messages(question, chunks))


def synthesize_fallback_answer(question: str, weak_chunks: list):
    """未命中知识库：用 LLM 通用知识 + 项目先验 + 弱相关片段（若有）生成答案。无 key 返回 None。

    外层会在答案前加 FALLBACK_LABEL 明确标注非知识库内容。
    """
    return _chat(_fallback_messages(question, weak_chunks))


def _chat_stream(messages: list, max_tokens: int = 800):
    """流式版 _chat：逐 token yield。无 key 时不产出任何 token。"""
    import json as _json
    import requests
    from day1_api_starter import get_llm_config, build_zhipu_jwt, load_local_env
    load_local_env()
    cfg = get_llm_config()
    api_key = cfg["api_key"]
    if not api_key:
        return
    bearer = build_zhipu_jwt(api_key) if cfg["is_zhipu"] else api_key
    model = cfg["model"] if cfg.get("is_zhipu") else RAG_SYNTH_MODEL
    payload = {"model": model, "messages": messages, "temperature": 0.2,
               "max_tokens": max_tokens, "stream": True}
    if cfg.get("reasoning_effort"):
        payload["reasoning_effort"] = cfg["reasoning_effort"]
    with requests.post(f"{cfg['api_base']}/chat/completions",
                       headers={"Authorization": f"Bearer {bearer}"},
                       json=payload, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        for raw in resp.iter_lines(decode_unicode=True):
            if not raw or not raw.startswith("data: "):
                continue
            chunk = raw[6:]
            if chunk.strip() == "[DONE]":
                break
            try:
                delta = _json.loads(chunk)["choices"][0].get("delta", {}).get("content", "")
                if delta:
                    yield delta
            except Exception:
                continue


def _retrieve_and_classify(question: str, top_k: int = 5) -> dict:
    """检索 + 门槛判定（命中/未命中），返回决策 + 片段，供流式/非流式共用。"""
    import chromadb
    from rag_tools import get_collection_name, get_embeddings_batch

    client = chromadb.PersistentClient(path=os.path.join(BASE_DIR, "chroma_db"))
    col = client.get_collection(get_collection_name())
    emb = get_embeddings_batch([question])
    res = col.query(query_embeddings=emb, n_results=top_k,
                    include=["documents", "metadatas", "distances"])
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0]

    best = dists[0] if dists else 99.0
    keywords = query_keywords(question)
    rescue_chunks = [d for d, dist in zip(docs, dists) if dist <= RAG_LEXICAL_RESCUE_DIST]
    lexical_rescued = best <= RAG_LEXICAL_RESCUE_DIST and lexical_hit(keywords, rescue_chunks)
    in_kb = bool(docs) and (best <= RAG_RELEVANCE_MAX_DIST or lexical_rescued)

    if in_kb:
        cutoff = RAG_RELEVANCE_MAX_DIST if best <= RAG_RELEVANCE_MAX_DIST else RAG_LEXICAL_RESCUE_DIST
        relevant = [(d, m) for d, m, dist in zip(docs, metas, dists) if dist <= cutoff]
        chunks = [d for d, _m in relevant]
        sources = sorted({(m or {}).get("source", "?") for _d, m in relevant})
        matched_by = "vector" if best <= RAG_RELEVANCE_MAX_DIST else "lexical_rescue"
    else:
        chunks = [d for d, dist in zip(docs, dists) if dist <= RAG_WEAK_CONTEXT_DIST]  # 弱相关背景
        sources = []
        matched_by = None
    return {"in_kb": in_kb, "chunks": chunks, "sources": sources,
            "matched_by": matched_by, "best": best, "has_dists": bool(dists)}


def gated_query_stream(question: str, top_k: int = 5):
    """流式版 gated_query：先 yield 一个 meta 事件，再逐 token yield delta，最后 done。

    事件形如：{"type":"meta", in_kb, mode, sources, matched_by, best_distance}
              {"type":"delta", "text": token}
              {"type":"done"}
    """
    try:
        from rag_tools import has_embedding_api_key
        if not has_embedding_api_key():
            yield {"type": "meta", "in_kb": False, "mode": "general_fallback",
                   "sources": [], "matched_by": None, "best_distance": None}
            yield {"type": "delta", "text": FALLBACK_LABEL}
            for tok in _chat_stream(_fallback_messages(question, [])):
                yield {"type": "delta", "text": tok}
            yield {"type": "done"}
            return

        g = _retrieve_and_classify(question, top_k)
        mode = "kb_grounded" if g["in_kb"] else "general_fallback"
        yield {"type": "meta", "in_kb": g["in_kb"], "mode": mode,
               "sources": g["sources"], "matched_by": g["matched_by"],
               "best_distance": round(g["best"], 4) if g["has_dists"] else None}

        if g["in_kb"]:
            msgs = _grounded_messages(question, g["chunks"])
        else:
            yield {"type": "delta", "text": FALLBACK_LABEL}
            msgs = _fallback_messages(question, g["chunks"])
        for tok in _chat_stream(msgs):
            yield {"type": "delta", "text": tok}
        yield {"type": "done"}
    except Exception as e:
        yield {"type": "meta", "in_kb": False, "mode": "general_fallback",
               "sources": [], "matched_by": None, "best_distance": None}
        yield {"type": "delta", "text": FALLBACK_LABEL + f"（检索异常：{e}）"}
        yield {"type": "done"}


def _grounded_messages(question: str, chunks: list) -> list:
    context = "\n\n".join(f"[资料{i+1}]\n{c}" for i, c in enumerate(chunks))
    return [
        {"role": "system", "content": (
            "你是 OfferClaw 的知识库问答助手。**只能基于下面提供的「资料」回答**，"
            "严禁使用资料之外的知识或常识补充。若资料不足以回答，直接说明资料不足。"
            "回答简洁、分点，末尾用一行列出引用的资料编号。\n\n" + context
        )},
        {"role": "user", "content": question},
    ]


def _fallback_messages(question: str, weak_chunks: list) -> list:
    bg = ""
    if weak_chunks:
        bg = ("\n\n以下是知识库里**可能相关但未必准确**的片段，可参考其中与项目相关的部分：\n"
              + "\n\n".join(f"[背景{i+1}]\n{c}" for i, c in enumerate(weak_chunks)))
    return [
        {"role": "system", "content": (
            "你是 OfferClaw 的求职/学习助手。用户的问题在策展知识库里没有直接覆盖。"
            "请结合你的通用知识、以及（若给出）下面的项目背景片段，给出有帮助、准确、简洁的回答；"
            "涉及大模型应用工程师方向时尽量贴合该语境。不要假装这是知识库的权威答案。" + bg
        )},
        {"role": "user", "content": question},
    ]


def gated_query(question: str, top_k: int = 5) -> dict:
    """知识库优先的问答（两段式）：

    - **命中**（强向量 / 词面救回）→ 仅基于 KB 片段合成答案 + 标出处，mode=kb_grounded。
    - **未命中** → 用 LLM 通用知识 + 项目先验 + 弱相关片段生成答案，开头加"非知识库"标注，
      mode=general_fallback。即始终给有用答案，但 KB-grounded 与否清晰区分。

    返回 dict：{query, in_kb, mode, answer, sources, matched_by, best_distance, retrieval_count}
    任何异常都安全降级为 general_fallback（不崩）。
    """
    try:
        import chromadb
        from rag_tools import get_collection_name, get_embeddings_batch, has_embedding_api_key

        if not has_embedding_api_key():
            ans = synthesize_fallback_answer(question, [])
            return {"query": question, "in_kb": False, "mode": "general_fallback",
                    "answer": FALLBACK_LABEL + (ans or "（无 LLM key，无法作答）"),
                    "sources": [], "matched_by": None, "best_distance": None, "retrieval_count": 0}

        client = chromadb.PersistentClient(path=os.path.join(BASE_DIR, "chroma_db"))
        col = client.get_collection(get_collection_name())
        emb = get_embeddings_batch([question])
        res = col.query(query_embeddings=emb, n_results=top_k,
                        include=["documents", "metadatas", "distances"])
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]

        best = dists[0] if dists else 99.0
        keywords = query_keywords(question)
        rescue_chunks = [d for d, dist in zip(docs, dists) if dist <= RAG_LEXICAL_RESCUE_DIST]
        lexical_rescued = best <= RAG_LEXICAL_RESCUE_DIST and lexical_hit(keywords, rescue_chunks)
        in_kb = bool(docs) and (best <= RAG_RELEVANCE_MAX_DIST or lexical_rescued)

        if in_kb:
            cutoff = RAG_RELEVANCE_MAX_DIST if best <= RAG_RELEVANCE_MAX_DIST else RAG_LEXICAL_RESCUE_DIST
            relevant = [(d, m) for d, m, dist in zip(docs, metas, dists) if dist <= cutoff]
            chunks = [d for d, _m in relevant]
            sources = sorted({(m or {}).get("source", "?") for _d, m in relevant})
            answer = synthesize_grounded_answer(question, chunks)
            if answer is None:
                answer = "（无 LLM key，返回原始片段）\n\n" + "\n---\n".join(c[:300] for c in chunks)
            return {
                "query": question, "in_kb": True, "mode": "kb_grounded",
                "matched_by": "vector" if best <= RAG_RELEVANCE_MAX_DIST else "lexical_rescue",
                "answer": answer, "sources": sources,
                "best_distance": round(best, 4), "retrieval_count": len(chunks),
            }

        # 未命中 → 兜底：弱相关片段（dist 在弱相关带内）+ 通用知识
        weak = [d for d, dist in zip(docs, dists) if dist <= RAG_WEAK_CONTEXT_DIST]
        ans = synthesize_fallback_answer(question, weak)
        if ans is None:
            ans = "（无 LLM key，无法作答）"
        return {
            "query": question, "in_kb": False, "mode": "general_fallback",
            "matched_by": None, "answer": FALLBACK_LABEL + ans, "sources": [],
            "best_distance": round(best, 4) if dists else None,
            "retrieval_count": 0,
        }
    except Exception as e:
        try:
            ans = synthesize_fallback_answer(question, [])
        except Exception:
            ans = None
        return {"query": question, "in_kb": False, "mode": "general_fallback",
                "answer": FALLBACK_LABEL + (ans or f"（检索异常：{e}）"),
                "sources": [], "matched_by": None, "best_distance": None, "retrieval_count": 0}
