# -*- coding: utf-8 -*-
"""knowledge_crawler.py — OfferClaw 半自动知识采集（P4）

定位（与 doc2kb 互补，不重复造轮子）：
    - doc2kb：抓取**需登录/浏览器渲染**的飞书/Notion 文档树（带层级、图片）。
    - 本工具：抓取**公开网页文章**（掘金/知乎专栏/博客等），并加一道
      **LLM 质量门**——按"大模型应用工程师"相关度 / 信息密度 / 时效打分，
      A/B 级落入 _pending 待人工确认，再用 promote 提升到正式知识库。

设计原则：
    - 复用 job_discovery.fetch_url（requests + Playwright 兜底）抓正文。
    - 复用 day1_api_starter 的 LLM 配置打分。
    - 一切落盘到 knowledge_base/_pending/web/，绝不直接进正式库（人在回路）。
    - 纯逻辑（slug / frontmatter / 评分解析 / 提升路径）可离线单测。

用法：
    python knowledge_crawler.py crawl <url>                      # 抓取 + 打分 → _pending/web/
    python knowledge_crawler.py score <pending_file.md>          # 重新打分
    python knowledge_crawler.py promote <pending_file.md> --to learning_resources
"""

import argparse
import datetime
import json
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

KB_DIR = os.path.join(BASE_DIR, "knowledge_base")
PENDING_WEB_DIR = os.path.join(KB_DIR, "_pending", "web")
TARGET_ROLE = "大模型应用工程师"
VALID_SUBDIRS = {"career_paths", "experience_posts", "learning_resources"}
SUBDIR_SOURCE_TYPE = {
    "career_paths": "career_knowledge",
    "experience_posts": "experience",
    "learning_resources": "resource",
}
SOURCE_TYPE_TO_SUBDIR = {v: k for k, v in SUBDIR_SOURCE_TYPE.items()}


# =====================================================
# 纯逻辑（可离线单测）
# =====================================================

def slugify(text: str, maxlen: int = 40) -> str:
    """把标题/URL 压成文件名安全的 slug。"""
    text = re.sub(r"https?://", "", text or "")
    text = re.sub(r"[^\w一-鿿]+", "_", text).strip("_").lower()
    return text[:maxlen] or "untitled"


def build_frontmatter(meta: dict) -> str:
    """生成 YAML frontmatter 字符串。tags 用 JSON 数组写法。"""
    lines = ["---"]
    for k in ["title", "source_url", "crawl_date", "quality", "target_role",
              "source_type", "review_status", "score_relevance", "score_density",
              "score_recency_ok", "score_reason"]:
        if k not in meta:
            continue
        v = meta[k]
        if isinstance(v, bool):
            v = "true" if v else "false"
        lines.append(f'{k}: "{v}"' if isinstance(v, str) else f"{k}: {v}")
    if meta.get("tags"):
        lines.append("tags: " + json.dumps(meta["tags"], ensure_ascii=False))
    lines.append("---")
    return "\n".join(lines)


def parse_frontmatter(text: str) -> dict:
    """从一篇 .md 解析 frontmatter（简单 KV，足够本工具用）。"""
    if not text.lstrip().startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    meta = {}
    for ln in parts[1].splitlines():
        m = re.match(r"^(\w+):\s*(.+)$", ln.strip())
        if m:
            key, val = m.group(1), m.group(2).strip().strip('"')
            meta[key] = val
    return meta


def parse_score(llm_text: str) -> dict:
    """从 LLM 输出里鲁棒解析评分 JSON；失败给保守默认（C / 待审）。"""
    m = re.search(r"```json\s*(\{.*?\})\s*```", llm_text, re.DOTALL) or \
        re.search(r"(\{.*\})", llm_text, re.DOTALL)
    data = {}
    if m:
        try:
            data = json.loads(m.group(1))
        except Exception:
            data = {}
    grade = str(data.get("grade", "C")).upper()
    if grade not in {"A", "B", "C", "REJECT"}:
        grade = "C"
    subdir = data.get("suggested_subdir", "learning_resources")
    if subdir not in VALID_SUBDIRS:
        subdir = "learning_resources"
    return {
        "grade": grade,
        "relevance": int(data.get("relevance", 0) or 0),
        "density": int(data.get("density", 0) or 0),
        "recency_ok": bool(data.get("recency_ok", True)),
        "reason": str(data.get("reason", "") or ""),
        "suggested_subdir": subdir,
        "suggested_title": str(data.get("suggested_title", "") or ""),
    }


# =====================================================
# LLM 质量打分
# =====================================================

_SCORE_PROMPT = """你是 OfferClaw 的知识库质量审核员。请评估下面这篇网页内容对一个
正在求职「{role}」的人是否值得收进学习知识库。

只输出一个 ```json 代码块，字段：
{{
  "grade": "A|B|C|reject",   // A=高质量干货 B=有参考价值 C=一般 reject=广告/无关/低质
  "relevance": 0-10,          // 与 {role} 方向相关度
  "density": 0-10,            // 信息密度（有无具体技术/步骤）
  "recency_ok": true|false,   // 内容是否未明显过时
  "reason": "一句话理由",
  "suggested_subdir": "career_paths|experience_posts|learning_resources",
  "suggested_title": "一个简洁中文标题"
}}

内容（截断）：
{content}
"""


def score_content(text: str, title: str = "") -> dict:
    """调 LLM 给内容打质量分。无 key / 失败 → 返回保守 C 档。"""
    try:
        import requests
        from day1_api_starter import get_llm_config, build_zhipu_jwt, load_local_env
        load_local_env()
        cfg = get_llm_config()
        api_key = cfg["api_key"]
        if not api_key:
            return {**parse_score(""), "reason": "无 LLM key，未打分，保守置 C"}
        prompt = _SCORE_PROMPT.format(role=TARGET_ROLE, content=text[:4000])
        bearer = build_zhipu_jwt(api_key) if cfg["is_zhipu"] else api_key
        payload = {
            "model": cfg["model"],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1, "max_tokens": 400,
        }
        if cfg.get("reasoning_effort"):
            payload["reasoning_effort"] = cfg["reasoning_effort"]
        resp = requests.post(
            f"{cfg['api_base']}/chat/completions",
            headers={"Authorization": f"Bearer {bearer}", "Content-Type": "application/json"},
            json=payload, timeout=60,
        )
        resp.raise_for_status()
        out = resp.json()["choices"][0]["message"].get("content", "") or ""
        return parse_score(out)
    except Exception as e:
        return {**parse_score(""), "reason": f"打分失败({e})，保守置 C"}


# =====================================================
# 命令
# =====================================================

def content_stats(text: str) -> dict:
    """正文统计，供审核判断"采集是否完整/有无链接堆砌"。"""
    import re
    lines = [l for l in text.splitlines() if l.strip()]
    link_lines = sum(1 for l in lines if "http" in l or "](" in l)
    images = sum(1 for l in lines if l.strip().startswith("!["))
    return {
        "chars": len(text),
        "lines": len(lines),
        "link_pct": (link_lines * 100 // max(len(lines), 1)),
        "images": images,
    }


def content_preview(text: str, head: int = 12, tail: int = 6) -> dict:
    """取正文开头/结尾若干行，便于人工判断有没有截断、缺内容。"""
    lines = [l for l in text.splitlines() if l.strip()]
    return {
        "head": "\n".join(lines[:head]),
        "tail": "\n".join(lines[-tail:]) if len(lines) > head else "",
        "truncated_middle": max(0, len(lines) - head - tail),
    }


def redact_secrets(text: str) -> tuple:
    """把采集到的正文里**疑似密钥/令牌**打码，避免把第三方泄露的 key 入库甚至推到仓库。

    返回 (脱敏后文本, 命中数)。覆盖 OpenAI/通用 sk-、AWS AKIA、GitHub ghp_/gho_ 等常见模式。
    保守匹配，避免误伤正文。
    """
    patterns = [
        r"sk-[A-Za-z0-9_\-]{20,}",          # OpenAI / 兼容
        r"AKIA[0-9A-Z]{16}",                # AWS Access Key
        r"gh[pousr]_[A-Za-z0-9]{30,}",      # GitHub tokens
        r"AIza[0-9A-Za-z_\-]{30,}",         # Google API key
        r"xox[baprs]-[A-Za-z0-9\-]{10,}",   # Slack
    ]
    n = 0
    for pat in patterns:
        text, c = re.subn(pat, "[REDACTED_SECRET]", text)
        n += c
    return text, n


def _score_and_save(text: str, url: str, origin: str, force_keep: bool = False) -> dict:
    """对一段正文打分并存入 _pending/web/（reject 不落盘）。

    crawl（requests/Playwright）与 from-text（浏览器插件采集）共用此后处理，
    保证两条采集轨道走同一质量门 + 同一落盘格式。``origin`` 记入 tags 便于溯源。
    采集内容会先做**密钥脱敏**（第三方文档常含泄露 key），再打分落盘。

    ``force_keep=True``（用户主动上传的本地文档）：即便相关性判为 REJECT 也仍落盘
    （降级为 C 档供人工确认），尊重"用户自己选的资料"；但真正空/过短仍拒绝。

    返回里**显式带上来源 URL、本地绝对路径、采集统计、内容预览**，
    方便审核：①点 source_url 看来源质量 ②开 saved_abs 看采集是否完整。
    """
    import hashlib
    os.makedirs(PENDING_WEB_DIR, exist_ok=True)
    text, _redacted = redact_secrets(text or "")
    if not text or len(text.strip()) < 80:
        return {"status": "rejected", "source_url": url, "grade": "REJECT",
                "reason": "正文过短或为空", "saved": None, "saved_abs": None,
                "next": "内容不足，未入 _pending"}
    score = score_content(text)
    if score["grade"] == "REJECT" and not force_keep:
        return {"status": "rejected", "source_url": url, "grade": "REJECT",
                "reason": score["reason"], "saved": None, "saved_abs": None,
                "next": "内容无效/无关，已丢弃，未入 _pending"}
    if score["grade"] == "REJECT":  # force_keep：降级 C 仍落盘
        score = {**score, "grade": "C",
                 "suggested_subdir": score.get("suggested_subdir") or "learning_resources",
                 "suggested_title": score.get("suggested_title") or "",
                 "reason": f"用户主动上传（原判：{score.get('reason','')}）"}

    title = score["suggested_title"] or slugify(url, 30)
    today = datetime.date.today().isoformat()
    uhash = hashlib.md5((url or text[:50]).encode("utf-8")).hexdigest()[:6]
    meta = {
        "title": title, "source_url": url or "(browser-capture)", "crawl_date": today,
        "quality": score["grade"], "target_role": TARGET_ROLE,
        "source_type": SUBDIR_SOURCE_TYPE[score["suggested_subdir"]],
        "review_status": "pending",
        "score_relevance": score["relevance"], "score_density": score["density"],
        "score_recency_ok": score["recency_ok"], "score_reason": score["reason"],
        "tags": [TARGET_ROLE, origin],
    }
    fname = f"{today}_{slugify(title)}_{uhash}.md"
    path = os.path.join(PENDING_WEB_DIR, fname)
    body = f"\n# {title}\n\n> 来源：{url or '(browser-capture)'}\n> 建议归类：{score['suggested_subdir']}\n\n{text.strip()}\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(build_frontmatter(meta) + "\n" + body)
    return {
        "status": "ok",
        "title": title,
        "source_url": url or "(browser-capture)",          # ① 审核：来源质量
        "saved": os.path.relpath(path, BASE_DIR),
        "saved_abs": path,                                  # ② 审核：打开看采集质量
        "grade": score["grade"], "relevance": score["relevance"],
        "density": score["density"], "reason": score["reason"],
        "suggested_subdir": score["suggested_subdir"],
        "stats": content_stats(text),
        "preview": content_preview(text),
        "next": f"审核：先看 source_url 判断来源；再开 saved_abs 看采集是否完整。"
                f"满意后 promote --to {score['suggested_subdir']}",
    }


# =====================================================
# GitHub 仓库采集（抓真正的教程内容，而非只抓 README）
# =====================================================

import re as _re

_GH_SKIP_NAMES = {"license", "license.md", "contributing.md", "code_of_conduct.md",
                  "security.md", "_sidebar.md", "_coverpage.md", "_navbar.md", ".nojekyll"}
_GH_SKIP_PATH = (".ipynb_checkpoints", "node_modules/", "/.github/", "/test/", "/tests/")
_GH_MAX_FILES = 60
_GH_MAX_CHARS = 600_000


def parse_github_repo(url: str):
    """从各种 GitHub URL 解析出 (owner, repo)；非 GitHub 返回 None。

    支持 github.com/owner/repo[/...]、raw.githubusercontent.com/owner/repo/branch/...
    """
    m = _re.search(r"github\.com/([^/\s]+)/([^/\s#?]+)", url) or \
        _re.search(r"raw\.githubusercontent\.com/([^/\s]+)/([^/\s]+)", url)
    if not m:
        return None
    owner, repo = m.group(1), m.group(2)
    repo = repo.replace(".git", "")
    if owner in {"raw", "gist"}:
        return None
    return owner, repo


def is_github_repo_url(url: str) -> bool:
    """是否是"仓库级"URL（应抓全仓内容，而非单文件）。

    True：github.com/owner/repo 根、或指向 README 的 raw URL。
    False：raw URL 指向某个具体非 README 文件（单文件抓取即可）。
    """
    if not parse_github_repo(url):
        return False
    if "raw.githubusercontent.com" in url:
        return url.rstrip("/").lower().endswith("readme.md")
    # github.com/owner/repo[ 或 /tree/... ]，但不是 /blob/具体文件
    if "/blob/" in url:
        return url.rstrip("/").lower().endswith("readme.md")
    return True


def rewrite_image_links(content: str, owner: str, repo: str, branch: str, file_path: str) -> str:
    """把仓库内 markdown/html 图片的**相对路径**重写成 GitHub raw 绝对 URL，
    使采集后的资源在本地/UI 打开时图片仍能正常显示。

    相对路径相对于该文件所在目录解析（含 ../）；已是 http/data/锚点的保持不变。
    """
    import posixpath
    from urllib.parse import quote
    base_dir = posixpath.dirname(file_path)
    raw_prefix = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/"

    def to_abs(rel: str) -> str:
        rel = rel.strip().strip('"').strip("'")
        if rel.startswith(("http://", "https://", "data:", "//", "#", "mailto:")):
            return rel
        resolved = posixpath.normpath(posixpath.join(base_dir, rel))
        return raw_prefix + quote(resolved)

    # markdown ![alt](url "可选title")
    def md_img(m):
        return f"![{m.group(1)}]({to_abs(m.group(2))}{m.group(3) or ''})"
    content = _re.sub(r'!\[([^\]]*)\]\(([^)\s]+)(\s+[^)]*)?\)', md_img, content)
    # html <img ... src="url" ...>
    def html_img(m):
        return m.group(0).replace(m.group(1), to_abs(m.group(1)), 1)
    content = _re.sub(r'<img[^>]+src=["\']([^"\']+)["\']', html_img, content)
    return content


def _ipynb_to_text(raw_json: str) -> str:
    """从 .ipynb（JSON）提取 markdown + code 单元文本，丢弃输出。"""
    try:
        nb = json.loads(raw_json)
    except Exception:
        return ""
    out = []
    for cell in nb.get("cells", []):
        if cell.get("cell_type") not in ("markdown", "code"):
            continue
        src = cell.get("source", [])
        text = "".join(src) if isinstance(src, list) else str(src)
        if not text.strip():
            continue
        if cell.get("cell_type") == "code":
            out.append("```python\n" + text + "\n```")
        else:
            out.append(text)
    return "\n\n".join(out)


def _gh_list_content_files(owner: str, repo: str) -> tuple:
    """返回 (branch, [content_paths])。content = .md/.ipynb，过滤样板/校验/重复目录。"""
    import requests
    h = {"User-Agent": "offerclaw-kb", "Accept": "application/vnd.github+json"}
    r = requests.get(f"https://api.github.com/repos/{owner}/{repo}", timeout=20, headers=h)
    if r.status_code == 403:
        raise RuntimeError("GitHub API 限流（未认证 60/小时），稍后再试")
    r.raise_for_status()
    branch = r.json().get("default_branch", "main")
    t = requests.get(f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1",
                     timeout=30, headers=h)
    t.raise_for_status()
    blobs = [x["path"] for x in t.json().get("tree", []) if x.get("type") == "blob"]

    def keep(p: str) -> bool:
        low = p.lower()
        if not low.endswith((".md", ".markdown", ".ipynb")):
            return False
        if any(s in low for s in _GH_SKIP_PATH):
            return False
        if os.path.basename(low) in _GH_SKIP_NAMES:
            return False
        return True

    files = [p for p in blobs if keep(p)]
    # 去重：若存在 docs/ 内容目录，优先只用 docs/（避免 docs 与 notebook 重复章节）
    docs = [p for p in files if p.lower().startswith("docs/")]
    if len(docs) >= 3:
        files = docs
    return branch, sorted(files)


def fetch_repo_text(url: str) -> dict:
    """抓取 GitHub 仓库的内容文件（.md/.ipynb）并拼成一篇长文。

    返回 {status:"ok", text, repo, branch, files_captured, files_total_found}
    或 {status:"error", error}。供 crawl_repo（入知识库）与
    简历项目分析（/api/resume/project）等复用。
    """
    import requests
    parsed = parse_github_repo(url)
    if not parsed:
        return {"status": "error", "error": "不是可识别的 GitHub 仓库 URL"}
    owner, repo = parsed
    branch, files = _gh_list_content_files(owner, repo)
    if not files:
        return {"status": "error", "error": "仓库内未找到 .md/.ipynb 内容文件"}

    h = {"User-Agent": "offerclaw-kb"}
    parts, used, total = [], [], 0
    for path in files:
        if len(used) >= _GH_MAX_FILES or total >= _GH_MAX_CHARS:
            break
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
        try:
            rr = requests.get(raw_url, timeout=30, headers=h)
            if rr.status_code != 200:
                continue
            content = rr.text
            if path.lower().endswith(".ipynb"):
                content = _ipynb_to_text(content)
            # 相对图片路径 → GitHub raw 绝对 URL，保证图片可正常显示
            content = rewrite_image_links(content, owner, repo, branch, path)
            content = content.strip()
            if len(content) < 40:
                continue
            parts.append(f"\n\n## {path}\n\n{content}")
            used.append(path)
            total += len(content)
        except Exception:
            continue

    if not parts:
        return {"status": "error", "error": "内容文件抓取失败（网络/限流）"}

    repo_url = f"https://github.com/{owner}/{repo}"
    header = (f"# {repo} —— GitHub 仓库内容采集\n\n"
              f"> 仓库：{repo_url}（分支 {branch}）\n"
              f"> 已采集 {len(used)} 个内容文件，共 {total} 字\n")
    return {
        "status": "ok", "text": header + "".join(parts), "repo": repo_url,
        "branch": branch, "files_captured": len(used), "files_total_found": len(files),
    }


def crawl_repo(url: str) -> dict:
    """抓取整个 GitHub 仓库的**真实内容文件**（章节 .md / notebook），
    拼成一篇知识文档 → 打分 → _pending/web/。修复"只抓 README 简介"的缺陷。
    """
    fetched = fetch_repo_text(url)
    if fetched.get("status") != "ok":
        return fetched
    repo_url = fetched["repo"]
    result = _score_and_save(fetched["text"], repo_url, origin="github仓库采集")
    if result.get("status") == "ok":
        result["repo"] = repo_url
        result["files_captured"] = fetched["files_captured"]
        result["files_total_found"] = fetched["files_total_found"]
        result["captured_paths"] = used
    return result


def cmd_crawl(url: str) -> dict:
    """轨道1：抓公开 URL → 打分 → _pending/web/。

    若 URL 是 GitHub 仓库（或其 README），**自动改走整仓内容采集**（crawl_repo），
    避免只抓到 README 简介、漏掉真正的教程章节。
    """
    if is_github_repo_url(url):
        return crawl_repo(url)
    from job_discovery import fetch_url
    return _score_and_save(fetch_url(url), url, origin="web采集")


def cmd_from_text(url: str, text_file: str) -> dict:
    """轨道2：把浏览器插件（Claude-in-Chrome / doc2kb）从登录态/反爬页采集到的
    正文文本接入同一质量门 + 审核流水线。

    text_file：已采集正文的本地文件（.md/.txt）。url：原始页面地址（供溯源）。
    用法：浏览器插件读飞书/知乎等已渲染页面 → 存成文件 → from-text → _pending → 审核 → promote。
    """
    src = text_file if os.path.isabs(text_file) else os.path.join(BASE_DIR, text_file)
    if not os.path.exists(src):
        return {"status": "error", "error": f"文件不存在：{text_file}"}
    with open(src, encoding="utf-8") as f:
        text = f.read()
    return _score_and_save(text, url, origin="浏览器采集")


def cmd_promote(pending_file: str, to_subdir: str, ingest: bool = False) -> dict:
    """把审核通过的 _pending 文件提升到正式知识库子目录。

    ``ingest=True`` 时**增量**入库（rag_ingest --add，不重建、不影响原有内容），
    提升后立即可检索；否则只移动文件，由调用方稍后增量入库。
    """
    if to_subdir not in VALID_SUBDIRS:
        return {"status": "error", "error": f"--to 必须是 {sorted(VALID_SUBDIRS)} 之一"}
    src = pending_file if os.path.isabs(pending_file) else os.path.join(BASE_DIR, pending_file)
    if not os.path.exists(src):
        return {"status": "error", "error": f"文件不存在：{pending_file}"}
    with open(src, encoding="utf-8") as f:
        content = f.read()
    meta = parse_frontmatter(content)
    # 提升时修正 review_status / source_type，与目标子目录对齐
    content = re.sub(r"review_status:\s*\"?pending\"?", 'review_status: "approved"', content)
    expected_st = SUBDIR_SOURCE_TYPE[to_subdir]
    if "source_type:" in content:
        content = re.sub(r"source_type:\s*\"?[^\"\n]+\"?", f'source_type: "{expected_st}"', content)
    dst_dir = os.path.join(KB_DIR, to_subdir)
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, os.path.basename(src))
    with open(dst, "w", encoding="utf-8") as f:
        f.write(content)
    os.remove(src)

    out = {
        "status": "ok",
        "promoted_to": os.path.relpath(dst, BASE_DIR),
        "source_type": expected_st,
        "title": meta.get("title", ""),
    }
    if ingest:
        import subprocess
        rel = os.path.relpath(dst, BASE_DIR)
        proc = subprocess.run(
            [os.path.join(BASE_DIR, ".venv/bin/python"), "rag_ingest.py", "--add", rel],
            cwd=BASE_DIR, capture_output=True, text=True, timeout=300,
        )
        tail = (proc.stdout or "").strip().splitlines()[-1:] or [""]
        out["ingest"] = "ok" if proc.returncode == 0 else "failed"
        out["ingest_detail"] = tail[0]
        out["next"] = "已增量入库，可直接检索（未重建、未影响原有内容）"
    else:
        out["next"] = "增量入库：python rag_ingest.py --add " + os.path.relpath(dst, BASE_DIR)
    return out


def cmd_score(pending_file: str) -> dict:
    """对已存在的 _pending 文件重新打分（只读，不改文件）。"""
    src = pending_file if os.path.isabs(pending_file) else os.path.join(BASE_DIR, pending_file)
    if not os.path.exists(src):
        return {"status": "error", "error": f"文件不存在：{pending_file}"}
    with open(src, encoding="utf-8") as f:
        content = f.read()
    # 去掉 frontmatter 再评分
    body = content.split("---", 2)[-1] if content.lstrip().startswith("---") else content
    score = score_content(body)
    return {"status": "ok", "file": pending_file, **score}


def cmd_review(pending_file: str) -> dict:
    """审核界面：把一篇待审文件的【来源 / 本地路径 / 评分 / 采集统计 / 内容预览】一次性给出，
    方便人工判断 ①来源质量（开 source_url）②采集质量（开 saved_abs，看有没有缺/截断）。只读不改。
    """
    src = pending_file if os.path.isabs(pending_file) else os.path.join(BASE_DIR, pending_file)
    if not os.path.exists(src):
        return {"status": "error", "error": f"文件不存在：{pending_file}"}
    with open(src, encoding="utf-8") as f:
        content = f.read()
    meta = parse_frontmatter(content)
    body = content.split("---", 2)[-1] if content.lstrip().startswith("---") else content
    return {
        "status": "ok",
        "title": meta.get("title", ""),
        "source_url": meta.get("source_url", ""),       # ① 来源：点开判断文章质量
        "saved_abs": os.path.abspath(src),              # ② 本地：打开判断采集质量
        "quality": meta.get("quality", ""),
        "score_relevance": meta.get("score_relevance", ""),
        "score_density": meta.get("score_density", ""),
        "score_reason": meta.get("score_reason", ""),
        "suggested_subdir": SOURCE_TYPE_TO_SUBDIR.get(meta.get("source_type", ""), "learning_resources"),
        "stats": content_stats(body),
        "preview": content_preview(body),
    }


# 工具/索引类文件名，不算审核候选
_NON_CANDIDATE = {"readme.md", "preview.md", "tree.md", "index.md"}


def cmd_list_pending() -> dict:
    """列出待审的"内容候选"（有 source_url 的真实采集文件），方便逐个 review。

    跳过 doc2kb 等工具产生的 README/PREVIEW/TREE/审计等非内容文件。
    """
    items = []
    for root, _dirs, files in os.walk(os.path.join(KB_DIR, "_pending")):
        for fn in sorted(files):
            if not fn.endswith(".md") or fn.startswith("_"):
                continue
            if fn.lower() in _NON_CANDIDATE or "formula_audit" in fn.lower():
                continue
            p = os.path.join(root, fn)
            with open(p, encoding="utf-8") as f:
                meta = parse_frontmatter(f.read())
            if not meta.get("source_url"):  # 无来源的不是采集候选
                continue
            items.append({
                "title": meta.get("title", fn),
                "source_url": meta.get("source_url", ""),
                "quality": meta.get("quality", ""),
                "saved_abs": os.path.abspath(p),
            })
    return {"status": "ok", "count": len(items), "items": items}


def _out(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="OfferClaw 半自动知识采集")
    sub = parser.add_subparsers(dest="cmd")
    p_crawl = sub.add_parser("crawl"); p_crawl.add_argument("url")
    p_ft = sub.add_parser("from-text")  # 浏览器插件采集的正文接入
    p_ft.add_argument("url"); p_ft.add_argument("--file", required=True)
    p_score = sub.add_parser("score"); p_score.add_argument("file")
    p_review = sub.add_parser("review"); p_review.add_argument("file")
    sub.add_parser("list")
    p_prom = sub.add_parser("promote"); p_prom.add_argument("file")
    p_prom.add_argument("--to", required=True, choices=sorted(VALID_SUBDIRS))
    p_prom.add_argument("--ingest", action="store_true", help="提升后立即增量入库（不重建）")
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    if args.cmd == "crawl":
        _out(cmd_crawl(args.url))
    elif args.cmd == "from-text":
        _out(cmd_from_text(args.url, args.file))
    elif args.cmd == "score":
        _out(cmd_score(args.file))
    elif args.cmd == "review":
        _out(cmd_review(args.file))
    elif args.cmd == "list":
        _out(cmd_list_pending())
    elif args.cmd == "promote":
        _out(cmd_promote(args.file, args.to, ingest=args.ingest))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
