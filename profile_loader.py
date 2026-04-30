"""profile_loader.py — OfferClaw 状态真实化（产品级 Agent 化指导 §4）

把 ``user_profile.md`` 解析成 ``match_job.run_match`` 能直接吃的 dict，
让 ``/api/match`` 等核心链路不再依赖 ``match_job.DEMO_PROFILE``。

**设计原则**

1. 不引入第三方 Markdown 解析库，纯正则 + 行扫描。
2. 字段缺失时回退到 ``profiles/p1_zhangyi_ai.json`` 对应键，
   再缺失时给安全默认（空 list / 0 / "不限"），保证下游 ``run_match``
   永远能拿到完整的 13 个键，不抛 KeyError。
3. 输出 dict 的键名和类型完全对齐 ``match_job.DEMO_PROFILE``，
   方便老调用方一行替换。
4. 默认带轻量缓存（按文件 mtime 失效），避免每次 ``/api/match``
   都重新读盘 + 正则。
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILE_MD = os.path.join(BASE_DIR, "user_profile.md")
PROFILE_JSON_FALLBACK = os.path.join(BASE_DIR, "profiles", "p1_zhangyi_ai.json")

REQUIRED_KEYS = [
    "学历",
    "专业",
    "所在地",
    "可接受地域",
    "方向优先级",
    "明确不做",
    "工作性质偏好",
    "期望薪资",
    "熟练技能",
    "会用技能",
    "项目数量",
    "实习数量",
    "英语自评",
]

_SAFE_DEFAULT: dict[str, Any] = {
    "学历": "本科",
    "专业": "",
    "所在地": "",
    "可接受地域": [],
    "方向优先级": [],
    "明确不做": [],
    "工作性质偏好": "不限",
    "期望薪资": "面议",
    "熟练技能": [],
    "会用技能": [],
    "项目数量": 0,
    "实习数量": 0,
    "英语自评": 1,
}

# ------- 简易缓存 -------
_CACHE: dict[str, Any] = {"mtime": None, "path": None, "data": None}


# =====================================================
# 字段提取（每个函数独立、可单测）
# =====================================================

def _line_value(text: str, label: str) -> str | None:
    """匹配形如 ``- 学历层次：硕士（在读）`` / ``学历层次：硕士``，返回冒号后内容。"""
    pat = re.compile(rf"^\s*-?\s*{re.escape(label)}\s*[:：]\s*(.+?)\s*$", re.MULTILINE)
    m = pat.search(text)
    return m.group(1).strip() if m else None


def _strip_paren(s: str) -> str:
    """去掉中英文括号及其中内容，例如 ``硕士（在读）`` → ``硕士``。"""
    return re.sub(r"[（(].*?[)）]", "", s).strip()


def _split_locations(s: str) -> list[str]:
    parts = re.split(r"[/、，,;；\s]+", s)
    return [p for p in (x.strip() for x in parts) if p]


def parse_education(text: str) -> str:
    raw = _line_value(text, "学历层次") or _line_value(text, "学历")
    if not raw:
        return _SAFE_DEFAULT["学历"]
    cleaned = _strip_paren(raw)
    for k in ["博士", "硕士", "本科", "大专", "高中"]:
        if k in cleaned:
            return k
    return cleaned or _SAFE_DEFAULT["学历"]


def parse_major(text: str) -> str:
    return (_line_value(text, "专业") or "").strip() or _SAFE_DEFAULT["专业"]


def parse_location(text: str) -> str:
    return (_line_value(text, "所在地") or "").strip() or _SAFE_DEFAULT["所在地"]


def parse_acceptable_locations(text: str) -> list[str]:
    raw = _line_value(text, "可接受工作地域") or _line_value(text, "可接受地域")
    return _split_locations(raw) if raw else []


def parse_directions(text: str) -> list[str]:
    """解析 ``§2 目标方向`` 子项下的有序列表（``1. xxx`` / ``2. xxx``）。

    ``目标方向`` 不是 ``##`` 顶级头而是 §2 内部 bullet，需要先抽 §2 再抽子块。
    """
    sec = _section(text, r"求职方向与偏好") or _section(text, r"求职方向")
    if not sec:
        return []
    m = re.search(r"^-\s*目标方向[^\n:：]*[：:]\s*\n([\s\S]*?)(?=^-\s|\Z)", sec, re.MULTILINE)
    block = m.group(1) if m else sec
    return [
        m.group(1).strip()
        for m in re.finditer(r"^\s*\d+[.、)]\s*(.+?)\s*$", block, re.MULTILINE)
    ]


def parse_explicit_not(text: str) -> list[str]:
    """``§2`` 中 ``- 明确不做的方向：`` 子项，取每条第一个 Latin token，小写化。

    user_profile.md 里它不是 ``##`` 顶级头，而是 §2 内部的二级 bullet，
    所以这里专门做"父 bullet 起，到下一个同级 bullet 止"的子块抽取。
    """
    sec = _section(text, r"求职方向与偏好") or _section(text, r"求职方向")
    if not sec:
        return []
    m = re.search(r"^-\s*明确不做的方向[：:]\s*\n([\s\S]*?)(?=^-\s|\Z)", sec, re.MULTILINE)
    if not m:
        return []
    sub = m.group(1)
    out: list[str] = []
    for line in re.finditer(r"^\s*-\s*([A-Za-z][A-Za-z0-9+#.\-]*)", sub, re.MULTILINE):
        tok = line.group(1).strip().lower()
        if tok and tok not in out and tok != "meta":
            out.append(tok)
    return out


def parse_work_mode(text: str) -> str:
    return (_line_value(text, "工作性质偏好") or _SAFE_DEFAULT["工作性质偏好"]).strip()


def parse_salary(text: str) -> str:
    return (_line_value(text, "期望薪资区间") or _line_value(text, "期望薪资") or _SAFE_DEFAULT["期望薪资"]).strip()


def _skills_block(text: str) -> str:
    """抽 §3 ``技能清单`` 中 ``编程语言`` 子块。"""
    sec = _section(text, r"技能清单")
    if not sec:
        return ""
    m = re.search(r"编程语言[：:]([\s\S]*?)(?:\n\s*-\s*工具|\n\s*-\s*AI|\n##|\Z)", sec)
    return m.group(1) if m else sec


def parse_skills_proficient(text: str) -> list[str]:
    block = _skills_block(text)
    m = re.search(r"熟练[：:]\s*(.+)", block)
    if not m:
        return []
    return _split_skills(m.group(1))


def parse_skills_familiar(text: str) -> list[str]:
    block = _skills_block(text)
    m = re.search(r"会用[：:]\s*(.+)", block)
    if not m:
        return []
    return _split_skills(m.group(1))


def _split_skills(s: str) -> list[str]:
    s = _strip_paren(s)
    parts = re.split(r"[、,，/;；\s]+", s)
    return [p for p in (x.strip() for x in parts) if p]


def parse_project_count(text: str) -> int:
    """统计 §4 中 ``项目 N`` 出现次数（去重）。"""
    sec = _section(text, r"项目经历")
    if not sec:
        return 0
    nums = set(int(m.group(1)) for m in re.finditer(r"^\s*-\s*项目\s*(\d+)", sec, re.MULTILINE))
    return len(nums)


def parse_intern_count(text: str) -> int:
    """统计 §7 中 ``实习 N`` 且非『待补充』的实习经历数。"""
    sec = _section(text, r"实习\s*/\s*工作经历")
    if not sec:
        return 0
    n = 0
    for m in re.finditer(r"^\s*-\s*实习\s*\d+[：:]\s*(.+?)\s*$", sec, re.MULTILINE):
        if "待补充" not in m.group(1):
            n += 1
    return n


def parse_english(text: str) -> int:
    """从 §9 自评表读 ``英语读写`` 行的分数；找不到则看『英语自评』行。"""
    sec = _section(text, r"当前能力自评")
    if sec:
        m = re.search(r"英语[读写]?[读写]?\s*\|\s*(\d+)", sec)
        if m:
            return int(m.group(1))
    raw = _line_value(text, "英语自评")
    if raw:
        m = re.search(r"\d+", raw)
        if m:
            return int(m.group(0))
    return _SAFE_DEFAULT["英语自评"]


# =====================================================
# 工具
# =====================================================

def _section(text: str, header_pat: str) -> str:
    """抽取 ``## N. <header_pat>...`` 到下一个 ``## `` 之间的内容。"""
    m = re.search(rf"^##\s*\d+\.[^\n]*{header_pat}[^\n]*\n([\s\S]*?)(?=^##\s|\Z)", text, re.MULTILINE)
    return m.group(1) if m else ""


# =====================================================
# 主入口
# =====================================================

def load_profile(path: str | None = None, *, use_cache: bool = True) -> dict[str, Any]:
    """从 ``user_profile.md`` 解析出 ``run_match`` 能用的 profile dict。

    流程：
      1. 优先解析 Markdown；缺字段就回退到 ``profiles/p1_zhangyi_ai.json``；
      2. 再缺就用 ``_SAFE_DEFAULT`` 兜底；
      3. 保证返回值一定包含 ``REQUIRED_KEYS`` 全部 13 个键。
    """
    md_path = path or PROFILE_MD

    if use_cache and _CACHE["data"] is not None and _CACHE["path"] == md_path:
        try:
            mtime = os.path.getmtime(md_path)
            if mtime == _CACHE["mtime"]:
                return dict(_CACHE["data"])
        except OSError:
            pass

    text = ""
    if os.path.exists(md_path):
        with open(md_path, "r", encoding="utf-8") as f:
            text = f.read()

    parsed: dict[str, Any] = {
        "学历": parse_education(text) if text else "",
        "专业": parse_major(text) if text else "",
        "所在地": parse_location(text) if text else "",
        "可接受地域": parse_acceptable_locations(text) if text else [],
        "方向优先级": parse_directions(text) if text else [],
        "明确不做": parse_explicit_not(text) if text else [],
        "工作性质偏好": parse_work_mode(text) if text else "不限",
        "期望薪资": parse_salary(text) if text else "",
        "熟练技能": parse_skills_proficient(text) if text else [],
        "会用技能": parse_skills_familiar(text) if text else [],
        "项目数量": parse_project_count(text) if text else 0,
        "实习数量": parse_intern_count(text) if text else 0,
        "英语自评": parse_english(text) if text else _SAFE_DEFAULT["英语自评"],
    }

    fallback: dict[str, Any] = {}
    if os.path.exists(PROFILE_JSON_FALLBACK):
        try:
            with open(PROFILE_JSON_FALLBACK, "r", encoding="utf-8") as f:
                fallback = json.load(f)
        except (OSError, json.JSONDecodeError):
            fallback = {}

    out: dict[str, Any] = {}
    list_keys = {"可接受地域", "方向优先级", "明确不做", "熟练技能", "会用技能"}
    for key in REQUIRED_KEYS:
        v = parsed.get(key)
        # text 非空时 list 字段保留解析结果（即使为空），不再被 fallback 覆盖，
        # 否则用户从 user_profile.md 删掉某项，行为不会变化（状态驱动名存实亡）。
        is_list_with_text = key in list_keys and bool(text)
        if _is_empty(v) and not is_list_with_text:
            v = fallback.get(key)
        if _is_empty(v) and not is_list_with_text:
            v = _SAFE_DEFAULT[key]
        if v is None:
            v = _SAFE_DEFAULT[key]
        out[key] = v

    out["_source"] = "user_profile.md" if text else (
        "profiles/p1_zhangyi_ai.json" if fallback else "safe_default"
    )

    if use_cache and os.path.exists(md_path):
        _CACHE["mtime"] = os.path.getmtime(md_path)
        _CACHE["path"] = md_path
        _CACHE["data"] = dict(out)

    return out


def _is_empty(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, (list, str, dict)) and len(v) == 0:
        return True
    return False


def reset_cache() -> None:
    """测试 / 状态变更后强制下次重新解析。"""
    _CACHE["mtime"] = None
    _CACHE["path"] = None
    _CACHE["data"] = None


if __name__ == "__main__":
    import json as _j
    p = load_profile()
    print(_j.dumps(p, ensure_ascii=False, indent=2))
