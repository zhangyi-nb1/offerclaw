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


def fetch_url(url: str, timeout: int = 15) -> str:
    """从 URL 抓正文（V2 占位实现：直接 requests + 去 HTML 标签）。"""
    import requests
    r = requests.get(url, timeout=timeout, headers={
        "User-Agent": "Mozilla/5.0 OfferClaw-JD-Reader",
    })
    r.raise_for_status()
    html = r.text
    # 极简版：去脚本/样式/标签
    html = re.sub(r"<script.*?</script>", "", html, flags=re.S | re.I)
    html = re.sub(r"<style.*?</style>", "", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", "\n", html)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def discover(raw: str = "", url: str = "") -> Dict[str, object]:
    """统一入口：raw 优先，否则 fetch_url(url)。返回结构化 JD。"""
    if not raw and not url:
        raise ValueError("raw 与 url 至少给一个")
    text = raw or fetch_url(url)
    parsed = extract_jd(text)
    parsed["source_url"] = url
    parsed["jd_text"] = text  # 透传给前端，方便直接喂给 /api/match
    return parsed


if __name__ == "__main__":
    import json, sys
    sample = sys.stdin.read() if not sys.stdin.isatty() else "岗位名称：LLM 实习生\n公司：测试\n地点：上海\n要求：Python / RAG / FastAPI"
    print(json.dumps(discover(raw=sample), ensure_ascii=False, indent=2))
