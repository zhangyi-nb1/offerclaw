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

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import sys
import datetime

# 确保能找到 rag_tools
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

app = FastAPI(
    title="OfferClaw API",
    description="求职作战 Agent 的 HTTP API 接口层（RAG + 岗位匹配 + 用户画像）",
    version="1.0.0",
)

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


# =====================================================
# API 路由
# =====================================================

@app.get("/")
async def root():
    """根路径：API 信息"""
    return {
        "name": "OfferClaw API",
        "version": "1.0.0",
        "description": "求职作战 Agent HTTP API",
        "endpoints": {
            "GET /health": "健康检查",
            "GET /api/profile": "获取用户画像摘要",
            "POST /api/query": "RAG 问答",
            "POST /api/search": "仅检索（不调 LLM）",
            "POST /api/match": "岗位匹配（占位）",
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

    # 简单解析（后续可用更精细的解析）
    name = "Zhang Yi"
    direction = ["Agent 应用工程", "AI 应用开发", "Prompt / Workflow 工程"]

    # 提取技能摘要
    skills_summary = "Python(2/5), MATLAB(熟练), Prompt(2/5), Agent(1/5), RAG(1/5→实战中)"

    return ProfileResponse(
        name=name,
        direction=direction,
        skills_summary=skills_summary,
        updated_at="2026-04-21",
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
    岗位匹配接口（占位实现）。
    后续对接 job_match_prompt.md 的完整 9 步流程。
    """
    return MatchResponse(
        status="stub",
        summary="岗位匹配模块尚未完全实现。当前版本仅接收 JD 文本，完整匹配分析需调用 job_match_prompt.md 流程。",
    )


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
