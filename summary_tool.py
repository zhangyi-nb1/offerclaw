# -*- coding: utf-8 -*-
"""
OfferClaw · 学习留痕复盘工具 (summary_tool.py)

职责：
    自动化执行 summary_prompt.md 的复盘流程。
    - 单日模式：读 daily_log.md 中指定日期块（默认今天）→ LLM 复盘 → 落盘
    - 周度模式：读最近 7 天 → LLM 周度复盘 → 落盘

使用：
    python summary_tool.py                  # 今日复盘
    python summary_tool.py --date 2026-04-25
    python summary_tool.py --weekly         # 本周复盘
"""

import argparse
import datetime
import os
import re
import sys

import requests

from day1_api_starter import API_KEY_ENV, build_zhipu_jwt, get_llm_config, load_local_env

DAILY_LOG_PATH = "daily_log.md"
SUMMARY_PROMPT_PATH = "summary_prompt.md"
SOURCE_POLICY_PATH = "source_policy.md"
TARGET_RULES_PATH = "target_rules.md"
OUTPUT_DIR = "summaries"


def read_text(path: str) -> str:
    if not os.path.exists(path):
        raise FileNotFoundError(f"必需文件缺失：{path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def extract_date_block(log: str, date_str: str) -> str:
    """从 daily_log.md 抓出 ## <date> 开头的整块。"""
    pattern = rf"(##\s+{re.escape(date_str)}.*?)(?=\n##\s+\d{{4}}-\d{{2}}-\d{{2}}|\Z)"
    m = re.search(pattern, log, re.DOTALL)
    return m.group(1).strip() if m else ""


def extract_recent_blocks(log: str, days: int = 7) -> str:
    """抓最近 days 天的所有 ## <YYYY-MM-DD> 块。"""
    today = datetime.date.today()
    blocks = []
    for i in range(days):
        d = (today - datetime.timedelta(days=i)).isoformat()
        b = extract_date_block(log, d)
        if b:
            blocks.append(b)
    return "\n\n".join(blocks)


def build_messages(prompt: str, source_policy: str, target_rules: str,
                   log_block: str, mode: str, date_str: str) -> list:
    system = (
        "你是 OfferClaw，按 summary_prompt.md 的 9 步流程做一次复盘。\n\n"
        f"========== summary_prompt.md ==========\n{prompt}\n\n"
        f"========== source_policy.md ==========\n{source_policy}\n\n"
        f"========== target_rules.md ==========\n{target_rules}\n"
    )
    structured_ask = (
        "\n\n在正文复盘之后，另起一段，用如下 ```json 代码块输出结构化复盘"
        "（供系统沉淀「次日调整规则」）：\n"
        "```json\n"
        '{\n'
        '  "main_tag": "补技能|补项目|补面试|岗位调研|投递准备",\n'
        '  "deviation_score": 0-100,\n'
        '  "completed": ["..."],\n'
        '  "incomplete": ["..."],\n'
        '  "blockers": ["..."],\n'
        '  "next_day_suggestion": "..."\n'
        '}\n'
        "```\n"
        "deviation_score：0=完全按计划，100=完全偏离。"
    )
    if mode == "daily":
        user = (
            f"请按 summary_prompt.md 单日模式复盘 {date_str}。\n"
            "下面是 daily_log.md 中该日期块的全文：\n\n"
            f"========== daily_log [{date_str}] ==========\n{log_block}"
            + structured_ask
        )
    else:
        user = (
            f"请按 summary_prompt.md 周度模式跑本周复盘（截至 {date_str}）。\n"
            "下面是最近 7 天的 daily_log.md 内容：\n\n"
            f"========== daily_log [recent 7d] ==========\n{log_block}"
        )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def call_llm(messages, api_key) -> str:
    cfg = _resolve_chat_config(api_key)
    payload = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 3000,
    }
    if cfg.get("reasoning_effort"):
        payload["reasoning_effort"] = cfg["reasoning_effort"]
    resp = requests.post(
        f"{cfg['api_base']}/chat/completions",
        headers={"Authorization": f"Bearer {cfg['bearer']}", "Content-Type": "application/json"},
        json=payload,
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"].get("content", "") or ""


def _resolve_chat_config(api_key: str) -> dict:
    """Resolve chat endpoint/auth for both current proxy and legacy Zhipu callers."""
    cfg = get_llm_config()
    zhipu_key = os.environ.get("ZHIPU_API_KEY", "")
    if api_key and api_key == zhipu_key:
        return {
            "api_base": "https://open.bigmodel.cn/api/paas/v4",
            "model": "glm-4-flash",
            "bearer": build_zhipu_jwt(api_key),
            "reasoning_effort": "",
        }
    bearer = build_zhipu_jwt(api_key) if cfg["is_zhipu"] else api_key
    return {**cfg, "bearer": bearer}


def _sig_tokens(text: str) -> set:
    """抽取显著词：英文/数字技术词（≥2 字符）+ 中文 2-gram。用于完成度比对。"""
    t = str(text)
    toks = set(m.lower() for m in re.findall(r"[A-Za-z][A-Za-z0-9_+\-\.]{1,}", t))
    # 中文按标点切块后取 2-gram
    for chunk in re.split(r"[\s\d\.,，。、:：;；()（）\[\]【】\-—/·]+", t):
        chunk = re.sub(r"[A-Za-z0-9_+\-\.]+", "", chunk)
        for i in range(len(chunk) - 1):
            toks.add(chunk[i:i + 2])
    return toks


# 比对时忽略的"框架性"高频词：几乎每条计划/留痕里都有，不构成完成证据
_STOP_2GRAMS = {"推进", "本周", "主线", "交付", "完成", "学习", "今日", "今天",
                "任务", "计划", "建议", "继续", "开始", "进行", "第周"}


def analyze_incomplete(done: list, planned: list) -> list:
    """对照"OfferClaw 今日计划"判定未完成项（确定性启发式，不调 LLM）。

    规则：planned 中某项，若没有任一 done 条目与其共享 ≥2 个显著词
    （或 ≥1 个英文技术词），则判为未完成。done 为空 → 全部未完成。
    晚间 LLM 复盘会在此基础上做更细的偏离度分析；这里只做即时反馈。
    """
    done = [str(d).strip() for d in (done or []) if str(d).strip()]
    planned = [str(p).strip() for p in (planned or []) if str(p).strip()]
    if not planned:
        return []
    if not done:
        return planned[:]
    done_toks = set()
    done_tech = set()
    for d in done:
        toks = _sig_tokens(d)
        done_toks |= toks
        done_tech |= {t for t in toks if re.match(r"^[a-z]", t)}
    incomplete = []
    for p in planned:
        p_toks = _sig_tokens(p) - _STOP_2GRAMS
        p_tech = {t for t in p_toks if re.match(r"^[a-z]", t)}
        overlap = p_toks & done_toks
        tech_hit = bool(p_tech & done_tech)
        if tech_hit or len(overlap) >= 2:
            continue
        incomplete.append(p)
    return incomplete


def append_structured_daily_log(tag: str = "", done=None, todo=None,
                                notes: str = "", date_str: str = None) -> dict:
    """把结构化留痕写入 daily_log.md，字段用 ### 分节（与 P2 _parse_log_block 对齐）。

    CLI（offerclaw_cli.cmd_log）、Web 表单（/api/daily/log）、GitHub 同步共用此写入器，
    保证全项目留痕格式一致、能被晚间复盘正确解析。
    """
    import datetime as _dt
    done = [d for d in (done or []) if str(d).strip()]
    todo = [t for t in (todo or []) if str(t).strip()]
    notes = (notes or "").strip()
    date_str = date_str or _dt.date.today().isoformat()

    lines = [f"\n## {date_str}\n"]
    if tag:
        lines += ["### 今日主线标签", tag, ""]
    lines += ["### 已完成"]
    lines += [f"- {d}" for d in done] or ["- 【待补充】"]
    lines += ["", "### 未完成"]
    lines += [f"- {t}" for t in todo] or ["- （无）"]
    if notes:
        lines += ["", "### 学习留痕", notes]
    entry = "\n".join(lines) + "\n"

    with open(DAILY_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(entry)
    return {
        "status": "ok", "date": date_str, "main_tag": tag,
        "done_count": len(done), "todo_count": len(todo), "has_notes": bool(notes),
    }


def _parse_log_block(block: str, date_str: str) -> dict:
    """从 daily_log 日期块里确定性抽取结构化字段（不依赖 LLM）。

    抓取：主线标签、实际完成项、未完成/偏离信号。daily_log 模板含
    「今日主线标签 / 实际完成 / 偏离度判断 / 明日建议」等字段。
    """
    main_tag = ""
    m = re.search(r"主线标签[：:\s]*([^\n（(]+)", block)
    if m:
        main_tag = m.group(1).strip(" `*")

    def _section(name: str) -> list[str]:
        # 抓 "### <name>" 或 "<name>：" 后面的列表/段落，到下一个 ## / ### 为止。
        # 注意：行尾 \n 已被 .*\n? 吃掉，故下一标题的 lookahead 不带前导 \n。
        pat = rf"(?:#+\s*{name}|{name})[：:\s]*\n?((?:.*\n?)*?)(?=#{{1,6}}\s|\Z)"
        mm = re.search(pat, block)
        if not mm:
            return []
        items = []
        for ln in mm.group(1).splitlines():
            s = ln.strip(" -*•\t")
            if s and not s.startswith("#") and len(s) >= 2:
                items.append(s)
        return items[:8]

    # 字段名与 daily_log 模板（已完成/未完成）及微信留痕（cmd_log）对齐
    completed = _section("已完成") or _section("实际完成") or _section("实际")
    incomplete = _section("未完成")
    return {
        "date": date_str,
        "main_tag": main_tag,
        "completed": completed,
        "incomplete": incomplete,
    }


def _extract_llm_json(summary_text: str) -> dict:
    """若 LLM 输出里带 ```json ... ``` 结构化块，鲁棒解析出来；失败返回 {}。"""
    import json as _json
    m = re.search(r"```json\s*(\{.*?\})\s*```", summary_text, re.DOTALL)
    if not m:
        m = re.search(r"(\{[^{}]*\"deviation_score\"[^{}]*\})", summary_text, re.DOTALL)
    if not m:
        return {}
    try:
        return _json.loads(m.group(1))
    except Exception:
        return {}


def build_structured_reflection(block: str, date_str: str, summary_text: str) -> dict:
    """合并确定性解析 + LLM JSON 增强，产出一条结构化复盘。

    deviation_score 优先用 LLM 给的；没有就按 incomplete/completed 比例估算。
    """
    base = _parse_log_block(block, date_str)
    llm = _extract_llm_json(summary_text)

    completed = llm.get("completed") or base["completed"]
    incomplete = llm.get("incomplete") or base["incomplete"]

    if "deviation_score" in llm:
        score = int(llm.get("deviation_score") or 0)
    else:
        total = len(completed) + len(incomplete)
        score = int(round(100 * len(incomplete) / total)) if total else 0

    return {
        "date": date_str,
        "main_tag": llm.get("main_tag") or base["main_tag"],
        "deviation_score": max(0, min(100, score)),
        "completed": completed,
        "incomplete": incomplete,
        "blockers": llm.get("blockers", []) or [],
        "next_day_suggestion": llm.get("next_day_suggestion", "") or "",
    }


def record_and_distill(reflection: dict) -> dict:
    """把结构化复盘写入分层 memory 并沉淀调整规则。失败静默（不阻塞复盘落盘）。"""
    try:
        from memory_layers import (
            EpisodicMemory, SemanticMemory,
            record_reflection, distill_reflections_to_semantic, get_active_adjustments,
        )
        epi, sem = EpisodicMemory(), SemanticMemory()
        record_reflection(epi, reflection)
        distill_reflections_to_semantic(epi, sem)
        return {"ok": True, "active_adjustments": get_active_adjustments(sem)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def save(content: str, mode: str, date_str: str) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    suffix = "weekly" if mode == "weekly" else "daily"
    path = os.path.join(OUTPUT_DIR, f"summary_{suffix}_{date_str}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def main():
    parser = argparse.ArgumentParser(description="OfferClaw 复盘工具")
    parser.add_argument("--date", help="单日模式日期 YYYY-MM-DD（默认今天）")
    parser.add_argument("--weekly", action="store_true", help="周度复盘")
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    load_local_env()
    api_key = os.environ.get(API_KEY_ENV)
    if not api_key:
        print(f"[ERROR] 未检测到 {API_KEY_ENV}")
        sys.exit(1)

    today = datetime.date.today().isoformat()
    date_str = args.date or today
    mode = "weekly" if args.weekly else "daily"

    print(f"[1/3] 读取依赖文件 + daily_log...")
    prompt = read_text(SUMMARY_PROMPT_PATH)
    sp = read_text(SOURCE_POLICY_PATH)
    tr = read_text(TARGET_RULES_PATH)
    log = read_text(DAILY_LOG_PATH)

    if mode == "daily":
        block = extract_date_block(log, date_str)
        if not block:
            print(f"[WARN] daily_log.md 中找不到 {date_str} 的块，仍然把全文喂给 LLM。")
            block = log[-3000:]
    else:
        block = extract_recent_blocks(log, days=7)
        if not block:
            print(f"[WARN] 最近 7 天无任何日期块，喂全文末尾。")
            block = log[-5000:]

    print(f"[2/3] 调用 LLM ({mode}, {date_str}) ...")
    messages = build_messages(prompt, sp, tr, block, mode, date_str)
    out = call_llm(messages, api_key)

    print(f"[3/3] 写入文件...")
    path = save(out, mode, date_str)
    print(f"[OK] 复盘已保存：{path}")

    # P2：单日复盘后沉淀结构化记录 → 分层 memory → 次日调整规则
    if mode == "daily":
        reflection = build_structured_reflection(block, date_str, out)
        result = record_and_distill(reflection)
        if result.get("ok"):
            print(f"[MEMORY] 已记录结构化复盘（偏离度={reflection['deviation_score']}，"
                  f"完成 {len(reflection['completed'])} / 未完成 {len(reflection['incomplete'])}）")
            adj = result.get("active_adjustments", [])
            if adj:
                print("[ADJUST] 当前生效的次日调整规则：")
                for a in adj:
                    print(f"  - {a}")
        else:
            print(f"[MEMORY] 跳过沉淀：{result.get('error')}")

    print("-" * 60)
    print(out[:1500])
    if len(out) > 1500:
        print(f"\n...（截断，完整 {len(out)} 字符见 {path}）")


if __name__ == "__main__":
    main()
