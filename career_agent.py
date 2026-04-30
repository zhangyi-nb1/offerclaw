# -*- coding: utf-8 -*-
"""
OfferClaw · 顶层 Orchestrator (career_agent.py)

V2 阶段三职责：
    把"画像 / 投递池 / 日志 / 缺口"四类状态聚合成一句"今天最该做什么"，
    供 /api/today 直接消费、UI 顶部横条直接渲染。

设计取舍：
    - 纯规则、不调 LLM（秒级返回，前端打开页面不卡）
    - 优先级：紧急投递动作 > 面试准备 > 缺口闭环 > 日志补登 > 默认建议
    - LLM 由后续阶段（resume_builder / summary_tool）按需调

读取来源：
    - applications.md（投递池状态机）
    - daily_log.md（日志最新块）
    - user_profile.md（兜底建议带方向）
"""

import datetime
import os
import re
from typing import Dict, List, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APPLICATIONS_PATH = os.path.join(BASE_DIR, "applications.md")
DAILY_LOG_PATH = os.path.join(BASE_DIR, "daily_log.md")
PROFILE_PATH = os.path.join(BASE_DIR, "user_profile.md")


def _read(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def parse_applications(md: str) -> List[Dict[str, str]]:
    """从 applications.md 抓所有 markdown 表格行（投递记录）。

    只识别"日期 | 公司 | 岗位 | 来源 | ... | 当前状态 | 下一步动作 | ..."这种 9+ 列表行。
    自动跳过 ``[DEMO]`` 行（示例数据），避免 ``today_advice`` 把 demo 投递顶到 headline。
    """
    rows: List[Dict[str, str]] = []
    headers: Optional[List[str]] = None
    in_table = False
    for line in md.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            in_table = False
            headers = None
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        # 跳过分隔行 |---|---|
        if all(re.fullmatch(r":?-+:?", c or "-") for c in cells):
            in_table = True
            continue
        if headers is None:
            # 只有当包含"当前状态"或"状态"才认作真正的投递池表头
            if any("状态" in c for c in cells) and any("公司" in c or "岗位" in c for c in cells):
                headers = cells
            continue
        if not in_table or not headers or len(cells) != len(headers):
            continue
        # 跳过 [DEMO] 示例行
        if any("[DEMO]" in c for c in cells):
            continue
        rows.append(dict(zip(headers, cells)))
    return rows


# 状态机：每个状态对应一句"该做什么"
_STATE_ACTION = {
    "已评估": ("决定投/不投", 30),
    "准备投递": ("尽快定稿简历并投出", 90),
    "已投递": ("耐心等反馈（≥7 天无回复转跟进）", 40),
    "等待反馈": ("写一封跟进邮件或转入放弃", 80),
    "面试中": ("准备面试题 & 复盘故事库", 100),
    "已 Offer": ("评估接受 / 比较其他 Offer", 95),
    "已拒绝": ("做一次失败复盘并更新故事库", 50),
    "主动放弃": ("做一次决策复盘", 20),
    "不投递": ("无需动作", 5),
}


def pick_top_application(rows: List[Dict[str, str]]) -> Optional[Tuple[Dict[str, str], str, int]]:
    """挑出当前优先级最高的一条投递。返回 (row, action_text, priority)。"""
    best: Optional[Tuple[Dict[str, str], str, int]] = None
    for r in rows:
        state = ""
        for k in r:
            if "状态" in k:
                state = r[k]
                break
        action, prio = _STATE_ACTION.get(state, ("", 0))
        if not action:
            continue
        if best is None or prio > best[2]:
            best = (r, action, prio)
    return best


def latest_log_date(log: str) -> Optional[str]:
    """daily_log.md 最近一次 ## YYYY-MM-DD 标题日期。"""
    dates = re.findall(r"^##\s+(\d{4}-\d{2}-\d{2})", log, re.MULTILINE)
    return max(dates) if dates else None


def days_since(date_str: str) -> Optional[int]:
    try:
        d = datetime.date.fromisoformat(date_str)
    except Exception:
        return None
    return (datetime.date.today() - d).days


def get_today_advice() -> Dict[str, object]:
    """生成"今天最该做什么"。返回结构供 /api/today 直接 JSON 化。"""
    apps_md = _read(APPLICATIONS_PATH)
    log_md = _read(DAILY_LOG_PATH)
    rows = parse_applications(apps_md)
    today = datetime.date.today().isoformat()

    headline = ""
    reason = ""
    source = ""
    next_actions: List[str] = []

    # 1) 投递池状态优先
    top = pick_top_application(rows)
    if top is not None:
        row, action, _prio = top
        company = next((row[k] for k in row if "公司" in k), "未知公司")
        post = next((row[k] for k in row if "岗位" in k), "未知岗位")
        state = next((row[k] for k in row if "状态" in k), "")
        nxt = next((row[k] for k in row if "下一步" in k), "")
        headline = f"【{company} · {post}】{action}"
        reason = f"applications.md 中此岗位状态为「{state}」，状态机指示该动作优先级最高。"
        source = "applications.md"
        if nxt:
            next_actions.append(f"按 applications.md 已写下一步：{nxt}")

    # 2) 日志补登
    last_log = latest_log_date(log_md)
    gap_days = days_since(last_log) if last_log else 99
    if gap_days is not None and gap_days >= 1:
        next_actions.append(
            f"补登 daily_log.md：上次记录是 {last_log}（距今 {gap_days} 天）。"
            f"可在 ⑤ 卡片直接追加。"
        )

    # 3) 兜底建议
    if not headline:
        if rows:
            headline = "暂无紧急投递任务，建议复盘最近匹配过的岗位"
            reason = "applications.md 中没有处于活跃状态的投递。"
            source = "applications.md"
        else:
            headline = "建议先在 ② 卡片粘一段 JD 跑一次匹配，把缺口固化进 ③ 卡片"
            reason = "applications.md 暂无投递记录，建议先做匹配评估。"
            source = "默认策略"
        next_actions.append("在 ② 卡片粘 JD → ③ 看缺口 → ④ 生成 4 周计划。")

    return {
        "today": today,
        "headline": headline,
        "reason": reason,
        "source": source,
        "next_actions": next_actions,
        "stats": {
            "applications_total": len(rows),
            "last_log_date": last_log or "",
            "log_gap_days": gap_days if gap_days is not None else -1,
        },
    }


if __name__ == "__main__":
    import json
    print(json.dumps(get_today_advice(), ensure_ascii=False, indent=2))
