# -*- coding: utf-8 -*-
"""offerclaw_cli.py — OfferClaw command-line interface for OpenClaw integration.

Direct CLI entry point — no FastAPI server needed.
OpenClaw skill calls these subcommands via shell; each prints JSON to stdout.

Usage:
    python offerclaw_cli.py today
    python offerclaw_cli.py profile
    python offerclaw_cli.py match "JD 原文..."
    python offerclaw_cli.py query "我的求职方向是什么"
    python offerclaw_cli.py daily
    python offerclaw_cli.py log "今天学了 LangGraph 条件路由"
    python offerclaw_cli.py doctor
    python offerclaw_cli.py health
"""

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

_env_local = os.path.join(BASE_DIR, ".env.local")
if os.path.exists(_env_local):
    with open(_env_local, encoding="utf-8") as _f:
        for _ln in _f:
            _ln = _ln.strip()
            if _ln and not _ln.startswith("#") and "=" in _ln:
                _k, _v = _ln.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())


def _json_out(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def cmd_today():
    from career_agent import get_today_advice
    _json_out(get_today_advice())


def cmd_profile():
    from profile_loader import load_profile
    p = load_profile()
    _json_out(p)


def cmd_match(jd_text):
    from profile_loader import load_profile
    from match_job import run_match, format_report
    profile = load_profile()
    report = run_match(profile, jd_text)
    _json_out({
        "conclusion": report.conclusion,
        "reason": report.conclusion_reason,
        "direction": report.direction,
        "suggestions": report.suggestions,
        "gap_list": report.gap_list,
    })


def _default_gaps_from_profile():
    """无显式缺口时，按画像现状给一份默认缺口（大模型应用工程师方向）。"""
    return (
        "技能缺口：\n"
        "- Python 工程能力需系统提升\n"
        "- 缺少 RAG / 向量检索的系统知识与实战\n"
        "- 缺少 Agent / 工具调用 / 工作流编排的项目经历\n"
        "经历缺口：\n"
        "- 缺少端到端、可写进简历的大模型应用开发项目"
    )


def _extract_weekly_themes(plan_md):
    """从计划正文抽取每周主题行，做微信友好摘要。"""
    import re
    themes = []
    for ln in plan_md.splitlines():
        m = re.match(r"\s*(Week\s*\d+[^\n]*主题[:：][^\n]+)", ln)
        if m:
            themes.append(m.group(1).strip())
    return themes


def cmd_plan(gaps=None):
    """生成 4 周学习计划（接 RAG 资源 + 项目先验），返回微信友好摘要 + 完整计划路径。

    供"给我制定/更新学习计划"在微信触发：OpenClaw 据返回的 wechat_summary 推送给用户，
    full_plan 已落盘到 plans/。
    """
    from plan_gen import prepare_plan_messages, call_llm_plain, append_resources_appendix, save_plan
    # 缺口来源优先级：显式入参 > 缺口信息库（累积的目标 JD 缺口）> 画像默认
    gaps = (gaps or "").strip()
    if not gaps:
        try:
            from gap_store import merged_gaps_text
            gaps = merged_gaps_text()
        except Exception:
            gaps = ""
    gaps = gaps or _default_gaps_from_profile()
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        _json_out({"status": "error", "error": "未配置 OPENAI_API_KEY"})
        return
    messages, resources = prepare_plan_messages(gaps)
    plan = call_llm_plain(messages, api_key, max_tokens=7000)
    # 退化产物（拒绝/无周结构）不落盘：避免污染"当前计划"并被后续注入自我复制
    from plan_gen import is_degenerate_plan
    if is_degenerate_plan(plan):
        _json_out({
            "status": "error",
            "error": "生成结果不是有效计划（无周结构/被拒绝），未保存。请重试或检查缺口输入。",
            "full_plan": plan,
        })
        return
    from plan_gen import normalize_plan_dates
    import datetime as _dt
    plan = normalize_plan_dates(plan, _dt.date.today().isoformat())
    plan = append_resources_appendix(plan, resources)
    path = save_plan(plan)
    themes = _extract_weekly_themes(plan)
    # 微信友好摘要：每周主题 + 资源数 + 完整计划位置
    lines = ["📚 学习计划已生成："]
    lines += [f"  {t}" for t in themes] if themes else ["  （详见完整计划）"]
    lines.append(f"📎 参考资源 {len(resources)} 份，完整计划：{os.path.relpath(path, BASE_DIR)}")
    _json_out({
        "status": "ok",
        "saved_path": path,
        "weekly_themes": themes,
        "resource_count": len(resources),
        "wechat_summary": "\n".join(lines),
        "full_plan": plan,
    })


def cmd_query(question):
    """KB 命中才答：检索→相关性门槛→命中则基于 KB 合成答案+标注来源；未命中坦白说没有。

    门槛逻辑统一收口在 rag_gate.gated_query（与 Web /api/query 共用同一套）。
    """
    from rag_gate import gated_query
    _json_out(gated_query(question))


def cmd_daily():
    daily_path = os.path.join(BASE_DIR, "daily_log.md")
    if not os.path.exists(daily_path):
        _json_out({"error": "daily_log.md not found"})
        return
    with open(daily_path, "r", encoding="utf-8") as f:
        content = f.read()
    import re
    blocks = re.findall(r"(## \d{4}-\d{2}-\d{2}.*?)(?=\n## \d{4}-\d{2}-\d{2}|\Z)", content, re.DOTALL)
    recent = blocks[-3:] if blocks else []
    _json_out({
        "total_entries": len(blocks),
        "recent": [b.strip()[:500] for b in recent],
    })


def _parse_structured_log(content):
    """解析轻量结构化留痕文本，返回 (tag, done[], todo[], notes)。

    支持的前缀（中英文冒号皆可，分号/换行分隔多项）：
      主线: / tag:        → 主线标签
      完成: / done:       → 已完成项
      未完成: / todo:     → 未完成项
      笔记: / note:       → 自由笔记
    无任何前缀时，整段作为 notes（freeform）。
    """
    import re
    tag, done, todo, notes = "", [], [], ""
    matched = False
    for line in content.splitlines():
        s = line.strip()
        if not s:
            continue
        m = re.match(r"^(主线|tag)[：:]\s*(.+)$", s, re.I)
        if m:
            tag = m.group(2).strip(); matched = True; continue
        m = re.match(r"^(完成|已完成|done)[：:]\s*(.+)$", s, re.I)
        if m:
            done += [x.strip() for x in re.split(r"[;；、]", m.group(2)) if x.strip()]; matched = True; continue
        m = re.match(r"^(未完成|todo)[：:]\s*(.+)$", s, re.I)
        if m:
            todo += [x.strip() for x in re.split(r"[;；、]", m.group(2)) if x.strip()]; matched = True; continue
        m = re.match(r"^(笔记|note)[：:]\s*(.+)$", s, re.I)
        if m:
            notes += m.group(2).strip() + "\n"; matched = True; continue
        # 未匹配前缀的行：归入 notes
        notes += s + "\n"
    if not matched:
        notes = content.strip()
    return tag, done, todo, notes.strip()


def cmd_log(content):
    """追加一条结构化留痕到 daily_log.md，字段与模板/P2 复盘解析对齐。"""
    from summary_tool import append_structured_daily_log
    tag, done, todo, notes = _parse_structured_log(content)
    _json_out(append_structured_daily_log(tag=tag, done=done, todo=todo, notes=notes))


def cmd_review(date_str=None):
    """触发当日（或指定日期）结构化复盘：调 summary_tool → 记忆沉淀 → 返回调整建议。

    供微信里说"复盘今天"时调用。若无 LLM key 或复盘失败，返回错误信息但不崩。
    """
    import datetime
    import subprocess
    date_str = date_str or datetime.date.today().isoformat()
    # 用户当日未留痕 → 自动按"今日计划全部未完成"记一条（长期养成：状态不留白），再复盘
    auto_logged = False
    try:
        log_md = open(os.path.join(BASE_DIR, "daily_log.md"), encoding="utf-8").read() \
            if os.path.exists(os.path.join(BASE_DIR, "daily_log.md")) else ""
        if f"## {date_str}" not in log_md:
            from career_agent import get_today_advice
            from summary_tool import append_structured_daily_log
            planned = get_today_advice().get("today_plan", [])
            append_structured_daily_log(
                tag="", done=[], todo=planned,
                notes="（系统自动：用户当日未留痕，按今日计划记为未完成）",
                date_str=date_str,
            )
            auto_logged = True
    except Exception:
        pass
    try:
        proc = subprocess.run(
            [os.path.join(BASE_DIR, ".venv/bin/python"), "summary_tool.py", "--date", date_str],
            cwd=BASE_DIR, capture_output=True, text=True, timeout=180,
        )
        out = proc.stdout
        # 提取 memory/adjust 反馈行
        adjust = [ln.strip() for ln in out.splitlines() if ln.strip().startswith("- ") and "建议" in ln]
        saved = next((ln for ln in out.splitlines() if "复盘已保存" in ln), "")
        # 读回当前生效调整
        active = []
        try:
            from memory_layers import SemanticMemory, get_active_adjustments
            active = get_active_adjustments(SemanticMemory())
        except Exception:
            pass
        _json_out({
            "status": "ok" if proc.returncode == 0 else "error",
            "date": date_str,
            "saved": saved.replace("[OK] ", "").strip(),
            "active_adjustments": active,
            "auto_logged": auto_logged,  # True=用户当日未留痕，系统已按今日计划记为未完成
        })
    except Exception as e:
        _json_out({"status": "error", "error": str(e), "date": date_str})


def cmd_doctor():
    import subprocess
    result = subprocess.run(
        [os.path.join(BASE_DIR, ".venv/bin/python"), "doctor.py"],
        cwd=BASE_DIR, capture_output=True, text=True, timeout=30
    )
    lines = result.stdout.strip().split("\n")
    summary = lines[-1] if lines else "unknown"
    _json_out({"output": result.stdout.strip(), "summary": summary})


def cmd_health():
    import chromadb
    try:
        from rag_tools import get_collection_name
        client = chromadb.PersistentClient(path=os.path.join(BASE_DIR, "chroma_db"))
        collection_name = get_collection_name()
        col = client.get_collection(collection_name)
        _json_out({
            "status": "healthy",
            "chroma_db": "connected",
            "collection": collection_name,
            "chunks": col.count(),
        })
    except Exception as e:
        _json_out({"status": "unhealthy", "error": str(e)})


def main():
    if len(sys.argv) < 2:
        print("Usage: python offerclaw_cli.py {today|profile|match|query|plan|daily|log|review|doctor|health} [args]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "today":
        cmd_today()
    elif cmd == "plan":
        cmd_plan(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "profile":
        cmd_profile()
    elif cmd == "match":
        if len(sys.argv) < 3:
            print("Usage: python offerclaw_cli.py match '<JD text>'")
            sys.exit(1)
        cmd_match(sys.argv[2])
    elif cmd == "query":
        if len(sys.argv) < 3:
            print("Usage: python offerclaw_cli.py query '<question>'")
            sys.exit(1)
        cmd_query(sys.argv[2])
    elif cmd == "daily":
        cmd_daily()
    elif cmd == "log":
        if len(sys.argv) < 3:
            print("Usage: python offerclaw_cli.py log '<content>'")
            sys.exit(1)
        cmd_log(sys.argv[2])
    elif cmd == "review":
        cmd_review(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "doctor":
        cmd_doctor()
    elif cmd == "health":
        cmd_health()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
