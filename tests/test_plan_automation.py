# -*- coding: utf-8 -*-
"""计划驱动自动化：最新计划 → 本周重点 → today/推送/再规划 都以它为参考。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import plan_gen  # noqa: E402

PLAN = """# OfferClaw 4 周计划

计划周期：2026-06-03 → 2026-06-30

Week 1 (06-03 → 06-09) 主题：夯实 Python 工程基础
  主线标签：[补技能]
  交付物：完成 Python 工程规范学习
Week 2 (06-10 → 06-16) 主题：RAG 全链路实战
  主线标签：[补项目]
  交付物：在 LocalFlow 集成 RAG recipe
Week 3 (06-17 → 06-23) 主题：Agent 工具调用
  主线标签：[补项目]
  交付物：新增一个 MCP tool
Week 4 (06-24 → 06-30) 主题：端到端收口
  主线标签：[投递准备]
  交付物：可投递简历素材
"""


def _fake_latest(edited=False):
    return {"content": PLAN, "filename": "plan_x.md", "mtime": 0, "edited_by_user": edited}


def test_summarize_picks_week_by_date(monkeypatch):
    monkeypatch.setattr(plan_gen, "load_latest_plan", lambda: _fake_latest())
    assert plan_gen.summarize_plan_for_automation("2026-06-05")["current_week"]["n"] == 1
    assert plan_gen.summarize_plan_for_automation("2026-06-12")["current_week"]["n"] == 2
    s4 = plan_gen.summarize_plan_for_automation("2026-06-25")
    assert s4["current_week"]["n"] == 4 and "收口" in s4["current_week"]["theme"]
    assert s4["current_week"]["deliverable"]


def test_summarize_flags_expired(monkeypatch):
    monkeypatch.setattr(plan_gen, "load_latest_plan", lambda: _fake_latest())
    s = plan_gen.summarize_plan_for_automation("2026-07-15")
    assert s["expired"] is True
    assert s["current_week"]["n"] == 4   # 到期后停在最后一周


def test_summarize_graceful_when_degenerate(monkeypatch):
    monkeypatch.setattr(plan_gen, "load_latest_plan",
                        lambda: {"content": "没有任何周结构的文本", "filename": "x.md",
                                 "mtime": 0, "edited_by_user": False})
    s = plan_gen.summarize_plan_for_automation("2026-06-12")
    assert s["has_plan"] is True and s["week_count"] == 0 and s["current_week"] is None


def test_summarize_no_plan(monkeypatch):
    monkeypatch.setattr(plan_gen, "load_latest_plan", lambda: None)
    assert plan_gen.summarize_plan_for_automation("2026-06-12") == {"has_plan": False}


def test_today_advice_leads_with_current_week(monkeypatch):
    import datetime
    import career_agent
    monkeypatch.setattr(plan_gen, "load_latest_plan", lambda: _fake_latest(edited=True))

    class _D(datetime.date):
        @classmethod
        def today(cls):
            return cls(2026, 6, 12)
    monkeypatch.setattr(career_agent.datetime, "date", _D)

    adv = career_agent.get_today_advice()
    assert adv["plan"]["has_plan"] and adv["plan"]["current_week"]["n"] == 2
    assert adv["plan"]["edited_by_user"] is True
    # 本周计划重点应置顶为主线动作
    assert adv["next_actions"], "next_actions 为空"
    assert "本周计划·第2周" in adv["next_actions"][0]
    assert "RAG 全链路" in adv["next_actions"][0]


def test_prepare_plan_messages_evolves_from_prev_plan(monkeypatch):
    monkeypatch.setattr(plan_gen, "load_latest_plan", lambda: _fake_latest())
    # 不实际检索资源，避免依赖向量库
    monkeypatch.setattr(plan_gen, "retrieve_learning_resources", lambda *a, **k: [])
    msgs, _ = plan_gen.prepare_plan_messages("技能缺口：\n- 缺少 RAG 实战")
    sys_msg = msgs[0]["content"]
    assert "用户当前计划（最新版" in sys_msg
    assert "基础上**演进**" in sys_msg
