# -*- coding: utf-8 -*-
"""投递管理（applications_store）+ 简历工坊（resume_project）回归。"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import applications_store as ap  # noqa: E402
import resume_project as rp  # noqa: E402

_TABLE = """# 投递追踪

| 日期 | 公司 | 岗位 | 来源 | 地点 | 匹配结论 | 样本定位 | 当前状态 | 下一步动作 | 备注 |
|---|---|---|---|---|---|---|---|---|---|
| 2026-04-22 | [DEMO] Acme | LLM 实习 | BOSS | 上海 | 暂不 | x | 不投递 | [示例] | — |
"""


@pytest.fixture()
def tmp_apps(tmp_path, monkeypatch):
    p = tmp_path / "applications.md"
    p.write_text(_TABLE, encoding="utf-8")
    monkeypatch.setattr(ap, "APPLICATIONS_PATH", str(p))
    return p


def test_upsert_adds_new_row(tmp_apps):
    r = ap.upsert_application("字节跳动", "大模型应用实习生", "已投递",
                              date="2026-06-04", next_action="等一周反馈")
    assert r["status"] == "ok" and r["action"] == "added"
    md = tmp_apps.read_text(encoding="utf-8")
    assert "| 字节跳动 | 大模型应用实习生 |" in md.replace("  ", " ")
    assert "已投递" in md and "等一周反馈" in md


def test_upsert_updates_existing_and_appends_timeline(tmp_apps):
    ap.upsert_application("字节跳动", "大模型应用实习生", "已投递", date="2026-06-04")
    r2 = ap.upsert_application("字节跳动", "大模型应用实习生", "面试中",
                               date="2026-06-10", next_action="准备一面八股")
    assert r2["action"] == "updated"
    md = tmp_apps.read_text(encoding="utf-8")
    assert md.count("字节跳动") == 1           # 不重复加行
    assert "面试中" in md and "06-10 面试中" in md  # 备注里有时间线


def test_upsert_rejects_bad_status(tmp_apps):
    r = ap.upsert_application("X", "Y", "瞎写的状态")
    assert r["status"] == "error"


def test_demo_rows_filtered(tmp_apps, monkeypatch):
    rows = ap.list_applications()
    assert not any("[DEMO]" in str(r) for r in rows)


def test_save_experience_writes_kb_format(tmp_path, monkeypatch):
    monkeypatch.setattr(ap, "EXPERIENCE_DIR", str(tmp_path / "exp"))
    r = ap.save_experience("字节跳动", "大模型应用实习生", "一面",
                           "一面考了 RAG 的 rerank 与多路召回，追问了去重策略；建议先把混合检索吃透。")
    assert r["status"] == "ok"
    body = open(r["saved_abs"], encoding="utf-8").read()
    assert 'source_type: "experience"' in body and "亲历" in body and "rerank" in body


def test_save_experience_rejects_too_short(tmp_path, monkeypatch):
    monkeypatch.setattr(ap, "EXPERIENCE_DIR", str(tmp_path / "exp"))
    assert ap.save_experience("A", "B", "一面", "太短")["status"] == "error"


# ---------------- resume_project ----------------

def test_gather_material_prefers_text():
    out = rp.gather_material(repo_url="https://github.com/x/y", text="项目介绍正文")
    assert out["status"] == "ok" and out["material"] == "项目介绍正文"


def test_gather_material_requires_input():
    assert rp.gather_material()["status"] == "error"


def test_build_messages_uses_default_pattern_without_templates(monkeypatch):
    monkeypatch.setattr(rp, "load_templates", lambda: [])
    msgs = rp.build_project_messages("一个 RAG 项目的介绍", "OfferClaw")
    sysm = msgs[0]["content"]
    assert "内置默认模式" in sysm and "绝不编造数字" in sysm
    assert "OfferClaw" in msgs[1]["content"]


def test_build_messages_injects_user_templates(monkeypatch):
    monkeypatch.setattr(rp, "load_templates",
                        lambda: [{"name": "tpl1.md", "content": "**项目｜角色**\n- 范例要点"}])
    msgs = rp.build_project_messages("素材", "")
    sysm = msgs[0]["content"]
    assert "模板范例 1：tpl1.md" in sysm and "严格学习其格式" in sysm
    assert "内置默认模式" not in sysm
