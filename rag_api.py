# -*- coding: utf-8 -*-
"""
OfferClaw · FastAPI 服务层

把 RAG 检索、岗位匹配、用户画像查询包装为 HTTP API。
对应蔚来 JD 职责："推进系统原型设计、接口开发和上线部署"

启动方式：
  uvicorn rag_api:app --host 0.0.0.0 --port 8000 --reload

测试方式：
  # 浏览器访问 http://localhost:8000/docs 打开 Swagger UI
  # 或用 curl:
  curl http://localhost:8000/health
  curl -X POST http://localhost:8000/api/query -d '{"query": "我的求职方向"}'
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, FileResponse, RedirectResponse
from pydantic import BaseModel
from typing import Optional
import json
import os
import sys
import datetime

import requests as _requests

# 确保能找到 rag_tools
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from logging_utils import (
    get_logger,
    request_logging_middleware,
    current_request_id,
)

app = FastAPI(
    title="OfferClaw API",
    description="求职作战 Agent 的 HTTP API 接口层（RAG + 岗位匹配 + 用户画像 + SSE 流式）",
    version="1.1.0",
)

app.middleware("http")(request_logging_middleware)

_log = get_logger("offerclaw.api")

# 延迟加载 RAG Agent（避免启动时阻塞）
_rag_agent = None


def get_rag_agent():
    """懒加载 RAG Agent"""
    global _rag_agent
    if _rag_agent is None:
        from rag_agent import RAGAgent
        _rag_agent = RAGAgent()
    return _rag_agent


# =====================================================
# 数据模型
# =====================================================

class QueryRequest(BaseModel):
    query: str
    top_k: int = 5
    use_retrieval: bool = True


class QueryResponse(BaseModel):
    query: str
    answer: str
    retrieval_count: int
    timestamp: str


class MatchRequest(BaseModel):
    jd_text: str


class MatchResponse(BaseModel):
    status: str
    summary: str


class ProfileResponse(BaseModel):
    name: str
    direction: list[str]
    skills_summary: str
    updated_at: str


def _parse_profile(content: str) -> tuple[str, list[str], str, str]:
    """从 user_profile.md 解析关键字段；缺字段时降级为占位值，不再硬编码。"""
    import re
    name = "未填写"
    updated_at = "未知"
    direction: list[str] = []
    skills_summary = "未提取"

    m = re.search(r"姓名[^：:]*[：:]\s*([^\n]+)", content)
    if m:
        name = m.group(1).strip().strip("【】 ")
    m = re.search(r"最近更新时间[：:]\s*([0-9\-/]+)", content)
    if m:
        updated_at = m.group(1).strip()

    block = re.search(r"目标方向[^\n]*\n((?:\s*\d+\.[^\n]+\n?)+)", content)
    if block:
        direction = [
            re.sub(r"^\s*\d+\.\s*", "", ln).strip()
            for ln in block.group(1).splitlines() if ln.strip()
        ]

    sk = re.search(r"##\s*3\.[^\n]*技能[\s\S]{0,800}", content)
    if sk:
        bullets = re.findall(r"-\s*([^\n]+)", sk.group(0))
        if bullets:
            skills_summary = "; ".join(b.strip() for b in bullets[:6])
    return name, direction, skills_summary, updated_at


# =====================================================
# API 路由
# =====================================================

@app.get("/")
async def root():
    """根路径：重定向到友好 UI。"""
    return RedirectResponse(url="/ui")


@app.get("/ui")
async def ui():
    """OfferClaw 控制台（零依赖单页应用）。"""
    return FileResponse(os.path.join(BASE_DIR, "static", "index.html"))


@app.get("/api/info")
async def info():
    """API 元信息（原 / 的内容）。"""
    return {
        "name": "OfferClaw API",
        "version": "1.1.0",
        "endpoints": {
            "GET /": "→ 重定向 /ui",
            "GET /ui": "友好控制台（推荐）",
            "GET /docs": "Swagger UI",
            "GET /health": "健康检查",
            "GET /api/profile": "用户画像摘要",
            "POST /api/query": "RAG 问答（一次性）",
            "POST /api/stream": "RAG 问答（SSE 流式）",
            "POST /api/search": "仅检索",
            "POST /api/match": "岗位匹配（三档结论）",
            "POST /api/reset": "清空对话历史",
        },
    }


@app.get("/health")
async def health():
    """健康检查"""
    import chromadb
    db_dir = os.path.join(BASE_DIR, "chroma_db")
    db_exists = os.path.exists(db_dir)
    
    collection_count = 0
    if db_exists:
        client = chromadb.PersistentClient(path=db_dir)
        try:
            col = client.get_collection("offerclaw_docs")
            collection_count = col.count()
        except Exception:
            pass

    return {
        "status": "healthy" if collection_count > 0 else "degraded",
        "chroma_db": "connected" if db_exists else "not_found",
        "collection_records": collection_count,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


@app.get("/api/profile", response_model=ProfileResponse)
async def get_profile():
    """获取用户画像摘要（读 user_profile.md）"""
    profile_path = os.path.join(BASE_DIR, "user_profile.md")
    if not os.path.exists(profile_path):
        raise HTTPException(status_code=404, detail="user_profile.md 不存在")

    with open(profile_path, "r", encoding="utf-8") as f:
        content = f.read()

    name, direction, skills_summary, updated_at = _parse_profile(content)
    return ProfileResponse(
        name=name,
        direction=direction,
        skills_summary=skills_summary,
        updated_at=updated_at,
    )


@app.post("/api/query", response_model=QueryResponse)
async def rag_query(req: QueryRequest):
    """
    RAG 问答接口。
    传入问题，返回 LLM 整合后的回答 + 检索到的片段数量。
    """
    try:
        agent = get_rag_agent()
        
        # 先检索
        docs = agent._retrieve(req.query, req.top_k)
        retrieval_count = len(docs) if docs else 0
        
        # 再调用 LLM
        answer = agent.chat(req.query, use_retrieval=req.use_retrieval)

        return QueryResponse(
            query=req.query,
            answer=answer,
            retrieval_count=retrieval_count,
            timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG 查询失败: {str(e)}")


@app.post("/api/search")
async def rag_search(req: QueryRequest):
    """
    仅检索接口（不调 LLM）。
    返回检索到的原始文档片段。
    """
    try:
        agent = get_rag_agent()
        
        if agent.collection is None:
            raise HTTPException(status_code=503, detail="ChromaDB 未连接")

        docs = agent._retrieve(req.query, req.top_k)

        return {
            "query": req.query,
            "results": [
                {
                    "document": doc["document"][:300],
                    "source": doc.get("source", "unknown"),
                    "title": doc.get("title", ""),
                    "distance": doc.get("distance", 0),
                }
                for doc in (docs or [])
            ],
            "count": len(docs) if docs else 0,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检索失败: {str(e)}")


@app.post("/api/match", response_model=MatchResponse)
async def job_match(req: MatchRequest):
    """
    岗位匹配接口：调用 match_job.run_match 真实跑出三档结论。
    """
    try:
        from match_job import run_match, format_report, DEMO_PROFILE
        report = run_match(DEMO_PROFILE, req.jd_text, jd_title="API 请求")
        return MatchResponse(
            status=report.conclusion,
            summary=format_report(report),
        )
    except Exception as e:
        _log.exception("match failed")
        raise HTTPException(status_code=500, detail=f"匹配失败: {str(e)}")


@app.post("/api/stream")
async def rag_stream(req: QueryRequest):
    """
    SSE 流式问答接口。
    用智谱 stream=True 把 token 实时推送给前端，模拟 ChatGPT 体验。
    对应蔚来 JD：端到端 LLM 应用工作流 / API 服务集成。
    """
    from rag_tools import generate_zhipu_token, get_embedding, LLM_MODEL
    import chromadb

    rid = current_request_id()
    _log.info(f"stream start q={req.query[:60]!r}")

    # 1) 检索（可选）
    context_block = ""
    retrieval_count = 0
    if req.use_retrieval:
        db_dir = os.path.join(BASE_DIR, "chroma_db")
        if os.path.exists(db_dir):
            try:
                client = chromadb.PersistentClient(path=db_dir)
                col = client.get_collection("offerclaw_docs")
                emb = get_embedding(req.query)
                res = col.query(query_embeddings=[emb], n_results=req.top_k)
                docs = res["documents"][0]
                metas = res["metadatas"][0]
                retrieval_count = len(docs)
                parts = [
                    f"[片段{i+1}] 来源: {metas[i].get('source','?')}\n{docs[i][:300]}"
                    for i in range(retrieval_count)
                ]
                context_block = "\n\n---\n\n".join(parts)
            except Exception as e:
                _log.warning(f"retrieval failed: {e}")

    system = (
        "你是 OfferClaw，求职作战助手。基于下面的检索片段回答用户问题，"
        "片段中没有的内容请如实告知，不要编造。\n\n【检索片段】\n"
        + (context_block or "（本次无检索结果）")
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": req.query},
    ]

    def gen():
        yield f"event: meta\ndata: {json.dumps({'request_id': rid, 'retrieval_count': retrieval_count}, ensure_ascii=False)}\n\n"
        try:
            token = generate_zhipu_token()
            with _requests.post(
                "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                headers={"Authorization": f"Bearer {token}"},
                json={"model": LLM_MODEL, "messages": messages, "stream": True},
                stream=True,
                timeout=120,
            ) as resp:
                resp.raise_for_status()
                for raw in resp.iter_lines(decode_unicode=True):
                    if not raw:
                        continue
                    if raw.startswith("data: "):
                        chunk = raw[6:]
                        if chunk.strip() == "[DONE]":
                            break
                        try:
                            j = json.loads(chunk)
                            delta = j["choices"][0].get("delta", {}).get("content", "")
                            if delta:
                                yield f"data: {json.dumps({'delta': delta}, ensure_ascii=False)}\n\n"
                        except Exception:
                            continue
            yield "event: done\ndata: {}\n\n"
            _log.info("stream done")
        except Exception as e:
            _log.exception("stream failed")
            yield f"event: error\ndata: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/api/reset")
async def reset_conversation():
    """清空对话历史"""
    try:
        agent = get_rag_agent()
        agent.reset()
        return {"status": "ok", "message": "对话历史已清空"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重置失败: {str(e)}")


# =====================================================
# 启动入口
# =====================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
