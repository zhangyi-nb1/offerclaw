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
    """从 URL 抓正文（对 JS 渲染 SPA 给出明确降级提示）。"""
    import requests
    r = requests.get(url, timeout=timeout, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124",
        "Accept-Language": "zh-CN,zh;q=0.9",
    })
    r.raise_for_status()
    html = r.text

    # 尝试解析：meta description / og:description
    import re as _re
    meta = (_re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', html, _re.I)
            or _re.search(r'<meta[^>]+content=["\'](.*?)["\'][^>]+name=["\']description["\']', html, _re.I))
    og = (_re.search(r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\'](.*?)["\']', html, _re.I))
    og_title = (_re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](.*?)["\']', html, _re.I))

    # 去 script/style，保留正文
    clean = _re.sub(r"<script.*?</script>", "", html, flags=_re.S | _re.I)
    clean = _re.sub(r"<style.*?</style>", "", clean, flags=_re.S | _re.I)
    clean = _re.sub(r"<[^>]+>", "\n", clean)
    clean = _re.sub(r"\n{3,}", "\n\n", clean).strip()

    # SPA 检测：有效正文不足 200 字符 → 该页是 JS 渲染
    if len(clean) < 200:
        og_title_text = og_title.group(1).strip() if og_title else ""
        # 只有 og:title 指向具体职位时才做部分回退（否则 meta desc 是公司通用描述，无用）
        if og_title_text and len(og_title_text) > 5:
            desc = (og.group(1).strip() if og else "") or ""
            return f"（自动抓取到部分信息，可能不完整）\n\n岗位标题：{og_title_text}\n摘要：{desc}\n\n注意：该页为 JS 渲染，完整 JD 请手动复制后粘贴。"
        raise ValueError(
            "SPA_PAGE: 该招聘页面由 JavaScript 动态渲染（如字节/阿里/腾讯等大厂招聘网站），"
            "简单 HTTP 请求无法获取职位详情。\n\n"
            "解决方法（30 秒）：\n"
            "1. 在浏览器打开该链接\n"
            "2. 等页面完全加载后，按 Ctrl+A 全选页面文字\n"
            "3. Ctrl+C 复制\n"
            "4. 粘贴到左边的 JD 文本框，再点 [ 开始匹配 ]"
        )
    return clean


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
