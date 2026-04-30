# -*- coding: utf-8 -*-
"""
OfferClaw · 主动求职 / JD 抽取助手 (job_discovery.py)

V2 阶段四职责：
    把"用户给的 JD 原文（粘贴或 URL 抓取）"快速整理成
    结构化 JD（公司 / 岗位 / 地点 / 职责 / 要求 / 工作性质），
    供 /api/discover 直接消费。

设计取舍：
    - V1：用户给 JD 原文（最快、最稳）
    - V2：用户给 URL，本脚本用 requests + 简单 readability 抓正文（不在本阶段实现，留接口）
    - 不做爬虫遍历招聘网站（违反 V2 报告 §七 任务四"半自动 不自动"）
    - 抽取用规则 + 关键字匹配优先；若用户传入 use_llm=True 才走 LLM（v1 默认关闭，秒级）
"""

import re
from typing import Dict, List, Optional


_LOC_HINT = re.compile(r"(?:工作地点|地点|Location|城市)[：: ]+([^\n，,；;]+)")
_TYPE_HINT = re.compile(r"(?:岗位性质|工作性质|招聘类型|类型)[：: ]+([^\n，,；;]+)")
_TITLE_HINT = re.compile(r"(?:岗位名称|职位名称|职位|岗位)[：: ]+([^\n，,；;]+)")
_COMPANY_HINT = re.compile(r"(?:公司|公司名称|招聘公司|Company)[：: ]+([^\n，,；;]+)")

_SKILL_KEYWORDS = [
    "Python","Java","Go","Rust","TypeScript","JavaScript","C++","SQL",
    "RAG","LangGraph","LangChain","LlamaIndex","FastAPI","Flask",
    "PyTorch","TensorFlow","Transformer","Embedding","LoRA","Prompt",
    "MCP","Agent","Vector","Chroma","Milvus","Faiss","HuggingFace",
    "Docker","Kubernetes","Linux","Git","CI/CD","AWS","Azure",
    "MySQL","PostgreSQL","Redis","Kafka","MongoDB",
]


def _first_match(pat: re.Pattern, text: str) -> str:
    m = pat.search(text)
    return m.group(1).strip() if m else ""


def extract_jd(raw: str) -> Dict[str, object]:
    """从粘贴的 JD 原文里规则化抽取结构化字段。"""
    raw = raw.strip()
    company = _first_match(_COMPANY_HINT, raw)
    title = _first_match(_TITLE_HINT, raw)
    location = _first_match(_LOC_HINT, raw)
    job_type = _first_match(_TYPE_HINT, raw)

    # 技能关键字命中
    hits: List[str] = []
    lower = raw.lower()
    for kw in _SKILL_KEYWORDS:
        if kw.lower() in lower and kw not in hits:
            hits.append(kw)

    # 抽职责段（"职位描述 / 工作职责 / 岗位职责"开头到下一个段落）
    duties = ""
    m = re.search(r"(?:工作职责|岗位职责|职位描述|Responsibilities)[：: ]*\n?(.{20,800}?)(?=\n(?:任职要求|岗位要求|职位要求|Requirements|要求|$))",
                  raw, re.DOTALL)
    if m: duties = m.group(1).strip()

    requirements = ""
    m = re.search(r"(?:任职要求|岗位要求|职位要求|Requirements)[：: ]*\n?(.{20,1200}?)(?=\n##|\Z)",
                  raw, re.DOTALL)
    if m: requirements = m.group(1).strip()

    return {
        "company": company,
        "title": title,
        "location": location,
        "job_type": job_type,
        "skills_detected": hits,
        "duties": duties,
        "requirements": requirements,
        "raw_chars": len(raw),
    }


def _strip_html(html: str) -> str:
    """去掉 script/style/标签，保留可读正文。"""
    import re as _re
    clean = _re.sub(r"<script.*?</script>", "", html, flags=_re.S | _re.I)
    clean = _re.sub(r"<style.*?</style>", "", clean, flags=_re.S | _re.I)
    clean = _re.sub(r"<[^>]+>", "\n", clean)
    clean = _re.sub(r"[ \t]+", " ", clean)
    clean = _re.sub(r"\n{3,}", "\n\n", clean).strip()
    return clean


def _fetch_with_playwright(url: str, timeout_ms: int = 30000) -> str:
    """用 Playwright 无头 Chromium 渲染页面，返回可读正文。"""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="zh-CN",
        )
        page = ctx.new_page()
        # networkidle：等网络静止 500ms（确保动态内容加载完毕）
        page.goto(url, wait_until="networkidle", timeout=timeout_ms)
        # 部分招聘站点会跳转登录页，尝试等待岗位正文容器出现
        for selector in ["[class*='job']", "[class*='position']", "[class*='jd']",
                         "main", "article", "#content", ".detail"]:
            try:
                page.wait_for_selector(selector, timeout=3000)
                break
            except Exception:
                continue
        text = page.inner_text("body")
        browser.close()
    return text.strip()


def fetch_url(url: str, timeout: int = 20) -> str:
    """从 URL 抓取 JD 正文。
    策略：
    1. 先用轻量 requests 快速抓取（静态页直接返回）
    2. 若正文 < 300 字（典型 SPA）→ 自动启动 Playwright 无头浏览器渲染
    3. Playwright 也失败 → 抛出清晰错误
    """
    import requests
    import re as _re

    try:
        r = requests.get(url, timeout=timeout, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        r.raise_for_status()
        clean = _strip_html(r.text)
    except Exception as req_err:
        clean = ""  # requests 失败也走 playwright

    # 静态页内容充足，直接返回
    if len(clean) >= 300:
        return clean

    # SPA / 动态页：启动无头浏览器
    try:
        text = _fetch_with_playwright(url, timeout_ms=timeout * 1500)
        if len(text) < 50:
            raise ValueError("页面内容为空，可能需要登录或地区限制")
        return text
    except Exception as pw_err:
        raise ValueError(
            f"无法自动抓取该页面内容（可能需要登录、验证码或地区限制）。\n"
            f"错误详情：{pw_err}\n\n"
            "建议：在浏览器手动打开页面，全选复制 JD 文字后粘贴到左侧文本框。"
        )


def _classify_source(url: str, raw: str) -> tuple[str, str]:
    """根据 URL 域名判断来源类型与可信度（A/B/C，与 source_policy.md 对齐）。

    Returns:
        (source_type, source_credibility)
        source_type ∈ {"official", "platform", "manual_paste", "unknown"}
        source_credibility ∈ {"A", "B", "C"}
    """
    if not url and raw:
        return "manual_paste", "B"
    u = (url or "").lower()
    # A 级：公司官网 / 官方招聘门户
    official_domains = ("jobs.bytedance.com", "talent.alibaba.com", "careers.tencent.com",
                        "campus.baidu.com", "nio.jobs.feishu.cn", "join.jd.com",
                        "career.huawei.com", "jobs.netease.com", "jobs.didiglobal.com",
                        "campus.meituan.com", "talent.kuaishou.com", "careers.bilibili.com",
                        ".feishu.cn/", "/careers", "/jobs/")
    for d in official_domains:
        if d in u:
            return "official", "A"
    # B 级：第三方招聘平台
    platform_domains = ("zhipin.com", "lagou.com", "linkedin.com", "liepin.com",
                        "51job.com", "zhaopin.com", "maimai.cn", "greenhouse.io",
                        "lever.co", "ashbyhq.com", "workable.com")
    for d in platform_domains:
        if d in u:
            return "platform", "B"
    return "unknown", "C"


def discover(raw: str = "", url: str = "") -> Dict[str, object]:
    """统一入口：raw 优先，否则 fetch_url(url)。返回结构化 JD。

    输出新增字段：
        source_type: official / platform / manual_paste / unknown
        source_credibility: A (官网) / B (招聘平台) / C (未知/匿名)
        notice: 不登录、不批量抓取、不自动投递 — 见 docs/ethical_use.md
    """
    if not raw and not url:
        raise ValueError("raw 与 url 至少给一个")
    text = raw or fetch_url(url)
    parsed = extract_jd(text)
    parsed["source_url"] = url
    parsed["jd_text"] = text  # 透传给前端，方便直接喂给 /api/match
    src_type, src_cred = _classify_source(url, raw)
    parsed["source_type"] = src_type
    parsed["source_credibility"] = src_cred
    parsed["notice"] = "OfferClaw 仅做半自动抽取：不登录、不批量、不自动投递。最终录入 applications.md 需用户确认。"
    return parsed


if __name__ == "__main__":
    import json, sys
    sample = sys.stdin.read() if not sys.stdin.isatty() else "岗位名称：LLM 实习生\n公司：测试\n地点：上海\n要求：Python / RAG / FastAPI"
    print(json.dumps(discover(raw=sample), ensure_ascii=False, indent=2))


# =====================================================================
# Phase 4：JD Discovery 增强 —— query_builder + ranker
# =====================================================================

def build_search_queries(profile: dict | None = None, max_queries: int = 6) -> List[str]:
    """根据 profile 生成搜索关键词组合（不去爬，仅供用户复制到搜索引擎）。"""
    if profile is None:
        from profile_loader import load_profile
        profile = load_profile()
    cities = profile.get("可接受地域") or ["上海", "南京"]
    directions = profile.get("方向优先级") or ["AI 应用开发"]
    skills = (profile.get("熟练技能") or [])[:3]
    work_type = "实习" if "实习" in (profile.get("求职性质") or "实习") else "校招"

    queries: List[str] = []
    for d in directions[:3]:
        for c in cities[:2]:
            base = f"{d} {work_type} {c}"
            if skills:
                base += " " + " ".join(skills)
            queries.append(base.strip())
            if len(queries) >= max_queries:
                return queries
    return queries


def rank_candidates(candidates: List[Dict], profile: dict | None = None) -> List[Dict]:
    """对候选 JD 列表调用 match_job，返回带 status/direction/score 的排序结果。

    candidates: [{"title": str, "jd_text": str}, ...]
    返回排序后的 [{...原字段, "status", "direction", "score", "reason"}]
    """
    from match_job import run_match, format_report
    if profile is None:
        from profile_loader import load_profile
        profile = load_profile()

    _ORDER = {"当前适合投递": 3, "中长期可转向": 2,
              "信息不足，建议补充后再判断": 1, "当前暂不建议投递": 0}

    out = []
    for c in candidates:
        jd_text = c.get("jd_text", "")
        title = c.get("title", "未命名")
        try:
            r = run_match(profile, jd_text, jd_title=title)
            status = r.conclusion or ""
            direction = r.direction or ""
            gaps = sum(len(v or []) for v in (r.gap_list or {}).values())
            reason = (r.conclusion_reason or format_report(r) or "")[:140]
        except Exception as e:
            status, direction, gaps, reason = "error", "", 99, str(e)
        out.append({
            **c,
            "status": status,
            "direction": direction,
            "gap_count": gaps,
            "score": _ORDER.get(status, 0),
            "reason": reason,
        })
    out.sort(key=lambda x: (-x["score"], x.get("gap_count", 99)))
    return out
