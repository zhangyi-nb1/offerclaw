# -*- coding: utf-8 -*-
"""profile_evolution.py — 画像演进：周度"画像更新建议" + 成长日志归档。

用户原则：
- OfferClaw 越用越懂用户的核心载体是画像，但**画像不自动改写**——每周复盘
  产出"更新建议"（字段/当前值/建议值/证据），由用户人工审核后自行写回；
- 每次建议**完整归档**到 growth_journal.md（成长日志）：不做向量化、不进任何
  上下文，纯粹供用户日后回看自己的成长轨迹、确认掌握了哪些能力。
"""

from __future__ import annotations

import datetime
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILE_PATH = os.path.join(BASE_DIR, "user_profile.md")
DAILY_LOG_PATH = os.path.join(BASE_DIR, "daily_log.md")
JOURNAL_PATH = os.path.join(BASE_DIR, "growth_journal.md")

_JOURNAL_HEADER = """# 成长日志（Growth Journal）

> 每周复盘自动归档"画像更新建议"：记录你能力的演进轨迹与证据。
> **本文件不向量化、不进任何模型上下文**——只给你自己回看用。
> 采纳建议后请自行修改 user_profile.md（再跑 `refresh-state` 让问答同步）。

---
"""


METRICS_STATE_PATH = os.path.join(BASE_DIR, "logs", "growth_metrics.json")


def _week_log_stats(log_md: str, start: datetime.date, end: datetime.date) -> dict:
    """统计 [start, end] 区间的留痕：天数 / 完成数 / 未完成数 / 平均偏离度（来自记忆层）。"""
    import re
    days = done = todo = 0
    d = start
    try:
        from summary_tool import extract_date_block, _parse_log_block
        while d <= end:
            block = extract_date_block(log_md, d.isoformat())
            if block:
                days += 1
                parsed = _parse_log_block(block, d.isoformat())
                done += len(parsed.get("completed") or [])
                todo += len(parsed.get("incomplete") or [])
            d += datetime.timedelta(days=1)
    except Exception:
        pass
    # 偏离度：episodic 里该区间的 reflection 平均分
    dev = None
    try:
        from memory_layers import EpisodicMemory
        scores = [int(e.get("deviation_score", 0) or 0)
                  for e in EpisodicMemory().all()
                  if e.get("kind") == "reflection"
                  and start.isoformat() <= str(e.get("date", "")) <= end.isoformat()]
        if scores:
            dev = round(sum(scores) / len(scores), 1)
    except Exception:
        pass
    total = done + todo
    rate = round(done * 100 / total, 1) if total else None
    return {"days_logged": days, "done": done, "todo": todo,
            "completion_rate": rate, "avg_deviation": dev}


def _count_replans(start: datetime.date, end: datetime.date) -> dict:
    """按文件名时间戳统计区间内的重排/编辑次数（plan_YYYYMMDD_*.md）。"""
    import glob
    import re
    from plan_gen import _plans_dir
    regen = edits = 0
    for p in glob.glob(os.path.join(_plans_dir(), "plan_*.md")):
        m = re.match(r"plan_(\d{8})_\d{6}(_user)?\.md$", os.path.basename(p))
        if not m:
            continue
        try:
            d = datetime.datetime.strptime(m.group(1), "%Y%m%d").date()
        except ValueError:
            continue
        if start <= d <= end:
            if m.group(2):
                edits += 1
            else:
                regen += 1
    return {"replans": regen, "manual_edits": edits}


def _load_metric_snapshots() -> list:
    import json
    try:
        with open(METRICS_STATE_PATH, encoding="utf-8") as f:
            return json.load(f).get("history", [])
    except Exception:
        return []


def _append_metric_snapshot(snap: dict) -> None:
    import json
    os.makedirs(os.path.dirname(METRICS_STATE_PATH), exist_ok=True)
    hist = _load_metric_snapshots()
    hist.append(snap)
    with open(METRICS_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump({"history": hist[-104:]}, f, ensure_ascii=False, indent=2)


def _trend(cur, prev, higher_is_better: bool = True) -> str:
    """趋势箭头：与上周比。无数据返回空。"""
    if cur is None or prev is None:
        return ""
    diff = cur - prev
    if abs(diff) < 1e-9:
        return "→"
    good = (diff > 0) == higher_is_better
    return ("↑" if diff > 0 else "↓") + ("✅" if good else "⚠️")


def compute_growth_metrics(today_iso: str = "") -> dict:
    """周度养成指标（确定性，不调 LLM）：本周 vs 上周 + 资产增量。

    让"agent 是否越来越契合"可测量：留痕率、完成率、偏离度是过程指标；
    重排/编辑次数是计划稳定性指标；知识库/缺口库增量是资产指标。
    """
    today = (datetime.date.fromisoformat(today_iso)
             if today_iso else datetime.date.today())
    this_start, this_end = today - datetime.timedelta(days=6), today
    prev_start, prev_end = today - datetime.timedelta(days=13), today - datetime.timedelta(days=7)

    log_md = ""
    try:
        with open(DAILY_LOG_PATH, encoding="utf-8") as f:
            log_md = f.read()
    except OSError:
        pass
    cur = _week_log_stats(log_md, this_start, this_end)
    prev = _week_log_stats(log_md, prev_start, prev_end)
    cur.update(_count_replans(this_start, this_end))

    # 资产现状 + 与上次快照的增量
    kb_chunks = None
    try:
        import chromadb
        from rag_tools import get_collection_name
        col = chromadb.PersistentClient(
            path=os.path.join(BASE_DIR, "chroma_db")).get_collection(get_collection_name())
        kb_chunks = col.count()
    except Exception:
        pass
    gap_targets = merged_gaps = None
    try:
        from gap_store import summary as gap_summary
        gs = gap_summary()
        gap_targets, merged_gaps = gs.get("total_targets"), gs.get("merged_gap_count")
    except Exception:
        pass
    adjustments = 0
    try:
        from memory_layers import SemanticMemory, get_active_adjustments
        adjustments = len(get_active_adjustments(SemanticMemory()))
    except Exception:
        pass

    snaps = _load_metric_snapshots()
    last = snaps[-1] if snaps else {}
    deltas = {}
    for key, val in (("kb_chunks", kb_chunks), ("gap_targets", gap_targets),
                     ("merged_gaps", merged_gaps)):
        if val is not None and last.get(key) is not None:
            deltas[key] = val - last[key]
    _append_metric_snapshot({
        "date": today.isoformat(), "kb_chunks": kb_chunks,
        "gap_targets": gap_targets, "merged_gaps": merged_gaps,
        "completion_rate": cur["completion_rate"], "days_logged": cur["days_logged"],
    })
    return {
        "week": f"{this_start.isoformat()} ~ {this_end.isoformat()}",
        "current": cur, "previous": prev,
        "kb_chunks": kb_chunks, "gap_targets": gap_targets,
        "merged_gaps": merged_gaps, "active_adjustments": adjustments,
        "deltas": deltas,
    }


def format_metrics_md(m: dict) -> str:
    """把指标格式化为成长日志里的小节（带与上周对比的趋势箭头）。"""
    cur, prev = m["current"], m["previous"]

    def _fmt(v, suffix=""):
        return f"{v}{suffix}" if v is not None else "—"

    lines = [f"### 📈 本周养成指标（{m['week']}）", ""]
    lines.append(
        f"- 留痕：{cur['days_logged']}/7 天 "
        f"{_trend(cur['days_logged'], prev['days_logged'])}（上周 {prev['days_logged']}/7）")
    lines.append(
        f"- 计划完成率：{_fmt(cur['completion_rate'], '%')} "
        f"{_trend(cur['completion_rate'], prev['completion_rate'])}"
        f"（完成 {cur['done']} / 未完成 {cur['todo']}；上周 {_fmt(prev['completion_rate'], '%')}）")
    lines.append(
        f"- 平均偏离度：{_fmt(cur['avg_deviation'])} "
        f"{_trend(cur['avg_deviation'], prev['avg_deviation'], higher_is_better=False)}"
        f"（上周 {_fmt(prev['avg_deviation'])}；越低越好）")
    lines.append(
        f"- 计划稳定性：重排 {cur['replans']} 次 · 手动编辑 {cur['manual_edits']} 次"
        "（频繁重排可能说明排期不贴合实际）")
    d = m.get("deltas", {})

    def _delta(key):
        return f"（较上次 {'+' if d[key] >= 0 else ''}{d[key]}）" if key in d else ""

    lines.append(
        f"- 资产：知识库 {_fmt(m['kb_chunks'])} 块{_delta('kb_chunks')} · "
        f"目标 JD {_fmt(m['gap_targets'])} 个{_delta('gap_targets')} · "
        f"缺口 {_fmt(m['merged_gaps'])} 条{_delta('merged_gaps')} · "
        f"生效调整规则 {m['active_adjustments']} 条")
    if cur["days_logged"] == 0:
        lines.append("- ⚠️ 本周零留痕：所有养成机制都在空转——指标的前提是留痕。")
    return "\n".join(lines)


def build_profile_update_messages() -> list:
    """组装"画像更新建议"的 LLM messages：画像 vs 近 14 天留痕+复盘事实。"""
    profile = ""
    if os.path.exists(PROFILE_PATH):
        with open(PROFILE_PATH, encoding="utf-8") as f:
            profile = f.read()
    log_recent = ""
    try:
        from summary_tool import extract_recent_blocks
        with open(DAILY_LOG_PATH, encoding="utf-8") as f:
            log_recent = extract_recent_blocks(f.read(), days=14)
    except Exception:
        pass
    adjustments = ""
    try:
        from memory_layers import SemanticMemory, get_active_adjustments
        adj = get_active_adjustments(SemanticMemory())
        adjustments = "\n".join(f"- {a}" for a in adj)
    except Exception:
        pass

    system = (
        "你是 OfferClaw 的画像审计员。任务：对比「用户画像的自评」与「近 14 天的实际留痕/复盘」，"
        "找出画像已经落后于事实的字段，输出**画像更新建议**。\n\n"
        "输出格式（markdown，逐条）：\n"
        "### 建议 N：<字段名>\n"
        "- 当前画像：<画像里的原值>\n"
        "- 建议更新：<新值>\n"
        "- 证据：<引用留痕的具体日期与内容，必须可追溯>\n"
        "- 置信度：高/中/低\n\n"
        "纪律：\n"
        "1) 只依据留痕/复盘里的**事实**提建议，绝不臆测；证据不足就不提；\n"
        "2) 技能自评升级要保守（完成了系统学习+实践才 +1，不要看了一篇文章就升级）；\n"
        "3) 一条建议一个字段；没有任何值得更新的就只输出一行：「本周画像无需更新（证据不足或无变化）」；\n"
        "4) 最后附一段 ≤3 行的「本周能力小结」：用户这周实际掌握/推进了什么（给用户自己看的成长记录）。"
    )
    user = (
        f"========== 用户画像（当前版本）==========\n{profile[:6000]}\n\n"
        f"========== 近 14 天留痕 ==========\n{log_recent[:6000] or '（近 14 天无留痕）'}\n\n"
        f"========== 复盘沉淀的调整规则 ==========\n{adjustments or '（无）'}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def append_growth_journal(suggestions_md: str, date_str: str = "") -> str:
    """把本周建议归档进成长日志（append-only），返回文件路径。"""
    date_str = date_str or datetime.date.today().isoformat()
    week = datetime.date.fromisoformat(date_str).isocalendar()
    entry = (
        f"\n## {date_str}（{week.year}-W{week.week:02d}）\n\n"
        f"{suggestions_md.strip()}\n\n"
        "**采纳情况**：（待你标注：已采纳/部分采纳/未采纳 + 原因）\n\n---\n"
    )
    is_new = not os.path.exists(JOURNAL_PATH)
    with open(JOURNAL_PATH, "a", encoding="utf-8") as f:
        if is_new:
            f.write(_JOURNAL_HEADER)
        f.write(entry)
    return JOURNAL_PATH


def suggest_profile_updates() -> dict:
    """生成本周 养成指标 + 画像更新建议，归档成长日志。返回微信/CLI 友好结构。

    指标是确定性计算（即便 LLM 不可用也照常产出）；建议部分才依赖 LLM。
    """
    metrics = compute_growth_metrics()
    metrics_md = format_metrics_md(metrics)

    api_key = os.environ.get("OPENAI_API_KEY")
    suggestions = ""
    if api_key:
        from plan_gen import call_llm_plain
        try:
            suggestions = (call_llm_plain(build_profile_update_messages(),
                                          api_key, max_tokens=1800) or "").strip()
        except Exception as e:
            suggestions = f"（画像建议生成失败：{e}）"
    else:
        suggestions = "（未配置 LLM key，本周仅记录养成指标）"

    entry = metrics_md + "\n\n---\n\n" + suggestions
    path = append_growth_journal(entry)
    no_update = "无需更新" in suggestions[:80]

    cur = metrics["current"]
    metric_line = (
        f"📈 本周养成：留痕 {cur['days_logged']}/7 天 · "
        f"完成率 {cur['completion_rate'] if cur['completion_rate'] is not None else '—'}"
        f"{'%' if cur['completion_rate'] is not None else ''} · "
        f"重排 {cur['replans']} 次")
    return {
        "status": "ok",
        "metrics": metrics,
        "suggestions": suggestions,
        "has_updates": bool(suggestions) and not no_update and "失败" not in suggestions[:20],
        "journal_path": os.path.relpath(path, BASE_DIR),
        "wechat_summary": metric_line + "\n" + (
            ("🌱 本周画像更新建议：\n" + suggestions[:800] +
             "\n\n采纳的话请修改 user_profile.md（或回复我代你改），改完跑 refresh-state 同步问答记忆。")
            if (not no_update and "（" != suggestions[:1]) else "🌱 本周画像无需更新（证据不足或无变化）。"
        ) + f"\n📒 已归档成长日志：{os.path.relpath(path, BASE_DIR)}",
    }
