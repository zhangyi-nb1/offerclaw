# -*- coding: utf-8 -*-
"""memory_layers.py — OfferClaw 分层 Memory（V4 §5）

把过去扁平的 ``memory.json`` 升级为认知心理学常见的三层结构：

* **Episodic（情景记忆）**：append-only 事件流（``logs/memory/episodic.jsonl``）。
  每次"匹配 / 投递 / 复盘"都追加一条不可变事件，类似 git log。
* **Semantic（语义记忆）**：从事件流中**沉淀**出来的稳定偏好与画像
  （``logs/memory/semantic.json``）。例如「用户偏好远程」「对 Java 类岗位
  保持距离」。是 KV 结构，可被覆盖。
* **Procedural（程序记忆）**：学到的 SOP / 启发式
  （``logs/memory/procedural.json``）。例如「投 RL 类岗位时简历必须强调
  PyTorch」。每条 SOP 是名+正文+触发场景。

设计原则：
1. **文件型 / 零依赖**：与项目"状态走文件"哲学一致；不引入 SQLite。
2. **路径可注入**：所有类都接受 ``base_dir`` 参数，便于单元测试 monkey-patch。
3. **append-only 不可改写**：episodic 只能 append；semantic/procedural 可改
   但保留 ``updated_at`` 时间戳。
4. **轻量沉淀逻辑**：``distill_to_semantic()`` 是占位用的"从事件总结偏好"
   钩子，当前实现是简单规则（统计某类事件出现频次）。LLM 沉淀留给上层。
"""

from __future__ import annotations

import datetime
import json
import os
from typing import Any, Callable

BASE_DIR_DEFAULT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "logs", "memory"
)


def _iso_now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _ensure(d: str) -> None:
    os.makedirs(d, exist_ok=True)


# =====================================================
# Episodic
# =====================================================

class EpisodicMemory:
    """append-only JSONL 事件流。读时可按谓词过滤。"""

    FILE = "episodic.jsonl"

    def __init__(self, base_dir: str | None = None) -> None:
        self.base_dir = base_dir or BASE_DIR_DEFAULT
        _ensure(self.base_dir)
        self.path = os.path.join(self.base_dir, self.FILE)

    def append(self, event: dict[str, Any]) -> dict:
        """追加一条事件；自动注入 ``ts_iso`` 与 ``id``。"""
        full = {
            "id": f"ep_{int(datetime.datetime.now().timestamp() * 1000)}",
            "ts_iso": _iso_now(),
            **event,
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(full, ensure_ascii=False) + "\n")
        return full

    def all(self) -> list[dict]:
        if not os.path.exists(self.path):
            return []
        out: list[dict] = []
        with open(self.path, "r", encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    out.append(json.loads(ln))
                except json.JSONDecodeError:
                    continue
        return out

    def recent(self, limit: int = 20) -> list[dict]:
        return self.all()[-limit:]

    def filter(self, predicate: Callable[[dict], bool]) -> list[dict]:
        return [e for e in self.all() if predicate(e)]

    def count_by(self, key: str) -> dict[str, int]:
        """按 key 的取值统计事件数（用于沉淀阶段）。"""
        out: dict[str, int] = {}
        for e in self.all():
            v = str(e.get(key, ""))
            if not v:
                continue
            out[v] = out.get(v, 0) + 1
        return out


# =====================================================
# Semantic
# =====================================================

class SemanticMemory:
    """JSON KV 偏好库。可读可写，每次更新打 ``updated_at`` 时间戳。"""

    FILE = "semantic.json"

    def __init__(self, base_dir: str | None = None) -> None:
        self.base_dir = base_dir or BASE_DIR_DEFAULT
        _ensure(self.base_dir)
        self.path = os.path.join(self.base_dir, self.FILE)

    def _load(self) -> dict:
        if not os.path.exists(self.path):
            return {"_meta": {"updated_at": _iso_now()}}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {"_meta": {"updated_at": _iso_now()}}

    def _save(self, data: dict) -> None:
        data.setdefault("_meta", {})["updated_at"] = _iso_now()
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        return self._load().get(key, default)

    def set(self, key: str, value: Any) -> None:
        data = self._load()
        data[key] = value
        self._save(data)

    def delete(self, key: str) -> bool:
        data = self._load()
        if key in data:
            del data[key]
            self._save(data)
            return True
        return False

    def all(self) -> dict:
        return self._load()


# =====================================================
# Procedural
# =====================================================

class ProceduralMemory:
    """学到的 SOP / 启发式集合。每条带名+正文+触发场景+更新时间。"""

    FILE = "procedural.json"

    def __init__(self, base_dir: str | None = None) -> None:
        self.base_dir = base_dir or BASE_DIR_DEFAULT
        _ensure(self.base_dir)
        self.path = os.path.join(self.base_dir, self.FILE)

    def _load(self) -> dict:
        if not os.path.exists(self.path):
            return {"sops": {}, "_meta": {"updated_at": _iso_now()}}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {"sops": {}, "_meta": {"updated_at": _iso_now()}}

    def _save(self, data: dict) -> None:
        data.setdefault("_meta", {})["updated_at"] = _iso_now()
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add(self, name: str, *, body: str, trigger: str = "") -> dict:
        data = self._load()
        sop = {
            "name": name,
            "body": body,
            "trigger": trigger,
            "updated_at": _iso_now(),
        }
        data["sops"][name] = sop
        self._save(data)
        return sop

    def get(self, name: str) -> dict | None:
        return self._load()["sops"].get(name)

    def list(self) -> list[dict]:
        return list(self._load()["sops"].values())

    def remove(self, name: str) -> bool:
        data = self._load()
        if name in data["sops"]:
            del data["sops"][name]
            self._save(data)
            return True
        return False


# =====================================================
# Distillation: episodic → semantic
# =====================================================

def distill_to_semantic(epi: EpisodicMemory, sem: SemanticMemory) -> dict:
    """从 episodic 事件流中沉淀偏好到 semantic memory。

    当前实现只做几条简单规则：
    1. 统计 ``event.kind = "match_run"`` 中 status 的分布。
    2. 统计被标记 ``direction`` 的频次，把最高频写入 ``preferred_direction``。

    LLM 化的沉淀（"用一段话总结用户偏好"）留给上层调用方，
    本函数只负责机械统计。
    """
    events = epi.all()
    match_events = [e for e in events if e.get("kind") == "match_run"]
    if not match_events:
        return {"distilled": False, "reason": "no_match_events"}

    status_dist: dict[str, int] = {}
    direction_dist: dict[str, int] = {}
    for e in match_events:
        s = e.get("status", "")
        d = e.get("direction", "")
        if s:
            status_dist[s] = status_dist.get(s, 0) + 1
        if d:
            direction_dist[d] = direction_dist.get(d, 0) + 1

    sem.set("match_status_distribution", status_dist)
    if direction_dist:
        top = max(direction_dist.items(), key=lambda kv: kv[1])
        sem.set("preferred_direction", {
            "value": top[0],
            "count": top[1],
            "from_n_events": len(match_events),
        })
    sem.set("last_distilled_at", _iso_now())
    return {
        "distilled": True,
        "n_match_events": len(match_events),
        "status_dist": status_dist,
        "direction_dist": direction_dist,
    }


# =====================================================
# P2：复盘 → 调整闭环（reflection → adjustments）
# =====================================================

ADJUSTMENTS_KEY = "daily_adjustments"


def record_reflection(epi: EpisodicMemory, reflection: dict) -> dict:
    """把一条结构化复盘写入 episodic（kind=reflection）。

    ``reflection`` 约定字段（缺省安全）：
      date, main_tag, deviation_score(0-100), completed[], incomplete[],
      blockers[], next_day_suggestion
    """
    event = {
        "kind": "reflection",
        "date": reflection.get("date", ""),
        "main_tag": reflection.get("main_tag", ""),
        "deviation_score": int(reflection.get("deviation_score", 0) or 0),
        "completed": list(reflection.get("completed", []) or []),
        "incomplete": list(reflection.get("incomplete", []) or []),
        "blockers": list(reflection.get("blockers", []) or []),
        "next_day_suggestion": reflection.get("next_day_suggestion", ""),
    }
    return epi.append(event)


def _norm_task_key(text: str) -> str:
    """把一条任务/缺口文本归一成用于跨天比对的关键词（取核心名词短语）。"""
    import re
    t = re.sub(r"[\s\d\.、:：（）()\[\]【】\-—]+", "", text)
    return t[:12]  # 取前若干字符做粗粒度聚类，避免措辞细微差异导致漏判


def distill_reflections_to_semantic(
    epi: EpisodicMemory,
    sem: SemanticMemory,
    recent_n: int = 5,
    streak: int = 3,
) -> dict:
    """从最近的 reflection 事件沉淀「次日调整规则」到 semantic 层。

    规则（确定性，可单测）：
    1. **高偏离连续**：最近 ``streak`` 天 deviation_score 均 ≥ 50
       → 规则 high_deviation_streak（建议减少每日任务量）。
    2. **反复未完成**：某类任务在最近 ``recent_n`` 天里 ≥ ``streak`` 次出现在
       incomplete → 规则 recurring_incomplete:<关键词>（建议减量/拆细/前置）。

    结果写入 ``sem[ADJUSTMENTS_KEY] = {"rules": [...], "updated_at": ...}``。
    """
    reflections = [e for e in epi.all() if e.get("kind") == "reflection"]
    recent = reflections[-recent_n:]
    rules: list[dict] = []

    # 规则 1：高偏离连续
    if len(recent) >= streak:
        tail = recent[-streak:]
        if all(int(e.get("deviation_score", 0) or 0) >= 50 for e in tail):
            rules.append({
                "pattern": "high_deviation_streak",
                "detail": f"最近 {streak} 天偏离度均 ≥ 50，建议下调每日任务量、优先保 1 个主线产出。",
                "since": tail[0].get("date", ""),
            })

    # 规则 2：反复未完成
    counter: dict[str, dict] = {}
    for e in recent:
        seen_in_day = set()
        for item in e.get("incomplete", []):
            key = _norm_task_key(item)
            if not key or key in seen_in_day:
                continue
            seen_in_day.add(key)
            slot = counter.setdefault(key, {"count": 0, "sample": item})
            slot["count"] += 1
    for key, slot in counter.items():
        if slot["count"] >= streak:
            rules.append({
                "pattern": f"recurring_incomplete:{key}",
                "detail": f"「{slot['sample']}」在最近 {len(recent)} 天里有 {slot['count']} 天未完成，建议减量/拆细/前置到精力高的时段。",
                "since": recent[0].get("date", ""),
            })

    sem.set(ADJUSTMENTS_KEY, {"rules": rules, "updated_at": _iso_now()})
    return {"distilled": True, "n_reflections": len(recent), "rules": rules}


def get_active_adjustments(sem: SemanticMemory) -> list[str]:
    """读出当前生效的调整建议文案列表（供 today_advice 等消费）。"""
    data = sem.get(ADJUSTMENTS_KEY) or {}
    return [r.get("detail", "") for r in data.get("rules", []) if r.get("detail")]


if __name__ == "__main__":
    epi = EpisodicMemory()
    sem = SemanticMemory()
    proc = ProceduralMemory()
    epi.append({"kind": "match_run", "jd_title": "DEMO",
                "status": "当前适合投递", "direction": "主方向"})
    sem.set("prefer_remote", True)
    proc.add("nio_vas_resume", body="强调 LangGraph / RAG / FastAPI",
             trigger="JD 含 大模型应用开发实习")
    print("episodic:", len(epi.all()))
    print("semantic:", sem.all())
    print("procedural:", proc.list())
    print("distill:", distill_to_semantic(epi, sem))
