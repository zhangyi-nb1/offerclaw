# -*- coding: utf-8 -*-
"""
OfferClaw · Day 1 Task 1 · LLM API 调用最小可运行脚本

目的：
    验证 "Python -> HTTP 请求 -> LLM 云端 -> 解析响应" 全链路可跑通。
    这是所有 LLM 应用和 Agent 项目的第一块积木。
    本脚本本身也会作为 Day 2 做 Agent Demo 的代码底座。

v0.6.3 (2026-05) 起：
    默认 provider 从智谱 GLM-4-Flash 切到 **OpenAI 兼容代理**
    （订阅中转站把 ChatGPT 账号包装成 OpenAI API）。
    模型 ``gpt-5.4``，reasoning_effort ``medium``。
    Embeddings 由 rag_tools.py 的 EMBEDDING_PROVIDER 配置决定。

使用步骤：
    1. 把 ``.env.local`` 里的 ``OPENAI_API_KEY`` / ``OPENAI_BASE_URL`` 设好。
    2. 安装唯一的第三方依赖：``pip install requests``
    3. 运行：``python day1_api_starter.py``

成功标志：
    控制台打印一段完整的 LLM 响应文本 + token usage 统计。
"""

import base64
import hashlib
import hmac
import json
import os
import sys
import time

import requests

# =====================================================
# Provider 配置 —— 想换 Provider 只改这几个常量（或改 .env.local 覆盖）
# =====================================================

# 默认：本机 OpenAI 兼容代理（订阅账号中转，gpt-5.4 + medium effort）
DEFAULT_API_BASE = "http://127.0.0.1:8080/v1"
DEFAULT_MODEL = "gpt-5.4"
DEFAULT_REASONING_EFFORT = "medium"
DEFAULT_TIMEOUT = 60.0

API_KEY_ENV = "OPENAI_API_KEY"

# 从 .env.local 或 shell 环境覆盖（env 优先级 > 这里的 default）
def _resolved(envvar: str, default: str) -> str:
    """``os.environ.get`` with a non-empty default fallback."""
    value = os.environ.get(envvar, "").strip()
    return value if value else default


# 备选 · 智谱 GLM（如果想切回旧路径，把下面 4 行解注释、注释掉上面的 OpenAI 默认即可）：
# DEFAULT_API_BASE = "https://open.bigmodel.cn/api/paas/v4"
# DEFAULT_MODEL = "glm-4-flash"
# DEFAULT_REASONING_EFFORT = ""  # 智谱不支持 reasoning_effort
# API_KEY_ENV = "ZHIPU_API_KEY"


# =====================================================
# 本地密钥加载（从 .env.local 读）
# =====================================================


def load_local_env(path: str = ".env.local") -> None:
    """从同目录下的 .env.local 读取 KEY=VALUE 并注入 os.environ。

    约定：
    - 以 # 开头的行是注释
    - 空行跳过
    - 已在 os.environ 里的 KEY 不会被覆盖（显式设置的终端环境变量优先级更高）
    - 只用 Python 标准库，不引入 python-dotenv
    """
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


# =====================================================
# 智谱 JWT 签名（旧路径备用，OpenAI 兼容代理不需要）
# =====================================================


def build_zhipu_jwt(api_key: str, exp_seconds: int = 3600) -> str:
    """把智谱复合 API Key 编码为 JWT，用作 Bearer token。

    智谱的 API Key 形如 ``<api_key_id>.<signing_key>``（用 '.' 分隔）。
    官方规范是把它拆开、构造 JWT、用 signing_key 做 HS256 签名。
    参考：https://bigmodel.cn/dev/api/http-auth#jwt-auth

    v0.6.3 起默认走 OpenAI 兼容代理（直接用 raw API key 做 Bearer），
    这个函数保留供旧 Zhipu 路径或 embeddings 调用复用。
    """
    try:
        api_key_id, signing_key = api_key.split(".", 1)
    except ValueError:
        raise ValueError("智谱 API Key 格式应为 '<api_key_id>.<signing_key>'，请检查 .env.local")

    header = {"alg": "HS256", "sign_type": "SIGN"}
    now_ms = int(round(time.time() * 1000))
    payload = {
        "api_key": api_key_id,
        "exp": now_ms + exp_seconds * 1000,
        "timestamp": now_ms,
    }

    def _b64(obj: dict) -> str:
        raw = json.dumps(obj, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

    header_b64 = _b64(header)
    payload_b64 = _b64(payload)
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = hmac.new(
        signing_key.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")

    return f"{header_b64}.{payload_b64}.{signature_b64}"


# =====================================================
# 资源解析器 —— 供其他脚本复用
# =====================================================


def get_llm_config() -> dict:
    """读取当前激活的 LLM 配置（env 优先）。

    所有 chat-completion 调用都应该走这里，避免每个脚本各自硬编码。
    """
    load_local_env()
    return {
        "api_base": _resolved("OPENAI_BASE_URL", DEFAULT_API_BASE),
        "model": _resolved("LLM_MODEL", DEFAULT_MODEL),
        "reasoning_effort": _resolved("LLM_REASONING_EFFORT", DEFAULT_REASONING_EFFORT),
        "timeout": float(_resolved("LLM_TIMEOUT", str(DEFAULT_TIMEOUT))),
        "api_key": os.environ.get(API_KEY_ENV, ""),
        "api_key_env": API_KEY_ENV,
        # Legacy compat for the 智谱 / glm flow
        "is_zhipu": "bigmodel" in _resolved("OPENAI_BASE_URL", DEFAULT_API_BASE).lower(),
    }


# Backwards-compat: existing imports `from day1_api_starter import API_BASE, MODEL`
# still work. They snap to current env at import time.
API_BASE = _resolved("OPENAI_BASE_URL", DEFAULT_API_BASE)
MODEL = _resolved("LLM_MODEL", DEFAULT_MODEL)


# =====================================================
# 最小请求函数
# =====================================================


def call_llm(prompt: str, api_key: str, *, system: str | None = None) -> dict:
    """发送一次 chat completion 请求，返回解析后的 JSON dict。

    使用当前 :func:`get_llm_config` 的配置（OpenAI 兼容代理 + gpt-5.4 +
    reasoning_effort medium 是默认）。

    参数：
        prompt  —— 用户输入的提问文本
        api_key —— Bearer token 用的 API 密钥（OpenAI 路径用 raw；
                   Zhipu 路径会自动 JWT 化）
        system  —— 可选 system 消息；默认是一个简洁助手 prompt

    返回：
        整个 JSON 响应对象（含 choices / usage / id 等）

    可能抛出：
        requests.HTTPError —— HTTP 非 2xx
        json.JSONDecodeError —— 响应不是合法 JSON
    """
    cfg = get_llm_config()
    if cfg["is_zhipu"]:
        bearer_token = build_zhipu_jwt(api_key)
    else:
        bearer_token = api_key

    url = f"{cfg['api_base']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
    }
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    else:
        messages.append({"role": "system", "content": "你是一个严谨的技术助手，回答直接、不废话。"})
    messages.append({"role": "user", "content": prompt})

    payload: dict = {
        "model": cfg["model"],
        "messages": messages,
    }
    # Reasoning effort —— gpt-5.x 系列特性；OpenAI 兼容代理支持。
    # 智谱 / 普通 chat model 不认这个字段就忽略（多数代理会优雅丢弃）。
    if cfg["reasoning_effort"]:
        payload["reasoning_effort"] = cfg["reasoning_effort"]

    response = requests.post(url, headers=headers, json=payload, timeout=cfg["timeout"])
    response.raise_for_status()
    return response.json()


def extract_reply(data: dict) -> str:
    """从响应 JSON 里提取 LLM 的文本回复。"""
    return data["choices"][0]["message"]["content"]


# =====================================================
# 主入口
# =====================================================


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    load_local_env()
    cfg = get_llm_config()

    api_key = cfg["api_key"]
    if not api_key:
        print(f"[ERROR] 未检测到环境变量 {cfg['api_key_env']}")
        print()
        print("有两种设置方式：")
        print(f"  A. 在 .env.local 文件里加一行：{cfg['api_key_env']}=你的密钥")
        print(f"  B. 在当前终端临时设置：")
        print(f"     PowerShell: $env:{cfg['api_key_env']} = '你的密钥'")
        print(f"     CMD:        set {cfg['api_key_env']}=你的密钥")
        sys.exit(1)

    prompt = "我想去洗车，但洗车行离我很近，那我是走过去还是开车过去？"

    print(f"[INFO] Provider         : {cfg['api_base']}")
    print(f"[INFO] Model            : {cfg['model']}")
    if cfg["reasoning_effort"]:
        print(f"[INFO] Reasoning effort : {cfg['reasoning_effort']}")
    print(f"[INFO] Prompt           : {prompt}")
    print("[INFO] 正在发送请求...")
    print()

    try:
        data = call_llm(prompt, api_key)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        reply = extract_reply(data)

        print("[RESPONSE] >>>")
        print(reply)
        print("<<< [END]")

        usage = data.get("usage", {})
        print()
        print(f"[USAGE] tokens = {usage}")

    except requests.HTTPError as e:
        print(f"[HTTP ERROR] {e}")
        print(f"响应体：{e.response.text if e.response is not None else 'N/A'}")
        print()
        print("常见原因：")
        print(f"  - API Key 错误（检查 {cfg['api_key_env']}）")
        print(f"  - 模型名称代理不支持（当前 model={cfg['model']}；试试 gpt-5.4-mini）")
        print(f"  - 代理 endpoint 不通（当前 base={cfg['api_base']}）")
        sys.exit(1)

    except requests.Timeout:
        print(f"[TIMEOUT] 请求超过 {cfg['timeout']} 秒未响应，检查网络连接")
        sys.exit(1)

    except KeyError as e:
        print(f"[PARSE ERROR] 响应结构不符合预期：缺字段 {e}")
        print(f"原始响应：{json.dumps(data, ensure_ascii=False, indent=2)}")
        sys.exit(1)

    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
