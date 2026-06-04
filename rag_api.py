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
import base64
import json
import os
import re
import sys
import datetime

import requests as _requests

# 确保能找到 rag_tools
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
DAILY_ATTACHMENT_DIR = os.path.join(BASE_DIR, "daily_attachments")
DAILY_ATTACHMENT_MAX_BYTES = 10 * 1024 * 1024
DAILY_ATTACHMENT_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif"}
HTML_NO_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}

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


def _active_llm_api_key() -> tuple[str, str]:
    """Return the active chat API key and env name from day1_api_starter config."""
    from day1_api_starter import get_llm_config

    cfg = get_llm_config()
    return cfg["api_key"], cfg["api_key_env"]


def get_rag_agent():
    """懒加载 RAG Agent"""
    global _rag_agent
    if _rag_agent is None:
        from rag_agent import RAGAgent
        _rag_agent = RAGAgent()
    return _rag_agent


def _safe_daily_attachment_name(name: str) -> str:
    """Return a local-safe file name while preserving the user's extension."""
    raw = os.path.basename(name or "").strip()
    stem, ext = os.path.splitext(raw)
    ext = ext.lower()
    stem = re.sub(r"[^0-9A-Za-z._\-\u4e00-\u9fff]+", "_", stem).strip("._-")
    if not stem:
        stem = "attachment"
    return f"{stem[:80]}{ext}"


def _unique_path(directory: str, filename: str) -> str:
    stem, ext = os.path.splitext(filename)
    candidate = os.path.join(directory, filename)
    idx = 2
    while os.path.exists(candidate):
        candidate = os.path.join(directory, f"{stem}-{idx}{ext}")
        idx += 1
    return candidate


def _decode_attachment_data(data_base64: str) -> bytes:
    payload = (data_base64 or "").strip()
    if "," in payload and payload.lower().startswith("data:"):
        payload = payload.split(",", 1)[1]
    try:
        return base64.b64decode(payload, validate=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="附件内容不是有效的 base64") from exc


def _html_file_response(filename: str) -> FileResponse:
    """Serve local UI HTML without browser cache during active iteration."""
    return FileResponse(
        os.path.join(BASE_DIR, "static", filename),
        headers=HTML_NO_CACHE_HEADERS,
    )


def _static_rev(filename: str) -> int:
    path = os.path.join(BASE_DIR, "static", filename)
    return int(os.path.getmtime(path))


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
    in_kb: bool = True            # P2.5：是否命中知识库
    sources: list[str] = []       # 命中时的来源文件名
    matched_by: str = ""          # vector | lexical_rescue | ""


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


class CurrentPlanResponse(BaseModel):
    has_plan: bool = False
    content: str = ""
    filename: str = ""
    mtime: int = 0
    edited_by_user: bool = False


class PlanSaveRequest(BaseModel):
    content: str
    note: str = ""        # 用户编辑说明（可选），记入记忆事件


class KBAddUrlRequest(BaseModel):
    url: str


class KBAddFileRequest(BaseModel):
    name: str
    content_base64: str = ""
    text: str = ""        # 也允许直接传纯文本（二选一）


class KBPromoteRequest(BaseModel):
    pending_file: str     # _score_and_save 返回的 saved（相对路径）
    to_subdir: str        # career_paths / experience_posts / learning_resources


class GapTargetRequest(BaseModel):
    jd_text: str = ""
    gaps: dict = {}       # match 产出的 {分类: [条目...]}
    title: str = ""
    company: str = ""


class ApplicationUpsertRequest(BaseModel):
    company: str
    position: str
    status: str                  # applications_store.STATUSES 之一
    date: str = ""               # 默认今天
    source: str = ""
    location: str = ""
    next_action: str = ""
    note: str = ""
    experience: str = ""         # 经验总结（笔试/面试真题、流程、教训）
    experience_stage: str = ""   # 笔试 / 一面 / 二面 / HR面 / 终面 / 其他
    add_to_kb: bool = False      # 经验是否加入知识库（指导 RAG 与学习计划）


class ResumeProjectRequest(BaseModel):
    repo_url: str = ""           # 项目仓库地址（GitHub 公开仓库优先）
    text: str = ""               # 项目介绍文本（或上传文件解码后的内容）
    project_name: str = ""


class ResumeTemplateUploadRequest(BaseModel):
    name: str                    # 文件名（.md/.txt）
    content_base64: str = ""
    text: str = ""


class DailyResponse(BaseModel):
    today_log: str = ""
    recent_summary: str = ""
    recent_days: int = 7


class DailyAppendRequest(BaseModel):
    text: str


class DailyLogStructuredRequest(BaseModel):
    tag: str = ""
    done: list[str] = []
    todo: list[str] = []
    notes: str = ""


class DailyAttachmentPayload(BaseModel):
    name: str
    content_type: str = ""
    data_base64: str


class DailyAttachmentRequest(BaseModel):
    files: list[DailyAttachmentPayload] = []


class ResumeResponse(BaseModel):
    pitch: str = ""
    stories_preview: str = ""


class TodayResponse(BaseModel):
    today: str
    headline: str
    reason: str = ""
    source: str = ""
    next_actions: list[str] = []
    adjustments: list[str] = []  # P2：复盘沉淀的次日调整规则
    plan: dict = {}              # 当前学习计划的本周重点（自动化引用的最新计划）
    today_plan: list[str] = []   # 今日对照清单（每日执行卡对照 + 未完成自动判定基准）
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


class AgentRequest(BaseModel):
    message: str
    mode: str = "deterministic"  # 'deterministic' | 'llm'
    max_steps: int = 3


class AgentResponse(BaseModel):
    answer: str
    tool_calls: list = []
    mode: str = "deterministic"
    steps: int = 0
    errors: list = []


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
async def ui(request: Request):
    """OfferClaw 控制台（零依赖单页应用）。"""
    if not request.url.query:
        return RedirectResponse(
            url=f"/ui?rev={_static_rev('index.html')}",
            status_code=307,
            headers=HTML_NO_CACHE_HEADERS,
        )
    return _html_file_response("index.html")


@app.get("/api/info")
async def info():
    """API 元信息（原 / 的内容）。"""
    return {
        "name": "OfferClaw API",
        "version": "1.1.0",
        "endpoints": {
            "GET /": "→ 重定向 /ui",
            "GET /ui": "友好控制台（推荐）",
            "GET /ui/console": "求职流程 Stepper 控制台（V3 Phase 3）",
            "GET /health": "健康检查",
            "GET /api/info": "本接口（元信息 + 路由清单）",
            "GET /api/profile": "用户画像摘要",
            "POST /api/query": "RAG 问答（一次性）",
            "POST /api/stream": "RAG 问答（SSE 流式）",
            "POST /api/search": "仅检索",
            "POST /api/match": "岗位匹配（三档结论 + 结构化缺口）",
            "POST /api/flow/run": "CareerFlow 主流程（profile→job_input→match→gap→plan→today→resume→application_suggest）",
            "POST /api/plan": "基于缺口生成 4 周路线规划",
            "POST /api/plan/stream": "4 周路线规划（SSE 流式）",
            "GET /api/daily": "今日 daily_log + 最近 7 天摘要",
            "POST /api/daily": "向 daily_log.md 追加今日条目",
            "POST /api/daily/attachments": "上传每日留痕附件（PDF / 图片）",
            "GET /api/resume": "简历素材聚合（pitch + 故事预览）",
            "GET /api/today": "今日建议（聚合投递池 + 日志 + 状态机）",
            "POST /api/discover": "JD 半自动抽取（粘贴或 URL → 结构化 JD）",
            "GET /api/jd/queries": "根据 profile 生成搜索关键词组合（半自动）",
            "POST /api/jd/rank": "对一组候选 JD 排序（调用 match_job）",
            "POST /api/resume/build": "JD 定制简历项目段生成（基于事实清单 + LLM）",
            "POST /api/resume/build/stream": "JD 定制简历项目段（SSE 流式）",
            "POST /api/resume/markdown": "完整 Markdown 简历草稿（默认无 LLM）",
            "POST /api/reset": "清空对话历史",
        },
    }


@app.get("/health")
async def health():
    """健康检查"""
    import chromadb
    from rag_tools import describe_embedding_config, get_collection_name

    db_dir = os.path.join(BASE_DIR, "chroma_db")
    db_exists = os.path.exists(db_dir)
    collection_name = get_collection_name()
    
    collection_count = 0
    if db_exists:
        client = chromadb.PersistentClient(path=db_dir)
        try:
            col = client.get_collection(collection_name)
            collection_count = col.count()
        except Exception:
            pass

    return {
        "status": "healthy" if collection_count > 0 else "degraded",
        "chroma_db": "connected" if db_exists else "not_found",
        "collection": collection_name,
        "collection_records": collection_count,
        "embedding": describe_embedding_config(),
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
    """RAG 问答接口（知识库优先 · 带门槛）。

    与微信路径（offerclaw_cli query）共用 rag_gate.gated_query：
    命中知识库才基于 KB 合成答案并标注来源；未命中坦白"知识库暂无"，
    绝不退回通用知识杜撰。
    """
    import asyncio
    try:
        from rag_gate import gated_query
        loop = asyncio.get_event_loop()
        d = await loop.run_in_executor(None, lambda: gated_query(req.query, req.top_k))
        return QueryResponse(
            query=req.query,
            answer=d.get("answer", ""),
            retrieval_count=d.get("retrieval_count", 0),
            timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            in_kb=d.get("in_kb", False),
            sources=d.get("sources", []),
            matched_by=d.get("matched_by") or "",
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
            prepare_plan_messages, call_llm_plain, save_plan,
            append_resources_appendix,
        )
        api_key, api_key_env = _active_llm_api_key()
        if not api_key:
            raise HTTPException(status_code=500, detail=f"{api_key_env} 未配置")
        gaps = _resolve_plan_gaps(req.gaps)
        # 统一入口：读依赖 + RAG 检索资源 + 组装 messages（与 CLI 一致）
        messages, resources = prepare_plan_messages(gaps)
        loop = asyncio.get_event_loop()
        plan_md = await loop.run_in_executor(
            None, lambda: call_llm_plain(messages, api_key, max_tokens=3500)
        )
        # 退化产物（拒绝/无周结构）不落盘，避免污染"当前计划"
        from plan_gen import is_degenerate_plan
        if is_degenerate_plan(plan_md):
            return PlanResponse(plan_md=plan_md, saved_path="")
        # 确定性追加参考资源附录，保证 API 路径也必含知识库引用
        plan_md = append_resources_appendix(plan_md, resources)
        path = save_plan(plan_md)
        return PlanResponse(plan_md=plan_md, saved_path=path)
    except HTTPException:
        raise
    except Exception as e:
        _log.exception("plan failed")
        raise HTTPException(status_code=500, detail=f"规划失败: {str(e)}")


@app.get("/api/plan/current", response_model=CurrentPlanResponse)
async def current_plan():
    """读取当前（最新）学习计划，供页面打开时直接展示。无计划时 has_plan=False。"""
    try:
        from plan_gen import load_latest_plan
        latest = load_latest_plan()
        if not latest:
            return CurrentPlanResponse(has_plan=False)
        return CurrentPlanResponse(
            has_plan=True,
            content=latest["content"],
            filename=latest["filename"],
            mtime=latest["mtime"],
            edited_by_user=latest["edited_by_user"],
        )
    except Exception as e:
        _log.exception("current_plan failed")
        raise HTTPException(status_code=500, detail=f"读取计划失败: {str(e)}")


@app.post("/api/plan/save", response_model=PlanResponse)
async def save_edited_plan(req: PlanSaveRequest):
    """保存用户手动编辑后的计划：落盘 plans/（带 _user 标识）+ 记一条 episodic 记忆事件，
    让复盘 / 今日建议能感知『用户调整过计划』。"""
    content = (req.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="计划内容不能为空")
    try:
        from plan_gen import save_plan
        path = save_plan(content, edited_by_user=True)
        # 让 OfferClaw 知晓：写入分层记忆（情景层），失败不阻塞落盘
        try:
            from memory_layers import EpisodicMemory
            EpisodicMemory().append({
                "kind": "plan_edited",
                "source": "web_ui",
                "note": (req.note or "").strip(),
                "chars": len(content),
                "saved_path": os.path.relpath(path, BASE_DIR),
            })
        except Exception:
            _log.warning("plan_edited memory append failed", exc_info=True)
        return PlanResponse(plan_md=content, saved_path=os.path.relpath(path, BASE_DIR))
    except HTTPException:
        raise
    except Exception as e:
        _log.exception("save_edited_plan failed")
        raise HTTPException(status_code=500, detail=f"保存计划失败: {str(e)}")


def _resolve_plan_gaps(req_gaps: str) -> str:
    """计划生成的缺口来源（按优先级）：显式入参 > 缺口信息库（累积的目标 JD 缺口）>
    画像通用方向。计划永远基于「画像 + 知识库 + 缺口库」三件套，与单次匹配解耦。"""
    g = (req_gaps or "").strip()
    if g:
        return g
    try:
        from gap_store import merged_gaps_text
        stored = merged_gaps_text()
        if stored:
            return stored
    except Exception:
        _log.warning("read gap_store failed", exc_info=True)
    return "（缺口库为空，按用户画像通用方向规划）"


@app.post("/api/gaps/target")
async def set_gap_target(req: GapTargetRequest):
    """把一个 JD 设为目标：JD 摘要 + 缺口持久入缺口库（跨 JD 合并去重）。
    此后所有计划（重新）生成都以累积缺口库为背景。"""
    try:
        from gap_store import add_target
        out = add_target(req.jd_text, req.gaps, title=req.title, company=req.company)
        if out.get("status") != "ok":
            raise HTTPException(status_code=400, detail=out.get("error", "入库失败"))
        return out
    except HTTPException:
        raise
    except Exception as e:
        _log.exception("set_gap_target failed")
        raise HTTPException(status_code=500, detail=f"目标入库失败: {str(e)}")


@app.get("/api/gaps")
async def get_gaps():
    """缺口信息库概览：目标 JD 列表 + 合并后的缺口 + 可直接喂计划的文本。"""
    try:
        from gap_store import list_targets, merged_gaps, merged_gaps_text, summary
        return {
            "status": "ok",
            **summary(),
            "targets": [
                {k: t.get(k) for k in ("id", "added_at", "title", "company", "raw_gap_count")}
                for t in list_targets()
            ],
            "merged": merged_gaps(),
            "merged_text": merged_gaps_text(),
        }
    except Exception as e:
        _log.exception("get_gaps failed")
        raise HTTPException(status_code=500, detail=f"读取缺口库失败: {str(e)}")


# =====================================================
# 投递管理：用户上传真实投递情况 + 亲历经验入知识库
# =====================================================

@app.get("/api/applications")
async def get_applications():
    """投递清单（过滤 [DEMO] 示例行）+ 状态枚举。"""
    try:
        from applications_store import list_applications, STATUSES
        return {"status": "ok", "rows": list_applications(), "statuses": STATUSES}
    except Exception as e:
        _log.exception("get_applications failed")
        raise HTTPException(status_code=500, detail=f"读取投递清单失败: {str(e)}")


@app.post("/api/applications/upsert")
async def upsert_application_api(req: ApplicationUpsertRequest):
    """新增/更新一条真实投递（按 公司+岗位 定位，备注追加时间线）。

    带经验总结时落盘 experience_posts/；勾选 add_to_kb 则**增量入向量库**
    （用户亲历的第一手经验，强指导 RAG 问答、学习计划与每日建议）。
    """
    import asyncio
    try:
        from applications_store import upsert_application, save_experience
        out = upsert_application(
            req.company, req.position, req.status,
            date=req.date, source=req.source, location=req.location,
            next_action=req.next_action, note=req.note,
        )
        if out.get("status") != "ok":
            raise HTTPException(status_code=400, detail=out.get("error", "写入失败"))

        if (req.experience or "").strip():
            exp = save_experience(req.company, req.position,
                                  req.experience_stage or "投递过程", req.experience)
            if exp.get("status") != "ok":
                out["experience_error"] = exp.get("error", "经验保存失败")
            else:
                out["experience_saved"] = exp["saved"]
                if req.add_to_kb:
                    import subprocess
                    before = _kb_count()
                    loop = asyncio.get_event_loop()
                    proc = await loop.run_in_executor(None, lambda: subprocess.run(
                        [os.path.join(BASE_DIR, ".venv/bin/python"), "rag_ingest.py",
                         "--add", exp["saved"], "--source-type", "experience"],
                        cwd=BASE_DIR, capture_output=True, text=True, timeout=300,
                    ))
                    _kb_clear_cache()
                    after = _kb_count()
                    out["kb_ingest"] = "ok" if proc.returncode == 0 else "failed"
                    out["kb_chunks_added"] = max(0, after - before)
                    out["kb_chunks_total"] = after
        return out
    except HTTPException:
        raise
    except Exception as e:
        _log.exception("upsert_application failed")
        raise HTTPException(status_code=500, detail=f"投递记录失败: {str(e)}")


# =====================================================
# 简历：项目 → 简历项目经历段（模板学习式生成）
# =====================================================

@app.get("/api/resume/templates")
async def list_resume_templates():
    """已学习的简历材料清单（写作指导 + 真实简历范例）。"""
    try:
        from resume_project import load_materials, extract_project_blocks
        m = load_materials()
        n_blocks = sum(len(extract_project_blocks(e["content"])) for e in m["examples"])
        return {
            "status": "ok",
            "guidance": [g["name"] for g in m["guidance"]],
            "examples": [e["name"] for e in m["examples"]],
            "project_blocks": n_blocks,
        }
    except Exception as e:
        _log.exception("list_resume_templates failed")
        raise HTTPException(status_code=500, detail=f"读取模板失败: {str(e)}")


@app.post("/api/resume/templates")
async def upload_resume_template(req: ResumeTemplateUploadRequest):
    """上传简历材料（.md/.txt）到 resume_templates/：
    文件名含 note/写法/指导 视为写作指导，否则视为真实简历范例（用于格式学习）。"""
    name = (req.name or "").strip()
    ext = os.path.splitext(name)[1].lower()
    if ext not in (".md", ".markdown", ".txt"):
        raise HTTPException(status_code=400, detail=f"仅支持 .md/.txt，收到 {ext or name}")
    text = req.text or ""
    if not text and req.content_base64:
        try:
            text = base64.b64decode(req.content_base64).decode("utf-8", errors="replace")
        except Exception:
            raise HTTPException(status_code=400, detail="文件解码失败（需 UTF-8 文本）")
    if len(text.strip()) < 50:
        raise HTTPException(status_code=400, detail="内容太短（≥50 字）")
    try:
        from resume_project import TEMPLATES_DIR
        os.makedirs(TEMPLATES_DIR, exist_ok=True)
        safe = re.sub(r"[^\w.\-一-鿿]+", "_", name)[:80]
        if not safe.endswith(".md"):
            safe = os.path.splitext(safe)[0] + ".md"
        path = os.path.join(TEMPLATES_DIR, safe)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        from resume_project import load_materials
        m = load_materials()
        return {"status": "ok", "saved": safe,
                "guidance_count": len(m["guidance"]), "example_count": len(m["examples"])}
    except HTTPException:
        raise
    except Exception as e:
        _log.exception("upload_resume_template failed")
        raise HTTPException(status_code=500, detail=f"保存模板失败: {str(e)}")


@app.post("/api/resume/project/stream")
async def resume_project_stream(req: ResumeProjectRequest):
    """项目素材（仓库地址 / md·txt / 粘贴文本）→ 按简历模板模式生成项目经历段。SSE 流式。"""
    import asyncio, json as _json
    api_key, api_key_env = _active_llm_api_key()
    if not api_key:
        raise HTTPException(status_code=500, detail=f"{api_key_env} 未配置")
    from resume_project import gather_material, build_project_messages
    from plan_gen import call_llm_stream

    loop = asyncio.get_event_loop()
    # 素材汇集（仓库抓取可能耗时，放线程池）
    gathered = await loop.run_in_executor(
        None, lambda: gather_material(repo_url=req.repo_url, text=req.text))
    if gathered.get("status") != "ok":
        raise HTTPException(status_code=400, detail=gathered.get("error", "素材获取失败"))

    profile = ""
    try:
        with open(os.path.join(BASE_DIR, "user_profile.md"), encoding="utf-8") as f:
            profile = f.read()
    except OSError:
        pass
    messages = build_project_messages(gathered["material"], req.project_name, profile)

    async def generate():
        q: asyncio.Queue = asyncio.Queue()
        # 先告知素材来源（meta 事件）
        yield f"data: {_json.dumps({'meta': {'origin': gathered['origin']}}, ensure_ascii=False)}\n\n"

        def _producer():
            try:
                for tok in call_llm_stream(messages, api_key, max_tokens=1800):
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


@app.post("/api/daily/log")
async def append_daily_structured(req: DailyLogStructuredRequest):
    """结构化留痕（Web 表单专用）：主线/已完成/未完成/笔记 → daily_log.md。

    与 CLI cmd_log、晚间复盘 _parse_log_block 走同一写入器，格式统一可解析。
    """
    try:
        from summary_tool import append_structured_daily_log, analyze_incomplete
        if not (req.done or req.todo or req.notes.strip() or req.tag.strip()):
            raise HTTPException(status_code=400, detail="留痕内容不能全空")
        # 未完成不由用户填写：对照 OfferClaw 今日计划自动判定（系统分析生成）
        planned: list = []
        try:
            from career_agent import get_today_advice
            planned = get_today_advice().get("today_plan", [])
        except Exception:
            _log.warning("load today_plan failed", exc_info=True)
        auto_todo = analyze_incomplete(req.done, planned)
        # 兼容外部调用方显式传入的 todo（如微信留痕），合并去重
        final_todo = auto_todo + [t for t in (req.todo or []) if t and t not in auto_todo]
        result = append_structured_daily_log(
            tag=req.tag.strip(), done=req.done, todo=final_todo, notes=req.notes,
        )
        result["today_plan"] = planned
        result["auto_incomplete"] = auto_todo
        return result
    except HTTPException:
        raise
    except Exception as e:
        _log.exception("structured daily log failed")
        raise HTTPException(status_code=500, detail=f"留痕失败: {str(e)}")


@app.post("/api/daily/attachments")
async def upload_daily_attachments(req: DailyAttachmentRequest):
    """保存学习留痕附件，返回可写入 daily_log.md 的本地链接。"""
    if not req.files:
        raise HTTPException(status_code=400, detail="files 不能为空")
    if len(req.files) > 8:
        raise HTTPException(status_code=400, detail="单次最多上传 8 个附件")

    today = datetime.date.today().isoformat()
    target_dir = os.path.join(DAILY_ATTACHMENT_DIR, today)
    os.makedirs(target_dir, exist_ok=True)

    saved = []
    for item in req.files:
        filename = _safe_daily_attachment_name(item.name)
        ext = os.path.splitext(filename)[1].lower()
        content_type = (item.content_type or "").lower()
        if ext not in DAILY_ATTACHMENT_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"不支持的附件类型: {ext or item.name}")
        if content_type and not (content_type == "application/pdf" or content_type.startswith("image/")):
            raise HTTPException(status_code=400, detail=f"不支持的附件 MIME: {content_type}")

        data = _decode_attachment_data(item.data_base64)
        if not data:
            raise HTTPException(status_code=400, detail=f"附件为空: {item.name}")
        if len(data) > DAILY_ATTACHMENT_MAX_BYTES:
            raise HTTPException(status_code=400, detail=f"附件过大: {item.name}")

        path = _unique_path(target_dir, filename)
        with open(path, "wb") as f:
            f.write(data)
        public_name = os.path.basename(path)
        url = f"/daily_attachments/{today}/{public_name}"
        saved.append({
            "name": public_name,
            "url": url,
            "markdown": f"[{public_name}]({url})",
            "size": len(data),
            "content_type": content_type,
        })
    return {"status": "ok", "date": today, "count": len(saved), "files": saved}


@app.get("/daily_attachments/{date_str}/{filename}")
async def get_daily_attachment(date_str: str, filename: str):
    """读取学习留痕附件。"""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_str):
        raise HTTPException(status_code=404, detail="附件不存在")
    filename = _safe_daily_attachment_name(filename)
    path = os.path.abspath(os.path.join(DAILY_ATTACHMENT_DIR, date_str, filename))
    root = os.path.abspath(DAILY_ATTACHMENT_DIR)
    if not path.startswith(root + os.sep) or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="附件不存在")
    return FileResponse(path)


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


# =====================================================
# 知识库维护：采集/上传 → 评分预览 → 人工确认 → 增量入库
# =====================================================

def _kb_count() -> int:
    """当前 collection 的块数（count 读 SQLite 元数据，跨进程即时准确）。"""
    import chromadb
    from rag_tools import get_collection_name
    client = chromadb.PersistentClient(path=os.path.join(BASE_DIR, "chroma_db"))
    try:
        return client.get_collection(get_collection_name()).count()
    except Exception:
        return 0


def _kb_clear_cache():
    """清 ChromaDB 进程内缓存：让长驻 API 的后续向量查询能立刻看到新入库内容
    （count 本就即时，但 HNSW 段缓存对跨进程新写入会滞后）。"""
    try:
        from chromadb.api.shared_system_client import SharedSystemClient
        SharedSystemClient.clear_system_cache()
    except Exception:
        _log.warning("clear_system_cache failed", exc_info=True)


@app.get("/api/kb/status")
async def kb_status():
    """知识库概览：collection 名、块数、按 source_type 的来源分布。"""
    import chromadb
    from rag_tools import get_collection_name
    try:
        name = get_collection_name()
        client = chromadb.PersistentClient(path=os.path.join(BASE_DIR, "chroma_db"))
        try:
            col = client.get_collection(name)
        except Exception:
            return {"status": "ok", "collection": name, "chunks": 0, "sources": {}}
        sources = {}
        try:
            got = col.get(include=["metadatas"])
            for m in (got.get("metadatas") or []):
                st = (m or {}).get("source_type", "unknown")
                sources[st] = sources.get(st, 0) + 1
        except Exception:
            pass
        return {"status": "ok", "collection": name, "chunks": col.count(), "sources": sources}
    except Exception as e:
        _log.exception("kb_status failed")
        raise HTTPException(status_code=500, detail=f"读取知识库状态失败: {str(e)}")


@app.get("/api/kb/pending")
async def kb_pending():
    """待人工确认的候选清单（已落 _pending、尚未入库）。"""
    try:
        from knowledge_crawler import cmd_list_pending, BASE_DIR as KC_BASE
        out = cmd_list_pending()
        for it in out.get("items", []):
            if it.get("saved_abs"):
                it["saved"] = os.path.relpath(it["saved_abs"], KC_BASE)
        return out
    except Exception as e:
        _log.exception("kb_pending failed")
        raise HTTPException(status_code=500, detail=f"读取待审列表失败: {str(e)}")


@app.post("/api/kb/add_url")
async def kb_add_url(req: KBAddUrlRequest):
    """① 抓取 URL → 打分 → 落 _pending（待确认），不直接入库。
    命中登录/安全验证墙时返回 400 + 明确提示（同 /api/discover）。"""
    import asyncio
    url = (req.url or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="url 不能为空")
    try:
        from knowledge_crawler import cmd_crawl
        loop = asyncio.get_event_loop()
        out = await loop.run_in_executor(None, lambda: cmd_crawl(url))
        return out  # status: ok / rejected / error，前端据此展示
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _log.exception("kb_add_url failed")
        raise HTTPException(status_code=500, detail=f"抓取失败: {str(e)}")


@app.post("/api/kb/add_file")
async def kb_add_file(req: KBAddFileRequest):
    """① 接收本地 .md/.txt（base64 或纯文本）→ 打分 → 落 _pending（待确认）。
    用户主动上传，故即便相关性偏低也保留（降级 C 供确认）。"""
    import asyncio
    name = (req.name or "upload.md").strip()
    ext = os.path.splitext(name)[1].lower()
    if ext not in (".md", ".txt", ".markdown"):
        raise HTTPException(status_code=400, detail=f"仅支持 .md/.txt/.markdown，收到 {ext or name}")
    text = req.text or ""
    if not text and req.content_base64:
        try:
            text = base64.b64decode(req.content_base64).decode("utf-8", errors="replace")
        except Exception:
            raise HTTPException(status_code=400, detail="文件内容解码失败（需 UTF-8 文本）")
    if not text.strip():
        raise HTTPException(status_code=400, detail="文件内容为空")
    try:
        from knowledge_crawler import _score_and_save
        loop = asyncio.get_event_loop()
        out = await loop.run_in_executor(
            None,
            lambda: _score_and_save(text, url=f"(本地上传:{name})", origin="本地上传", force_keep=True),
        )
        return out
    except Exception as e:
        _log.exception("kb_add_file failed")
        raise HTTPException(status_code=500, detail=f"处理上传失败: {str(e)}")


@app.post("/api/kb/promote")
async def kb_promote(req: KBPromoteRequest):
    """② 人工确认后：把 _pending 文件提升到正式子目录并**增量入库**（不重建）。
    返回入库前后块数；清进程缓存让 Web 查询即时可见。"""
    import asyncio
    pending = (req.pending_file or "").strip()
    subdir = (req.to_subdir or "").strip()
    if not pending or not subdir:
        raise HTTPException(status_code=400, detail="pending_file 与 to_subdir 必填")
    try:
        from knowledge_crawler import cmd_promote, VALID_SUBDIRS
        if subdir not in VALID_SUBDIRS:
            raise HTTPException(status_code=400, detail=f"to_subdir 必须是 {sorted(VALID_SUBDIRS)} 之一")
        before = _kb_count()
        loop = asyncio.get_event_loop()
        out = await loop.run_in_executor(
            None, lambda: cmd_promote(pending, subdir, ingest=True)
        )
        if out.get("status") != "ok":
            raise HTTPException(status_code=400, detail=out.get("error", "提升失败"))
        _kb_clear_cache()  # 让本进程后续向量查询能看到新入库内容
        after = _kb_count()
        out["chunks_before"] = before
        out["chunks_after"] = after
        out["chunks_added"] = max(0, after - before)
        return out
    except HTTPException:
        raise
    except Exception as e:
        _log.exception("kb_promote failed")
        raise HTTPException(status_code=500, detail=f"入库失败: {str(e)}")


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
    api_key, api_key_env = _active_llm_api_key()
    if not api_key:
        raise HTTPException(status_code=500, detail=f"{api_key_env} 未配置")
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
    api_key, api_key_env = _active_llm_api_key()
    if not api_key:
        raise HTTPException(status_code=500, detail=f"{api_key_env} 未配置")
    from plan_gen import (
        prepare_plan_messages, call_llm_stream, save_plan,
        append_resources_appendix,
    )
    gaps = _resolve_plan_gaps(req.gaps)
    # 统一入口：读依赖 + RAG 检索资源 + 组装 messages（与 CLI / 非流式一致）
    messages, resources = prepare_plan_messages(gaps)

    async def generate():
        loop = asyncio.get_event_loop()
        q: asyncio.Queue = asyncio.Queue()
        full_text = []

        def _producer():
            try:
                for tok in call_llm_stream(messages, api_key, max_tokens=3500):
                    full_text.append(tok)
                    loop.call_soon_threadsafe(q.put_nowait, ("tok", tok))
                raw = "".join(full_text)
                # 退化产物（拒绝/无周结构）不落盘，避免污染"当前计划"被后续注入自我复制
                from plan_gen import is_degenerate_plan
                if is_degenerate_plan(raw):
                    loop.call_soon_threadsafe(q.put_nowait, ("done", ""))
                    return
                # 流结束后：确定性追加参考资源附录，再落盘
                plan_md = append_resources_appendix(raw, resources)
                # 把附录部分也作为最后一段 token 推给前端
                appendix = plan_md[len(raw):]
                if appendix:
                    loop.call_soon_threadsafe(q.put_nowait, ("tok", appendix))
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
    """SSE 流式问答（知识库优先 · 带门槛 · 与 /api/query 同一套 rag_gate）。

    先推 meta（in_kb / mode / sources），再逐 token 推 delta：
    - 命中知识库 → 基于 KB 合成 + 标出处；
    - 未命中 → 通用知识 + 项目先验兜底，开头带"非知识库"标注。
    用 qwen-turbo 合成，首字延迟低、体感快。
    """
    from rag_gate import gated_query_stream
    rid = current_request_id()
    _log.info(f"stream start q={req.query[:60]!r}")

    def gen():
        try:
            for ev in gated_query_stream(req.query, req.top_k):
                t = ev.get("type")
                if t == "meta":
                    meta = {k: ev[k] for k in
                            ("in_kb", "mode", "sources", "matched_by", "best_distance") if k in ev}
                    meta["request_id"] = rid
                    yield f"event: meta\ndata: {json.dumps(meta, ensure_ascii=False)}\n\n"
                elif t == "delta":
                    yield f"data: {json.dumps({'delta': ev.get('text', '')}, ensure_ascii=False)}\n\n"
                elif t == "done":
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
async def ui_console(request: Request):
    """求职流程 Stepper 控制台（Phase 3）。"""
    if not request.url.query:
        return RedirectResponse(
            url=f"/ui/console?rev={_static_rev('console.html')}",
            status_code=307,
            headers=HTML_NO_CACHE_HEADERS,
        )
    return _html_file_response("console.html")


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


@app.post("/api/agent", response_model=AgentResponse)
async def agent_run(req: AgentRequest):
    """ReAct Agent：一句自然语言 → tool 调用 → 结论（V4 §3）。

    mode='deterministic'（默认）：纯关键词路由，无 KEY 也能用，秒级返回。
    mode='llm'：function calling 工具循环，无 KEY 自动降级到 deterministic。
    """
    try:
        from react_agent import run as agent_run_fn
        out = agent_run_fn(req.message, mode=req.mode, max_steps=req.max_steps)
        return AgentResponse(**out)
    except Exception as e:
        _log.exception("agent_run failed")
        raise HTTPException(status_code=500, detail=f"agent 执行失败: {str(e)}")


# =====================================================
# Observability：trace + 重放（V4 §4）
# =====================================================

@app.get("/api/trace")
async def trace_list(limit: int = 20):
    """列出最近 N 条 CareerFlow trace（按 mtime 倒序）。"""
    from observability import list_traces
    return {"items": list_traces(limit=limit)}


@app.get("/api/trace/{trace_id}")
async def trace_detail(trace_id: str):
    """读回单条 trace 的全部 JSONL 事件。"""
    from observability import read_trace
    try:
        return read_trace(trace_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"trace 不存在: {trace_id}")


@app.post("/api/flow/run_traced", response_model=FlowRunResponse)
async def flow_run_traced(req: FlowRunRequest):
    """跑 routed CareerFlow 并落 trace 文件，返回 state（含 _trace_id）。"""
    from observability import trace_career_flow
    try:
        out = trace_career_flow(
            req.jd_text, jd_title=req.jd_title, skip_llm=req.skip_llm,
            routed=True,
        )
        return FlowRunResponse(
            match_report=out.get("match_report", {}),
            gaps=out.get("gaps", {}),
            plan_outline=out.get("plan_outline", []),
            today_advice=out.get("today_advice", {}),
            resume_skeleton=out.get("resume_skeleton", {}),
            application_suggestion=out.get("application_suggestion", {}),
            requires_confirmation=out.get("requires_confirmation", []),
            trace=out.get("trace", []) + [{"_trace_id": out["_trace_id"]}],
            errors=out.get("errors", []),
        )
    except Exception as e:
        _log.exception("flow_run_traced failed")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# 启动入口
# =====================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
