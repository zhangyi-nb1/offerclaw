# -*- coding: utf-8 -*-
"""
OfferClaw · 路线规划最小代码版（plan_gen.py）

职责：
    给定一份 JD 匹配产生的"缺口清单"，按 plan_prompt.md 的契约调用
    LLM 生成一份 4 周可执行计划。

设计取舍（V1 阶段）：
    - 不在本地复现 plan_prompt.md 的全部 9 步逻辑；把 prompt 整篇喂给 LLM，让 LLM 走流程
    - 本脚本只负责：组装上下文（profile + plan_prompt + 缺口清单）→ 调 LLM → 落盘
    - 不做缺口的本地解析校验（那是 plan_prompt.md 第 2 步的职责，由 LLM 在内部做）

输入：
    1. user_profile.md（自动读取）
    2. plan_prompt.md（自动读取）
    3. 缺口清单：命令行参数 --gaps <file> 或 stdin 粘贴

输出：
    plans/plan_<YYYYMMDD_HHMMSS>.md

使用：
    python plan_gen.py --gaps gaps.md
    或
    python plan_gen.py            # 然后从 stdin 粘贴，输入 EOF（Ctrl+Z 回车 / Ctrl+D）结束
"""

import argparse
import datetime
import os
import sys

import requests

from day1_api_starter import (
    API_KEY_ENV,
    build_zhipu_jwt,
    get_llm_config,
    load_local_env,
)


PROFILE_PATH = "user_profile.md"
PLAN_PROMPT_PATH = "plan_prompt.md"
DAILY_LOG_PATH = "daily_log.md"
SOURCE_POLICY_PATH = "source_policy.md"
TARGET_RULES_PATH = "target_rules.md"
OUTPUT_DIR = "plans"
PROJECT_CONTEXT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "knowledge_base", "project_context")


def read_text(path: str) -> str:
    if not os.path.exists(path):
        raise FileNotFoundError(f"必需文件缺失：{path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_project_context() -> str:
    """读取 knowledge_base/project_context/ 下的"已有项目现状"先验，拼成上下文块。

    这些是用户自有的在建项目（如 LocalFlow），OfferClaw **只读**：规划时据此建议
    "在现有项目上推进/扩展"，不让用户从零重造，也绝不代为开发。无则返回空串。
    """
    if not os.path.isdir(PROJECT_CONTEXT_DIR):
        return ""
    blocks = []
    for fn in sorted(os.listdir(PROJECT_CONTEXT_DIR)):
        if fn.endswith(".md") and not fn.startswith("_"):
            with open(os.path.join(PROJECT_CONTEXT_DIR, fn), encoding="utf-8") as f:
                blocks.append(f.read())
    return "\n\n".join(blocks)


def read_gaps(args) -> str:
    if args.gaps:
        return read_text(args.gaps)
    print("请粘贴缺口清单，输入完成后按 Ctrl+Z 回车（Windows）或 Ctrl+D（Unix）结束：")
    data = sys.stdin.read().strip()
    if not data:
        raise ValueError("缺口清单为空，已退出")
    return data


# =====================================================
# P1：RAG 检索学习资源（让计划基于真实知识库，而非 LLM 即兴编）
# =====================================================

# 只检索"岗位知识 / 学习资源"类内容，避免把画像/日志等内部文件混进推荐
RESOURCE_SOURCE_TYPES = ["career_knowledge", "resource"]

_KB_TITLE_CACHE: dict | None = None


def _kb_title_map() -> dict:
    """构建 {文件名: frontmatter title} 映射，用于给资源显示真实主题标题。

    chunk metadata 里的 title 往往是 ``## 正文采集`` 这类切块小标题，对 LLM
    没有指示性；文件级 frontmatter 的 title（如「7. 大模型 Harness Engineering」）
    才能让 LLM 把资源对应到缺口。一次性扫描 knowledge_base，缓存结果。
    """
    global _KB_TITLE_CACHE
    if _KB_TITLE_CACHE is not None:
        return _KB_TITLE_CACHE
    import re
    mapping = {}
    kb_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge_base")
    for root, _dirs, files in os.walk(kb_dir):
        if "_pending" in root:
            continue
        for fn in files:
            if not fn.endswith(".md") or fn.startswith("_"):
                continue
            try:
                with open(os.path.join(root, fn), encoding="utf-8") as f:
                    head = f.read(600)
                m = re.search(r'^title:\s*"?([^"\n]+)"?\s*$', head, re.MULTILINE)
                if m:
                    mapping[fn] = m.group(1).strip()
            except Exception:
                continue
    _KB_TITLE_CACHE = mapping
    return mapping


def _split_gap_queries(gaps: str, direction: str = "") -> list[str]:
    """把缺口清单拆成若干条独立检索 query。

    每条缺口（以 -/* 或数字开头的行，或冒号后的短句）单独成一条 query，
    并各自拼上方向语境。这样能为「RAG 缺口」「Agent 缺口」分别检索到
    各自最相关的章节，而不是用一个大杂烩 query 把它们平均掉。
    """
    items = []
    for ln in gaps.splitlines():
        s = ln.strip().lstrip("-*0123456789.、 ").strip()
        # 去掉整行包裹的【】小标题括号（前端缺口卡用 【硬门槛缺口】 这种格式）
        s = s.strip("【】 ").strip()
        # 去掉"技能缺口："这类冒号前缀小标题
        if "：" in s and len(s.split("：", 1)[0]) <= 6:
            s = s.split("：", 1)[1].strip()
        if not s:
            continue
        # 跳过纯分类小标题（硬门槛缺口/技能缺口/经历缺口/建议…），它们是结构标签而非检索内容。
        # 限长 ≤8，避免误杀「…能力缺口」这类描述性长句。
        if (s.endswith("缺口") and len(s) <= 8) or s in ("建议", "总结", "说明", "备注"):
            continue
        if len(s) >= 6:
            items.append(s)
    if not items:
        items = [gaps.strip()]
    prefix = f"{direction} " if direction else ""
    return [f"{prefix}{it}" for it in items]


def retrieve_learning_resources(
    gaps: str,
    direction: str = "",
    per_query: int = 4,
    top_files: int = 6,
) -> list[dict]:
    """基于缺口清单做 RAG 检索，返回去重后的学习资源片段。

    返回 ``[{"source": 文件名, "title": 标题, "snippet": 正文片段}, ...]``。
    设计要点：
    - **逐条缺口分别检索**（multi-query），再合并去重，保证每个缺口都能
      命中针对性资源，而非一个大杂烩 query 把不同主题平均掉
    - 只检索 ``career_knowledge`` / ``resource`` 两类 source_type
    - 按 source 文件去重；跳过纯 frontmatter / 纯目录等低密度片段
    - 任何失败（无 KEY / 集合不存在 / 依赖缺失）都静默返回 []，
      让 plan_gen 在离线 / 无 RAG 时仍能正常出计划
    """
    try:
        import chromadb
        from rag_tools import get_collection_name, get_embeddings_batch, has_embedding_api_key

        if not has_embedding_api_key():
            return []

        client = chromadb.PersistentClient(
            path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_db")
        )
        col = client.get_collection(get_collection_name())
        if col.count() == 0:
            return []

        queries = _split_gap_queries(gaps, direction)
        embeddings = get_embeddings_batch(queries)

        seen_sources = set()
        out = []
        # 轮转：每条 query 先各取最佳 1 个不重复来源，再回头补第 2 个……
        # 这样保证「每个缺口都有资源」，而不是某个缺口霸占全部名额。
        ranked_per_query = []
        for emb in embeddings:
            res = col.query(
                query_embeddings=[emb],
                n_results=per_query * 3,
                where={"source_type": {"$in": RESOURCE_SOURCE_TYPES}},
                include=["documents", "metadatas"],
            )
            ranked_per_query.append(list(zip(res.get("documents", [[]])[0],
                                             res.get("metadatas", [[]])[0])))

        for round_i in range(per_query * 3):
            for hits in ranked_per_query:
                if round_i >= len(hits):
                    continue
                doc, meta = hits[round_i]
                src = meta.get("source", "?")
                if src in seen_sources:
                    continue
                snippet = _clean_snippet(doc)
                if len(snippet) < 40:
                    continue
                seen_sources.add(src)
                # 优先用文件级 frontmatter 标题（指示性强），退回 chunk 标题
                file_title = _kb_title_map().get(src, "")
                out.append({
                    "source": src,
                    "title": file_title or meta.get("title", "") or "",
                    "snippet": snippet[:300],
                })
                if len(out) >= top_files:
                    return out
        return out
    except Exception:
        return []


def _clean_snippet(doc: str) -> str:
    """清理片段用于展示：去掉 frontmatter、来源 blockquote、页面目录标题，留真正正文。"""
    import re
    text = doc
    # 去掉开头的 YAML frontmatter
    if text.lstrip().startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            text = parts[2]
    lines = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            continue
        # 跳过来源/路径/入库说明等 blockquote 与一级标题、目录标记
        if s.startswith(">") or s.startswith("# "):
            continue
        if s in ("## 页面结构目录", "## 正文采集", "## 正文内容", "## 图片素材"):
            continue
        lines.append(s)
    return " ".join(lines).strip()


def _extract_direction(profile: str) -> str:
    """从 user_profile.md 抽取目标方向（仅取编号的方向条目，不含薪资/岗位类型噪音）。

    抓「目标方向」标题后紧跟的数字编号行，遇到第一个非编号行即停止。
    抓不到就返回空串（不影响检索）。
    """
    import re
    lines = profile.splitlines()
    out = []
    capture = False
    for ln in lines:
        s = ln.strip()
        if "目标方向" in s:
            capture = True
            continue
        if capture:
            m = re.match(r"^\d+[\.、]\s*(.+)$", s)
            if m:
                out.append(m.group(1).strip())
            elif s and not s.startswith(("-", "*")):
                break
            elif out:  # 已抓到编号项后遇到 - 开头的下一字段，停止
                break
    return " ".join(out)


def format_resources_block(resources: list[dict]) -> str:
    """把检索到的资源格式化成喂给 LLM 的上下文块。"""
    if not resources:
        return ""
    lines = ["以下是从本地知识库检索到的、与缺口相关的真实学习资源（请在计划中优先引用，标注来源文件名）：\n"]
    for i, r in enumerate(resources, 1):
        title = f"《{r['title']}》" if r["title"] else ""
        lines.append(f"[资源{i}] {title}（来源：{r['source']}）\n  {r['snippet']}\n")
    return "\n".join(lines)


def build_messages(profile: str, plan_prompt: str, daily_log: str,
                   source_policy: str, target_rules: str, gaps: str,
                   resources_block: str = "", project_context: str = "") -> list:
    """组装要发给 LLM 的 messages。

    设计：把 5 份依赖文件作为 system 上下文，缺口清单作为 user 消息。
    LLM 内部按 plan_prompt 的 9 步流程执行。
    P1：若 ``resources_block`` 非空，追加 RAG 检索到的真实学习资源。
    项目先验：若 ``project_context`` 非空，追加用户已有项目现状，要求把实战任务
    优先落到"在已有项目上推进"，且 OfferClaw 只建议不动手（只读）。
    """
    system_content = (
        "你是 OfferClaw，部署在长期会话中的求职作战官。\n"
        "你接下来要严格按 plan_prompt.md 的指令执行一次路线规划。\n"
        "下面是你必须读取的依赖文件全文。\n\n"
        f"========== plan_prompt.md ==========\n{plan_prompt}\n\n"
        f"========== user_profile.md ==========\n{profile}\n\n"
        f"========== target_rules.md ==========\n{target_rules}\n\n"
        f"========== daily_log.md ==========\n{daily_log}\n\n"
        f"========== source_policy.md ==========\n{source_policy}\n"
    )

    if resources_block:
        system_content += (
            f"\n========== 知识库检索资源（RAG） ==========\n{resources_block}\n"
            "规划每周/每日任务时，凡涉及上面资源覆盖的主题，"
            "必须引用对应资源并标注「来源：<文件名>」；不要编造不存在的资源链接。\n"
        )

    if project_context:
        system_content += (
            f"\n========== 用户已有项目现状（只读先验）==========\n{project_context}\n"
            "规划实战任务时的硬性要求：\n"
            "1) 优先把实战落到上面已有项目上（基于其现状给出『下一步推进建议』），"
            "不要让用户从零重造已有项目已具备的东西；\n"
            "2) 你对这些项目【只读】——只给学习/推进建议，绝不代为编码、修改、提交，"
            "措辞用『建议你/可以尝试』，不要写成『我来实现』；\n"
            "3) 若用户明确表示想『从零搭一个新项目来学习』，则可另规划新建项目（二者都支持）。\n"
        )

    project_directive = ""
    if project_context:
        project_directive = (
            "\n\n【实战编排硬性要求】用户已有在建项目（见 system 的『用户已有项目现状』）。\n"
            "凡『缺项目经历 / 端到端项目 / Agent / 工具调用 / 工作流 / Harness』类实战缺口，"
            "**必须编排为『在已有项目上推进的下一步』**（明确写出在哪个项目、加什么、达到什么），"
            "不要让用户从零再造一个同类项目。每条这类任务用『建议你…』措辞，"
            "OfferClaw 只建议、不代为开发。纯基础类缺口（如 Python 语法）可正常安排学习任务。"
        )
    user_content = (
        "请按 plan_prompt.md 的 9 步流程，基于下面这份缺口清单生成 4 周计划。\n"
        "今天日期是 " + datetime.date.today().isoformat() + "。"
        + project_directive + "\n\n"
        "========== 缺口清单 ==========\n" + gaps
    )

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]


def call_llm_plain(messages, api_key, max_tokens: int = 4000) -> str:
    """调用 LLM，不带 tools（规划是单次纯文本生成）。"""
    cfg = _resolve_chat_config(api_key)
    url = f"{cfg['api_base']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {cfg['bearer']}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": max_tokens,
    }
    if cfg.get("reasoning_effort"):
        payload["reasoning_effort"] = cfg["reasoning_effort"]
    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"].get("content", "") or ""


def call_llm_stream(messages, api_key, max_tokens: int = 4000):
    """调用 LLM，stream=True，逐 token yield str。供 SSE 端点消费。"""
    import json as _json
    cfg = _resolve_chat_config(api_key)
    url = f"{cfg['api_base']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {cfg['bearer']}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": max_tokens,
        "stream": True,
    }
    if cfg.get("reasoning_effort"):
        payload["reasoning_effort"] = cfg["reasoning_effort"]
    with requests.post(url, headers=headers, json=payload, timeout=120, stream=True) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            if isinstance(line, bytes):
                line = line.decode("utf-8", "replace")
            if line.startswith("data: "):
                data = line[6:]
                if data.strip() == "[DONE]":
                    return
                try:
                    chunk = _json.loads(data)
                    delta = chunk["choices"][0]["delta"].get("content", "")
                    if delta:
                        yield delta
                except Exception:
                    pass


def _resolve_chat_config(api_key: str) -> dict:
    """Resolve chat endpoint/auth for both current proxy and legacy Zhipu callers."""
    cfg = get_llm_config()
    zhipu_key = os.environ.get("ZHIPU_API_KEY", "")
    if api_key and api_key == zhipu_key:
        return {
            "api_base": "https://open.bigmodel.cn/api/paas/v4",
            "model": "glm-4-flash",
            "bearer": build_zhipu_jwt(api_key),
            "reasoning_effort": "",
        }
    bearer = build_zhipu_jwt(api_key) if cfg["is_zhipu"] else api_key
    return {**cfg, "bearer": bearer}


def prepare_plan_messages(gaps: str) -> tuple[list, list[dict]]:
    """读依赖文件 + RAG 检索资源 + 组装 messages 的统一入口。

    CLI 与 FastAPI（/api/plan、/api/plan/stream）共用此函数，确保三条
    路径的 RAG 接入行为一致（避免只有 CLI 享受 P1）。

    返回 ``(messages, resources)``。``resources`` 供调用方追加确定性附录。
    """
    profile = read_text(PROFILE_PATH)
    plan_prompt = read_text(PLAN_PROMPT_PATH)
    daily_log = read_text(DAILY_LOG_PATH)
    source_policy = read_text(SOURCE_POLICY_PATH)
    target_rules = read_text(TARGET_RULES_PATH)

    direction = _extract_direction(profile)
    resources = retrieve_learning_resources(gaps, direction=direction)
    resources_block = format_resources_block(resources)
    project_context = load_project_context()

    messages = build_messages(
        profile, plan_prompt, daily_log, source_policy, target_rules,
        gaps, resources_block=resources_block, project_context=project_context,
    )
    return messages, resources


def append_resources_appendix(plan_text: str, resources: list[dict]) -> str:
    """在 LLM 生成的计划末尾追加一个确定性的「参考资源」附录。

    LLM 是否在正文里引用资源不稳定（同一输入可能引用 0~N 次），因此由代码
    确定性地把 RAG 检索到的真实资源附在计划末尾，保证每份计划都能落到
    可追溯的知识库来源（满足 P1：计划输出必含知识库资源引用）。
    """
    if not resources:
        return plan_text
    lines = [
        plan_text.rstrip(),
        "",
        "---",
        "",
        "## 📚 本计划参考的知识库资源（RAG 自动检索）",
        "",
        "> 由 OfferClaw 基于上面的缺口清单从本地知识库自动检索，按相关度排序；"
        "学习对应主题时优先参考。",
        "",
    ]
    for i, r in enumerate(resources, 1):
        title = r["title"] or r["source"]
        lines.append(f"{i}. **{title}**")
        lines.append(f"   - 来源：`{r['source']}`")
        lines.append(f"   - 摘要：{r['snippet'][:140]}")
        lines.append("")
    return "\n".join(lines)


def _plans_dir() -> str:
    """plans/ 目录的绝对路径（相对 plan_gen.py 所在目录，避免受 CWD 影响）。"""
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, OUTPUT_DIR)


def save_plan(content: str, edited_by_user: bool = False) -> str:
    """落盘一份计划到 plans/。edited_by_user=True 时文件名带 _user 后缀，便于回读时标识。"""
    out_dir = _plans_dir()
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = "_user" if edited_by_user else ""
    path = os.path.join(out_dir, f"plan_{ts}{suffix}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def load_latest_plan() -> dict | None:
    """读取 plans/ 下最新的 plan_*.md。返回 {content, path, filename, mtime, edited_by_user}，
    没有任何计划时返回 None。"""
    import glob
    out_dir = _plans_dir()
    files = glob.glob(os.path.join(out_dir, "plan_*.md"))
    if not files:
        return None
    latest = max(files, key=os.path.getmtime)
    with open(latest, encoding="utf-8") as f:
        content = f.read()
    fname = os.path.basename(latest)
    return {
        "content": content,
        "path": latest,
        "filename": fname,
        "mtime": int(os.path.getmtime(latest)),
        "edited_by_user": fname.endswith("_user.md"),
    }


def main():
    parser = argparse.ArgumentParser(description="OfferClaw 路线规划生成器")
    parser.add_argument("--gaps", "-g", help="缺口清单文件路径（默认从 stdin 读）")
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    load_local_env()
    api_key = os.environ.get(API_KEY_ENV)
    if not api_key:
        print(f"[ERROR] 未检测到环境变量 {API_KEY_ENV}")
        sys.exit(1)

    print("[1/4] 读取缺口清单...")
    gaps = read_gaps(args)

    print("[2/4] 读取依赖文件 + RAG 检索相关学习资源...")
    messages, resources = prepare_plan_messages(gaps)
    if resources:
        print(f"      ✓ 命中 {len(resources)} 份知识库资源：")
        for r in resources:
            print(f"        - {r['title'] or r['source']}（{r['source']}）")
    else:
        print("      （未命中知识库资源，将生成不带引用的计划）")

    print("[3/4] 调用 LLM 生成计划（最长 120 秒）...")
    plan_text = call_llm_plain(messages, api_key)
    # 确定性追加参考资源附录，保证计划必含可追溯的知识库来源
    plan_text = append_resources_appendix(plan_text, resources)

    print("[4/4] 写入文件...")
    out_path = save_plan(plan_text)
    print(f"\n✓ 计划已生成：{out_path}")
    print("=" * 60)
    print(plan_text[:2000])
    if len(plan_text) > 2000:
        print(f"\n...（截断，完整内容见 {out_path}，共 {len(plan_text)} 字符）")


if __name__ == "__main__":
    main()
