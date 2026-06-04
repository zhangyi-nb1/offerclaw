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
    """生成本周画像更新建议 + 归档成长日志。返回微信/CLI 友好结构。"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {"status": "error", "error": "未配置 OPENAI_API_KEY"}
    from plan_gen import call_llm_plain
    messages = build_profile_update_messages()
    out = (call_llm_plain(messages, api_key, max_tokens=1800) or "").strip()
    if not out:
        return {"status": "error", "error": "LLM 未返回内容"}
    path = append_growth_journal(out)
    no_update = "无需更新" in out[:80]
    return {
        "status": "ok",
        "suggestions": out,
        "has_updates": not no_update,
        "journal_path": os.path.relpath(path, BASE_DIR),
        "wechat_summary": (
            ("🌱 本周画像更新建议：\n" + out[:800] +
             "\n\n采纳的话请修改 user_profile.md（或回复我代你改），改完跑 refresh-state 同步问答记忆。")
            if not no_update else "🌱 本周画像无需更新（证据不足或无变化）。"
        ) + f"\n📒 已归档成长日志：{os.path.relpath(path, BASE_DIR)}",
    }
