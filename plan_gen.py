# -*- coding: utf-8 -*-
"""
OfferClaw · 路线规划最小代码版（plan_gen.py）

职责：
    给定一份 JD 匹配产生的"缺口清单"，按 plan_prompt.md 的契约调用
    LLM 生成一份 4 周可执行计划。

设计取舍（V1 阶段）：
    - 不在本地复现 plan_prompt.md 的全部 9 步逻辑；把 prompt 整篇喂给 LLM，让 LLM 走流程
    - 本脚本只负责：组装上下文（profile + plan_prompt + 缺口清单）→ 调 LLM → 落盘
    - 不做缺口的本地解析校验（那是 plan_prompt.md 第 2 步的职责，由 LLM 在内部做）

输入：
    1. user_profile.md（自动读取）
    2. plan_prompt.md（自动读取）
    3. 缺口清单：命令行参数 --gaps <file> 或 stdin 粘贴

输出：
    plans/plan_<YYYYMMDD_HHMMSS>.md

使用：
    python plan_gen.py --gaps gaps.md
    或
    python plan_gen.py            # 然后从 stdin 粘贴，输入 EOF（Ctrl+Z 回车 / Ctrl+D）结束
"""

import argparse
import datetime
import os
import sys

import requests

from agent_demo import (
    API_BASE,
    API_KEY_ENV,
    MODEL,
    build_zhipu_jwt,
    load_local_env,
)


PROFILE_PATH = "user_profile.md"
PLAN_PROMPT_PATH = "plan_prompt.md"
DAILY_LOG_PATH = "daily_log.md"
SOURCE_POLICY_PATH = "source_policy.md"
TARGET_RULES_PATH = "target_rules.md"
OUTPUT_DIR = "plans"


def read_text(path: str) -> str:
    if not os.path.exists(path):
        raise FileNotFoundError(f"必需文件缺失：{path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def read_gaps(args) -> str:
    if args.gaps:
        return read_text(args.gaps)
    print("请粘贴缺口清单，输入完成后按 Ctrl+Z 回车（Windows）或 Ctrl+D（Unix）结束：")
    data = sys.stdin.read().strip()
    if not data:
        raise ValueError("缺口清单为空，已退出")
    return data


def build_messages(profile: str, plan_prompt: str, daily_log: str,
                   source_policy: str, target_rules: str, gaps: str) -> list:
    """组装要发给 LLM 的 messages。

    设计：把 5 份依赖文件作为 system 上下文，缺口清单作为 user 消息。
    LLM 内部按 plan_prompt 的 9 步流程执行。
    """
    system_content = (
        "你是 OfferClaw，部署在长期会话中的求职作战官。\n"
        "你接下来要严格按 plan_prompt.md 的指令执行一次路线规划。\n"
        "下面是你必须读取的依赖文件全文。\n\n"
        f"========== plan_prompt.md ==========\n{plan_prompt}\n\n"
        f"========== user_profile.md ==========\n{profile}\n\n"
        f"========== target_rules.md ==========\n{target_rules}\n\n"
        f"========== daily_log.md ==========\n{daily_log}\n\n"
        f"========== source_policy.md ==========\n{source_policy}\n"
    )

    user_content = (
        "请按 plan_prompt.md 的 9 步流程，基于下面这份缺口清单生成 4 周计划。\n"
        "今天日期是 " + datetime.date.today().isoformat() + "。\n\n"
        "========== 缺口清单 ==========\n" + gaps
    )

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]


def call_llm_plain(messages, api_key, max_tokens: int = 4000) -> str:
    """调用智谱 LLM，不带 tools（规划是单次纯文本生成）。"""
    bearer = build_zhipu_jwt(api_key)
    url = f"{API_BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {bearer}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": max_tokens,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"].get("content", "") or ""


def call_llm_stream(messages, api_key, max_tokens: int = 4000):
    """调用智谱 LLM，stream=True，逐 token yield str。供 SSE 端点消费。"""
    import json as _json
    bearer = build_zhipu_jwt(api_key)
    url = f"{API_BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {bearer}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": max_tokens,
        "stream": True,
    }
    with requests.post(url, headers=headers, json=payload, timeout=120, stream=True) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            if isinstance(line, bytes):
                line = line.decode("utf-8", "replace")
            if line.startswith("data: "):
                data = line[6:]
                if data.strip() == "[DONE]":
                    return
                try:
                    chunk = _json.loads(data)
                    delta = chunk["choices"][0]["delta"].get("content", "")
                    if delta:
                        yield delta
                except Exception:
                    pass


def save_plan(content: str) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(OUTPUT_DIR, f"plan_{ts}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def main():
    parser = argparse.ArgumentParser(description="OfferClaw 路线规划生成器")
    parser.add_argument("--gaps", "-g", help="缺口清单文件路径（默认从 stdin 读）")
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    load_local_env()
    api_key = os.environ.get(API_KEY_ENV)
    if not api_key:
        print(f"[ERROR] 未检测到环境变量 {API_KEY_ENV}")
        sys.exit(1)

    print("[1/4] 读取依赖文件...")
    profile = read_text(PROFILE_PATH)
    plan_prompt = read_text(PLAN_PROMPT_PATH)
    daily_log = read_text(DAILY_LOG_PATH)
    source_policy = read_text(SOURCE_POLICY_PATH)
    target_rules = read_text(TARGET_RULES_PATH)

    print("[2/4] 读取缺口清单...")
    gaps = read_gaps(args)

    print("[3/4] 调用 LLM 生成计划（最长 120 秒）...")
    messages = build_messages(profile, plan_prompt, daily_log,
                              source_policy, target_rules, gaps)
    plan_text = call_llm_plain(messages, api_key)

    print("[4/4] 写入文件...")
    out_path = save_plan(plan_text)
    print(f"\n✓ 计划已生成：{out_path}")
    print("=" * 60)
    print(plan_text[:2000])
    if len(plan_text) > 2000:
        print(f"\n...（截断，完整内容见 {out_path}，共 {len(plan_text)} 字符）")


if __name__ == "__main__":
    main()
