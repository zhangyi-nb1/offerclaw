# -*- coding: utf-8 -*-
"""job_discovery 抓取的「登录/安全验证墙」识别测试。

背景：BOSS 直聘（zhipin）等站点对未登录/无头客户端会把 job_detail 302 跳到
安全验证页（/web/passport/zp/security.html）。此前 fetch_url 只报「页面内容为空」，
既误导用户、又可能把验证页 HTML 当 JD。这里锁定：命中墙→明确可执行的提示；
正常 JD→不误判。
"""
import pytest


def test_wall_reason_detects_security_redirect():
    """最终 URL 落到安全/登录页 → 判为墙。"""
    from job_discovery import _wall_reason
    assert _wall_reason(
        "https://www.zhipin.com/web/passport/zp/security.html?seed=x&callbackUrl=/job_detail/abc",
        "<html>...</html>")
    assert _wall_reason("https://x.com/login?redirect=/jd/1", "")


def test_wall_reason_detects_verification_text():
    """正文出现登录/人机验证文案 → 判为墙。"""
    from job_discovery import _wall_reason
    assert _wall_reason("https://job.example.com/jd/1", "请先登录后查看完整职位描述")
    assert _wall_reason("https://job.example.com/jd/2", "请完成安全验证后继续")


def test_wall_reason_passes_normal_jd():
    """正常 JD 页不得被误判为墙。"""
    from job_discovery import _wall_reason
    assert not _wall_reason(
        "https://job.example.com/jd/123",
        "岗位职责：负责大模型应用开发，要求熟悉 RAG / Agent / FastAPI。")


def test_fetch_url_wall_message_is_actionable(monkeypatch):
    """命中墙时 fetch_url 抛出的 ValueError 要点明原因并引导手动粘贴，
    且不会把验证页 HTML 当 JD 返回（应抛错而非返回内容）。"""
    import requests
    import job_discovery as jd

    class _FakeResp:
        url = "https://www.zhipin.com/web/passport/zp/security.html?callbackUrl=/job_detail/x"
        text = "<html><body>安全验证</body></html>"
        def raise_for_status(self):  # noqa: D401
            pass

    monkeypatch.setattr(requests, "get", lambda *a, **k: _FakeResp())
    with pytest.raises(ValueError) as ei:
        jd.fetch_url("https://www.zhipin.com/job_detail/x.html", timeout=5)
    msg = str(ei.value)
    assert "登录" in msg and "粘贴" in msg, msg
    assert "安全验证" in msg or "security.html" in msg, msg
