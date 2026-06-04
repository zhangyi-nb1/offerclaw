# -*- coding: utf-8 -*-
"""applications_store.py — 投递管理的写入层（Web 投递功能栏的后端）。

用户流程（用户定义）：
- 用户上传自己的真实投递情况：企业名、投递岗、投递进度+时间点、经验总结；
- 经验总结（笔试/面试真题、流程、教训）可选择**加入知识库**——亲历经验是
  第一手强指导信号，入库后直接影响 RAG 问答、学习计划与每日建议。

存储：
- 投递行：写入 applications.md 的「投递清单」表（沿用既有状态机与字段，
  career_agent.parse_applications / pick_top_application 直接消费）；
- 经验总结：写成 knowledge_base/experience_posts/亲历_*.md（frontmatter
  含 company/position/stage），由 API 层决定是否增量入向量库。
"""

from __future__ import annotations

import datetime
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APPLICATIONS_PATH = os.path.join(BASE_DIR, "applications.md")
EXPERIENCE_DIR = os.path.join(BASE_DIR, "knowledge_base", "experience_posts")

# 与 applications.md「状态枚举」表一致
STATUSES = ["已评估", "准备投递", "不投递", "已投递", "等待反馈",
            "面试中", "已 Offer", "已拒绝", "主动放弃"]

# 投递清单表的列（与现有表头一致）
_COLUMNS = ["日期", "公司", "岗位", "来源", "地点", "匹配结论",
            "样本定位", "当前状态", "下一步动作", "备注"]


def _today() -> str:
    return datetime.date.today().isoformat()


def _clean_cell(s: str) -> str:
    """单元格清洗：去掉竖线/换行，防止破坏 markdown 表格。"""
    return re.sub(r"[|\r\n]+", " ", str(s or "")).strip() or "—"


def list_applications(include_demo: bool = False) -> list[dict]:
    """读取投递清单（默认过滤 [DEMO] 示例行）。"""
    from career_agent import parse_applications
    if not os.path.exists(APPLICATIONS_PATH):
        return []
    with open(APPLICATIONS_PATH, encoding="utf-8") as f:
        md = f.read()
    rows = parse_applications(md)  # parse 已跳过 [DEMO]
    if include_demo:
        return rows
    return rows


def upsert_application(company: str, position: str, status: str, *,
                       date: str = "", source: str = "", location: str = "",
                       next_action: str = "", note: str = "") -> dict:
    """新增或更新一条投递记录（按 公司+岗位 定位）。

    更新时：覆盖 日期/当前状态/下一步动作；备注**追加**时间线
    （`MM-DD 状态` 形式），保留投递进度的时间点轨迹。
    """
    company, position = _clean_cell(company), _clean_cell(position)
    if company == "—" or position == "—":
        return {"status": "error", "error": "企业名与投递岗不能为空"}
    if status not in STATUSES:
        return {"status": "error", "error": f"进度必须是 {STATUSES} 之一"}
    date = (date or _today()).strip()

    with open(APPLICATIONS_PATH, encoding="utf-8") as f:
        lines = f.read().splitlines()

    # 定位「投递清单」表：找含 当前状态 的表头行
    header_idx = None
    for i, ln in enumerate(lines):
        if ln.strip().startswith("|") and "当前状态" in ln and "公司" in ln:
            header_idx = i
            break
    if header_idx is None:
        return {"status": "error", "error": "applications.md 中找不到投递清单表"}

    # 表体范围：表头+分隔行之后，直到第一个非 | 行
    body_start = header_idx + 2
    body_end = body_start
    while body_end < len(lines) and lines[body_end].strip().startswith("|"):
        body_end += 1

    timeline_mark = f"{date[5:]} {status}"  # MM-DD 状态
    updated = False
    for i in range(body_start, body_end):
        cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
        if len(cells) != len(_COLUMNS):
            continue
        if cells[1] == company and cells[2] == position:
            cells[0] = date
            cells[7] = status
            if next_action:
                cells[8] = _clean_cell(next_action)
            # 备注追加时间线 + 可选新备注
            extra = [x for x in [timeline_mark, _clean_cell(note) if note else ""] if x and x != "—"]
            old_note = cells[9] if cells[9] != "—" else ""
            cells[9] = _clean_cell(" · ".join([x for x in [old_note] + extra if x]))
            lines[i] = "| " + " | ".join(cells) + " |"
            updated = True
            break

    if not updated:
        row = ["" for _ in _COLUMNS]
        row[0] = date
        row[1], row[2] = company, position
        row[3] = _clean_cell(source)
        row[4] = _clean_cell(location)
        row[5] = row[6] = "—"
        row[7] = status
        row[8] = _clean_cell(next_action) or "—"
        row[9] = _clean_cell(note) if note else timeline_mark
        lines.insert(body_end, "| " + " | ".join(row) + " |")

    with open(APPLICATIONS_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return {"status": "ok", "action": "updated" if updated else "added",
            "company": company, "position": position, "state": status, "date": date}


def save_experience(company: str, position: str, stage: str, text: str) -> dict:
    """把一段亲历投递经验写成知识库格式的 md（experience_posts/）。

    返回 {status, saved, saved_abs}；是否增量入向量库由调用方（API 层）决定。
    """
    text = (text or "").strip()
    if len(text) < 20:
        return {"status": "error", "error": "经验总结太短（≥20 字），写点真东西"}
    os.makedirs(EXPERIENCE_DIR, exist_ok=True)
    today = _today()
    slug = re.sub(r"[^\w一-鿿]+", "_", f"{company}_{position}")[:40]
    fname = f"亲历_{slug}_{today}.md"
    path = os.path.join(EXPERIENCE_DIR, fname)
    stage = _clean_cell(stage)
    body = (
        "---\n"
        f'title: "亲历投递经验：{company} · {position}（{stage}）"\n'
        f'source_url: "(用户亲历投递)"\n'
        f'crawl_date: "{today}"\n'
        'quality: "A"\n'
        'source_type: "experience"\n'
        'review_status: "approved"\n'
        f'tags: ["亲历", "投递经验", "{stage}"]\n'
        "---\n\n"
        f"# 亲历投递经验：{company} · {position}\n\n"
        f"> 阶段：{stage} · 记录日期：{today}\n"
        f"> 本文为用户亲身经历的第一手经验，对学习计划与每日建议有强指导意义。\n\n"
        f"{text}\n"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    return {"status": "ok", "saved": os.path.relpath(path, BASE_DIR), "saved_abs": path}
