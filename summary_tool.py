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

from agent_demo import API_BASE, API_KEY_ENV, MODEL, build_zhipu_jwt, load_local_env

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
    if mode == "daily":
        user = (
            f"请按 summary_prompt.md 单日模式复盘 {date_str}。\n"
            "下面是 daily_log.md 中该日期块的全文：\n\n"
            f"========== daily_log [{date_str}] ==========\n{log_block}"
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
    bearer = build_zhipu_jwt(api_key)
    resp = requests.post(
        f"{API_BASE}/chat/completions",
        headers={"Authorization": f"Bearer {bearer}", "Content-Type": "application/json"},
        json={"model": MODEL, "messages": messages, "temperature": 0.3, "max_tokens": 3000},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"].get("content", "") or ""


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
    print("-" * 60)
    print(out[:1500])
    if len(out) > 1500:
        print(f"\n...（截断，完整 {len(out)} 字符见 {path}）")


if __name__ == "__main__":
    main()
