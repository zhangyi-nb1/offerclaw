# -*- coding: utf-8 -*-
"""
OfferClaw · Day 1 Task 1 · LLM API 调用最小可运行脚本

目的：
    验证 "Python -> HTTP 请求 -> LLM 云端 -> 解析响应" 全链路可跑通。
    这是所有 LLM 应用和 Agent 项目的第一块积木。
    本脚本本身也会作为 Day 2 做 Agent Demo 的代码底座。

使用步骤：
    1. 注册一个国内大模型 API 账号（推荐 DeepSeek，注册后有免费额度）：
       - DeepSeek：https://platform.deepseek.com/
       - 备选 · 智谱 GLM（glm-4-flash 有长期免费额度）：https://open.bigmodel.cn/
       - 备选 · Moonshot Kimi：https://platform.moonshot.cn/

    2. 在平台的 "API Keys" 页面创建一个密钥（格式形如 sk-xxxx）。

    3. 把密钥设置为环境变量，避免硬编码进代码：
       - PowerShell：$env:DEEPSEEK_API_KEY = "sk-你的密钥"
       - CMD：      set DEEPSEEK_API_KEY=sk-你的密钥
       - Git Bash：export DEEPSEEK_API_KEY="sk-你的密钥"

    4. 安装唯一的第三方依赖：
         pip install requests

    5. 运行：
         python day1_api_starter.py

成功标志：
    控制台打印一段完整的 LLM 响应文本 + token usage 统计。
    这意味着 Python -> API 全链路通了，Day 2 可以在此基础上加"工具调用"
    变成最小 Agent Demo。
"""

import os
import sys
import json
import time
import hmac
import hashlib
import base64
import requests


# =====================================================
# Provider 配置 —— 想换 Provider 只改这 3 个常量
# =====================================================

# 默认：智谱 GLM-4-Flash（长期免费额度，OpenAI 兼容接口）
API_BASE = "https://open.bigmodel.cn/api/paas/v4"
API_KEY_ENV = "ZHIPU_API_KEY"
MODEL = "glm-4-flash"

# 备选 · DeepSeek：
# API_BASE = "https://api.deepseek.com/v1"
# API_KEY_ENV = "DEEPSEEK_API_KEY"
# MODEL = "deepseek-chat"
#
# 备选 · Moonshot Kimi：
# API_BASE = "https://api.moonshot.cn/v1"
# API_KEY_ENV = "MOONSHOT_API_KEY"
# MODEL = "moonshot-v1-8k"


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
# 智谱 JWT 签名（仅智谱 provider 需要）
# =====================================================

def build_zhipu_jwt(api_key: str, exp_seconds: int = 3600) -> str:
    """把智谱复合 API Key 编码为 JWT，用作 Bearer token。

    智谱的 API Key 形如 `<api_key_id>.<signing_key>`（用 '.' 分隔）。
    官方规范是把它拆开、构造 JWT、用 signing_key 做 HS256 签名。
    参考：https://bigmodel.cn/dev/api/http-auth#jwt-auth

    本函数不依赖 PyJWT，只用 Python 标准库实现。

    参数：
        api_key      —— 完整的智谱复合密钥
        exp_seconds  —— JWT 过期时间（秒），默认 1 小时

    返回：
        可直接放进 "Authorization: Bearer <...>" 头里的 JWT 字符串
    """
    try:
        api_key_id, signing_key = api_key.split(".", 1)
    except ValueError:
        raise ValueError(
            "智谱 API Key 格式应为 '<api_key_id>.<signing_key>'，请检查 .env.local"
        )

    header = {"alg": "HS256", "sign_type": "SIGN"}
    now_ms = int(round(time.time() * 1000))
    payload = {
        "api_key": api_key_id,
        "exp": now_ms + exp_seconds * 1000,
        "timestamp": now_ms,
    }

    def _b64(obj: dict) -> str:
        """紧凑 JSON 序列化 + URL-safe base64 编码 + 去尾部 '=' 填充。"""
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
# 最小请求函数
# =====================================================

def call_llm(prompt: str, api_key: str) -> dict:
    """发送一次 chat completion 请求，返回解析后的 JSON dict。

    参数：
        prompt   —— 用户输入的提问文本
        api_key  —— 通过环境变量读入的 API 密钥

    返回：
        整个 JSON 响应对象（含 choices / usage / id 等）

    可能抛出：
        requests.HTTPError —— HTTP 状态码非 2xx（通常是密钥错 / 余额不足）
        json.JSONDecodeError —— 响应不是合法 JSON（极少见）
    """
    # 智谱 provider 的 Bearer token 必须是 JWT，不能是 raw key
    # 其他 provider（DeepSeek / Moonshot）直接用 raw key
    if "open.bigmodel.cn" in API_BASE:
        bearer_token = build_zhipu_jwt(api_key)
    else:
        bearer_token = api_key

    url = f"{API_BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "你是一个严谨的技术助手，回答直接、不废话。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.8,  # 0.0-1.0，越高越发散（可选，默认值因 provider 而异）
    }

    # timeout 设 30 秒是为了防止 LLM 长时间挂起阻塞脚本
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()  # 非 2xx 抛 HTTPError
    return response.json()


def extract_reply(data: dict) -> str:
    """从响应 JSON 里提取 LLM 的文本回复。

    OpenAI 兼容接口的标准路径是 choices[0].message.content。
    """
    return data["choices"][0]["message"]["content"]


# =====================================================
# 主入口
# =====================================================

def main():
    # Windows 控制台默认 GBK 编码，LLM 返回含表情/特殊字符时会炸，切 UTF-8
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    # 0. 先尝试从 .env.local 加载本地密钥（如果文件存在）
    load_local_env()

    # 1. 读取 API Key
    api_key = os.environ.get(API_KEY_ENV)
    if not api_key:
        print(f"[ERROR] 未检测到环境变量 {API_KEY_ENV}")
        print()
        print("有两种设置方式：")
        print(f"  A. 在 .env.local 文件里加一行：{API_KEY_ENV}=你的密钥")
        print(f"  B. 在当前终端临时设置：")
        print(f"     PowerShell: $env:{API_KEY_ENV} = '你的密钥'")
        print(f"     CMD:        set {API_KEY_ENV}=你的密钥")
        sys.exit(1)

    # 2. 构造一个简单的测试 prompt
    prompt = "我想去洗车，但洗车行离我很近，那我是走过去还是开车过去？"

    # 3. 打印请求上下文（方便排查）
    print(f"[INFO] Provider : {API_BASE}")
    print(f"[INFO] Model    : {MODEL}")
    print(f"[INFO] Prompt   : {prompt}")
    print("[INFO] 正在发送请求...")
    print()

    # 4. 发送请求 + 异常分类处理
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
        print("  - API Key 错误（检查环境变量是否设置正确）")
        print("  - 账户余额不足 / 未激活")
        print("  - 模型名称不对（检查 MODEL 常量）")
        sys.exit(1)

    except requests.Timeout:
        print("[TIMEOUT] 请求超过 30 秒未响应，检查网络连接")
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
    
