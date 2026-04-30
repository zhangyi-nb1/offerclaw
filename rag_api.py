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

# 自动加载 .env.local（本地私密 Key，不进 git），补充到环境变量
_env_local = os.path.join(BASE_DIR, ".env.local")
if os.path.exists(_env_local):
    with open(_env_local, encoding="utf-8") as _f:
        for _ln in _f:
            _ln = _ln.strip()
            if _ln and not _ln.startswith("#") and "=" in _ln:
                _k, _v = _ln.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

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
    direction: str = ""
    gap_list: dict = {}
    suggestions: list = []


class FlowRunRequest(BaseModel):
    jd_text: str
    jd_title: str = "未命名 JD"
    skip_llm: bool = True


class FlowRunResponse(BaseModel):
    match_report: dict = {}
    gaps: dict = {}
    plan_outline: list = []
    today_advice: dict = {}
    resume_skeleton: dict = {}
    application_suggestion: dict = {}
    requires_confirmation: list = []
    trace: list = []
    errors: list = []


class PlanRequest(BaseModel):
    gaps: str = ""


class PlanResponse(BaseModel):
    plan_md: str
    saved_path: str = ""


class DailyResponse(BaseModel):
    today_log: str = ""
    recent_summary: str = ""
    recent_days: int = 7


class DailyAppendRequest(BaseModel):
    text: str


class ResumeResponse(BaseModel):
    pitch: str = ""
    stories_preview: str = ""


class TodayResponse(BaseModel):
    today: str
    headline: str
    reason: str = ""
    source: str = ""
    next_actions: list[str] = []
    stats: dict = {}


class DiscoverRequest(BaseModel):
    raw: str = ""
    url: str = ""


class DiscoverResponse(BaseModel):
    company: str = ""
    title: str = ""
    location: str = ""
    job_type: str = ""
    skills_detected: list[str] = []
    duties: str = ""
    requirements: str = ""
    raw_chars: int = 0
    source_url: str = ""
    jd_text: str = ""


class ResumeBuildRequest(BaseModel):
    jd_text: str
    company: str = ""
    title: str = ""


class ResumeBuildResponse(BaseModel):
    resume_md: str
    jd_summary_chars: int = 0


class ResumeMarkdownRequest(BaseModel):
    jd_text: str = ""
    skip_llm: bool = True


class ResumeMarkdownResponse(BaseModel):
    resume_md: str
    sections: list[str] = []
    jd_chars: int = 0
    skip_llm: bool = True
    llm_used: bool = False
    llm_error: str = ""


class JDQueriesResponse(BaseModel):
    queries: list[str] = []
    profile_cities: list[str] = []
    profile_directions: list[str] = []


class JDCandidate(BaseModel):
    title: str
    jd_text: str


class JDRankRequest(BaseModel):
    candidates: list[JDCandidate]


class JDRankItem(BaseModel):
    title: str
    status: str = ""
    direction: str = ""
    gap_count: int = 0
    score: int = 0
    reason: str = ""


class JDRankResponse(BaseModel):
    ranked: list[JDRankItem]
    total: int = 0


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
            "POST /api/match": "岗位匹配（三档结论 + 结构化缺口）",
            "POST /api/flow/run": "CareerFlow 主流程（profile→match→gap→plan→today→resume→application_suggest）",
            "POST /api/plan": "基于缺口生成 4 周路线规划",
            "GET /api/daily": "今日 daily_log + 最近 7 天摘要",
            "POST /api/daily": "向 daily_log.md 追加今日条目",
            "GET /api/resume": "简历素材聚合（pitch + 故事预览）",
            "GET /api/today": "今日建议（聚合投递池 + 日志 + 状态机）",
            "POST /api/discover": "JD 半自动抽取（粘贴或 URL → 结构化 JD）",
            "GET /api/jd/queries": "根据 profile 生成搜索关键词组合（半自动）",
            "POST /api/jd/rank": "对一组候选 JD 排序（调用 match_job）",
            "POST /api/resume/build": "JD 定制简历项目段生成（基于事实清单 + LLM）",
            "POST /api/resume/markdown": "完整 Markdown 简历草稿（默认无 LLM）",
            "GET /ui/console": "求职流程 Stepper 控制台（Phase 3）",
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
    返回结构化 gap_list + suggestions，方便前端独立渲染缺口卡。
    """
    try:
        from match_job import run_match, format_report
        from profile_loader import load_profile
        profile = load_profile()
        report = run_match(profile, req.jd_text, jd_title="API 请求")
        return MatchResponse(
            status=report.conclusion,
            summary=format_report(report),
            direction=report.direction,
            gap_list=report.gap_list or {},
            suggestions=report.suggestions or [],
        )
    except Exception as e:
        _log.exception("match failed")
        raise HTTPException(status_code=500, detail=f"匹配失败: {str(e)}")


@app.post("/api/flow/run", response_model=FlowRunResponse)
async def flow_run(req: FlowRunRequest):
    """CareerFlow 主流程：profile → match → gap → plan → today → resume → application_suggest。

    返回完整 CareerState，前端可分段渲染（卡片 / Stepper）。
    任何写入意图都收在 ``requires_confirmation`` 中，**本接口不会写文件**。
    """
    import asyncio
    try:
        from career_flow import run_career_flow
        loop = asyncio.get_event_loop()
        out = await loop.run_in_executor(
            None,
            lambda: run_career_flow(
                req.jd_text, jd_title=req.jd_title, skip_llm=req.skip_llm,
            ),
        )
        return FlowRunResponse(
            match_report=out.get("match_report") or {},
            gaps=out.get("gaps") or {},
            plan_outline=out.get("plan_outline") or [],
            today_advice=out.get("today_advice") or {},
            resume_skeleton=out.get("resume_skeleton") or {},
            application_suggestion=out.get("application_suggestion") or {},
            requires_confirmation=out.get("requires_confirmation") or [],
            trace=out.get("trace") or [],
            errors=out.get("errors") or [],
        )
    except Exception as e:
        _log.exception("flow_run failed")
        raise HTTPException(status_code=500, detail=f"CareerFlow 失败: {str(e)}")


@app.post("/api/plan", response_model=PlanResponse)
async def gen_plan(req: PlanRequest):
    """基于缺口清单生成 4 周路线规划。无缺口时用 DATA_CONTRACT.md 风格的兜底输入。"""
    import asyncio
    try:
        from plan_gen import (
            read_text, build_messages, call_llm_plain, save_plan,
            PROFILE_PATH, PLAN_PROMPT_PATH, DAILY_LOG_PATH,
            SOURCE_POLICY_PATH, TARGET_RULES_PATH,
        )
        api_key = os.getenv("ZHIPU_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="ZHIPU_API_KEY 未配置")
        gaps = (req.gaps or "").strip() or "（前端未提供缺口清单，按用户画像通用方向规划）"
        messages = build_messages(
            profile=read_text(PROFILE_PATH),
            plan_prompt=read_text(PLAN_PROMPT_PATH),
            daily_log=read_text(DAILY_LOG_PATH),
            source_policy=read_text(SOURCE_POLICY_PATH),
            target_rules=read_text(TARGET_RULES_PATH),
            gaps=gaps,
        )
        loop = asyncio.get_event_loop()
        plan_md = await loop.run_in_executor(
            None, lambda: call_llm_plain(messages, api_key, max_tokens=3500)
        )
        path = save_plan(plan_md)
        return PlanResponse(plan_md=plan_md, saved_path=path)
    except HTTPException:
        raise
    except Exception as e:
        _log.exception("plan failed")
        raise HTTPException(status_code=500, detail=f"规划失败: {str(e)}")


@app.get("/api/daily", response_model=DailyResponse)
async def get_daily():
    """读 daily_log.md：返回今日块 + 最近 7 天聚合。"""
    try:
        from summary_tool import read_text, extract_date_block, extract_recent_blocks, DAILY_LOG_PATH
        log = read_text(DAILY_LOG_PATH)
        today = datetime.date.today().isoformat()
        return DailyResponse(
            today_log=extract_date_block(log, today),
            recent_summary=extract_recent_blocks(log, days=7),
            recent_days=7,
        )
    except Exception as e:
        _log.exception("daily get failed")
        raise HTTPException(status_code=500, detail=f"读取失败: {str(e)}")


@app.post("/api/daily", response_model=DailyResponse)
async def append_daily(req: DailyAppendRequest):
    """向 daily_log.md 追加今日条目（如果今日块不存在则新建标题）。"""
    try:
        from summary_tool import read_text, extract_date_block, extract_recent_blocks, DAILY_LOG_PATH
        text = (req.text or "").strip()
        if not text:
            raise HTTPException(status_code=400, detail="text 不能为空")
        today = datetime.date.today().isoformat()
        log_path = DAILY_LOG_PATH
        existing = read_text(log_path) if os.path.exists(log_path) else ""
        block = extract_date_block(existing, today)
        ts = datetime.datetime.now().strftime("%H:%M")
        if block:
            new_log = existing.rstrip() + f"\n- {ts} {text}\n"
        else:
            sep = "\n\n" if existing else ""
            new_log = existing + f"{sep}## {today}\n- {ts} {text}\n"
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(new_log)
        return DailyResponse(
            today_log=extract_date_block(new_log, today),
            recent_summary=extract_recent_blocks(new_log, days=7),
            recent_days=7,
        )
    except HTTPException:
        raise
    except Exception as e:
        _log.exception("daily append failed")
        raise HTTPException(status_code=500, detail=f"追加失败: {str(e)}")


@app.get("/api/resume", response_model=ResumeResponse)
async def get_resume():
    """聚合简历素材：docs/resume_pitch.md 全文 + interview_story_bank.md 标题列表。"""
    try:
        pitch_path = os.path.join(BASE_DIR, "docs", "resume_pitch.md")
        story_path = os.path.join(BASE_DIR, "interview_story_bank.md")
        pitch = open(pitch_path, encoding="utf-8").read() if os.path.exists(pitch_path) else "（缺 docs/resume_pitch.md）"
        stories_preview = ""
        if os.path.exists(story_path):
            import re as _re
            content = open(story_path, encoding="utf-8").read()
            titles = _re.findall(r"^## (Story.*)$", content, _re.MULTILINE)
            stories_preview = "\n".join(f"- {t}" for t in titles) or "（未识别到 Story 标题）"
        return ResumeResponse(pitch=pitch, stories_preview=stories_preview)
    except Exception as e:
        _log.exception("resume failed")
        raise HTTPException(status_code=500, detail=f"读取失败: {str(e)}")


@app.get("/api/today", response_model=TodayResponse)
async def get_today():
    """V2 阶段三：聚合 applications + daily_log + profile，给一句"今天最该做什么"。"""
    try:
        from career_agent import get_today_advice
        return TodayResponse(**get_today_advice())
    except Exception as e:
        _log.exception("today failed")
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


@app.post("/api/discover", response_model=DiscoverResponse)
async def discover(req: DiscoverRequest):
    """V2 阶段四：JD 半自动抽取。raw 文本或 URL 都可，返回结构化 JD。
    URL 模式：先 requests 快速抓，若 SPA 则自动启动 Playwright 无头浏览器渲染。
    """
    import asyncio
    try:
        from job_discovery import discover as _disc
        loop = asyncio.get_event_loop()
        # Playwright 是同步阻塞调用，放线程池避免卡事件循环
        out = await loop.run_in_executor(None, lambda: _disc(raw=req.raw, url=req.url))
        return DiscoverResponse(**out)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _log.exception("discover failed")
        raise HTTPException(status_code=500, detail=f"抽取失败: {str(e)}")


@app.post("/api/resume/build", response_model=ResumeBuildResponse)
async def build_resume(req: ResumeBuildRequest):
    """V2 阶段五：针对一份 JD 生成 OfferClaw 项目段（bullet + 段落 + 命中分析）。"""
    import asyncio
    try:
        from resume_builder import build_resume_for_jd
        meta = []
        if req.company: meta.append(f"公司：{req.company}")
        if req.title: meta.append(f"岗位：{req.title}")
        meta.append("JD 原文：\n" + req.jd_text[:4000])
        jd_summary = "\n".join(meta)
        loop = asyncio.get_event_loop()
        out = await loop.run_in_executor(None, lambda: build_resume_for_jd(jd_summary))
        return ResumeBuildResponse(**out)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        _log.exception("resume build failed")
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


@app.post("/api/resume/build/stream")
async def build_resume_stream(req: ResumeBuildRequest):
    """流式版简历生成：SSE 逐 token 返回，首 token 约 1s 内到达。"""
    import asyncio, json as _json
    api_key = os.getenv("ZHIPU_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ZHIPU_API_KEY 未配置")
    from resume_builder import build_messages as _bm, _read
    from plan_gen import call_llm_stream
    meta = []
    if req.company: meta.append(f"公司：{req.company}")
    if req.title: meta.append(f"岗位：{req.title}")
    meta.append("JD 原文：\n" + req.jd_text[:4000])
    messages = _bm(jd_summary="\n".join(meta),
                   profile=_read(os.path.join(BASE_DIR, "user_profile.md")))

    async def generate():
        loop = asyncio.get_event_loop()
        q: asyncio.Queue = asyncio.Queue()

        def _producer():
            try:
                for tok in call_llm_stream(messages, api_key, max_tokens=2000):
                    loop.call_soon_threadsafe(q.put_nowait, tok)
            except Exception as exc:
                loop.call_soon_threadsafe(q.put_nowait, f"\n\n[生成错误: {exc}]")
            finally:
                loop.call_soon_threadsafe(q.put_nowait, None)

        loop.run_in_executor(None, _producer)
        while True:
            tok = await q.get()
            if tok is None:
                yield "data: [DONE]\n\n"
                break
            yield f"data: {_json.dumps({'text': tok}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/plan/stream")
async def gen_plan_stream(req: PlanRequest):
    """流式版规划生成：SSE 逐 token 返回。"""
    import asyncio, json as _json
    api_key = os.getenv("ZHIPU_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ZHIPU_API_KEY 未配置")
    from plan_gen import (
        read_text, build_messages, call_llm_stream, save_plan,
        PROFILE_PATH, PLAN_PROMPT_PATH, DAILY_LOG_PATH,
        SOURCE_POLICY_PATH, TARGET_RULES_PATH,
    )
    gaps = (req.gaps or "").strip() or "（前端未提供缺口清单，按用户画像通用方向规划）"
    messages = build_messages(
        profile=read_text(PROFILE_PATH),
        plan_prompt=read_text(PLAN_PROMPT_PATH),
        daily_log=read_text(DAILY_LOG_PATH),
        source_policy=read_text(SOURCE_POLICY_PATH),
        target_rules=read_text(TARGET_RULES_PATH),
        gaps=gaps,
    )

    async def generate():
        loop = asyncio.get_event_loop()
        q: asyncio.Queue = asyncio.Queue()
        full_text = []

        def _producer():
            try:
                for tok in call_llm_stream(messages, api_key, max_tokens=3500):
                    full_text.append(tok)
                    loop.call_soon_threadsafe(q.put_nowait, ("tok", tok))
                # 流结束后落盘
                plan_md = "".join(full_text)
                path = save_plan(plan_md)
                loop.call_soon_threadsafe(q.put_nowait, ("done", path))
            except Exception as exc:
                loop.call_soon_threadsafe(q.put_nowait, ("err", str(exc)))

        loop.run_in_executor(None, _producer)
        while True:
            kind, val = await q.get()
            if kind == "tok":
                yield f"data: {_json.dumps({'text': val}, ensure_ascii=False)}\n\n"
            elif kind == "done":
                yield f"data: {_json.dumps({'done': True, 'saved_path': val}, ensure_ascii=False)}\n\n"
                break
            else:
                yield f"data: {_json.dumps({'error': val}, ensure_ascii=False)}\n\n"
                break

    return StreamingResponse(
        generate(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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
# Phase 3 / 4 / 5：UI Console + JD Discovery 增强 + Resume Markdown
# =====================================================

@app.get("/ui/console")
async def ui_console():
    """求职流程 Stepper 控制台（Phase 3）。"""
    return FileResponse(os.path.join(BASE_DIR, "static", "console.html"))


@app.get("/api/jd/queries", response_model=JDQueriesResponse)
async def jd_queries():
    """根据 user_profile.md 生成搜索关键词组合（不爬，仅推荐）。"""
    try:
        from job_discovery import build_search_queries
        from profile_loader import load_profile
        prof = load_profile()
        return JDQueriesResponse(
            queries=build_search_queries(prof),
            profile_cities=prof.get("可接受地域") or [],
            profile_directions=prof.get("方向优先级") or [],
        )
    except Exception as e:
        _log.exception("jd_queries failed")
        raise HTTPException(status_code=500, detail=f"生成搜索词失败: {str(e)}")


@app.post("/api/jd/rank", response_model=JDRankResponse)
async def jd_rank(req: JDRankRequest):
    """对一组候选 JD 调 match_job 排序，输出推荐顺序。"""
    try:
        from job_discovery import rank_candidates
        ranked = rank_candidates([c.model_dump() for c in req.candidates])
        items = [JDRankItem(
            title=r.get("title", ""), status=r.get("status", ""),
            direction=r.get("direction", ""), gap_count=r.get("gap_count", 0),
            score=r.get("score", 0), reason=r.get("reason", ""),
        ) for r in ranked]
        return JDRankResponse(ranked=items, total=len(items))
    except Exception as e:
        _log.exception("jd_rank failed")
        raise HTTPException(status_code=500, detail=f"JD 排序失败: {str(e)}")


@app.post("/api/resume/markdown", response_model=ResumeMarkdownResponse)
async def resume_markdown(req: ResumeMarkdownRequest):
    """生成完整 Markdown 简历草稿（默认无 LLM）。"""
    try:
        from resume_builder import build_resume_markdown
        out = build_resume_markdown(jd_text=req.jd_text, skip_llm=req.skip_llm)
        return ResumeMarkdownResponse(
            resume_md=out["resume_md"], sections=out["sections"],
            jd_chars=out["jd_chars"], skip_llm=out["skip_llm"],
            llm_used=out.get("llm_used", False), llm_error=out.get("llm_error", ""),
        )
    except Exception as e:
        _log.exception("resume_markdown failed")
        raise HTTPException(status_code=500, detail=f"生成简历草稿失败: {str(e)}")


# =====================================================
# 启动入口
# =====================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
