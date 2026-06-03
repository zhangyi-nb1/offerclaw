# -*- coding: utf-8 -*-
"""
OfferClaw · RAG 工具模块

提供：
1. 智谱 JWT Bearer Token 签名（纯标准库，无 PyJWT，作为 legacy fallback）
2. 可配置 Embedding API 调用（智谱 / 百炼 / OpenAI 兼容）
3. Markdown 文档分块（LangChain + 自定义过滤）
4. ChromaDB 入库 / 检索封装

设计原则：
- 复用项目 1 的手写 JWT 风格，不引入 PyJWT
- embedding provider 由 .env.local 配置，切换 provider 时使用独立 Chroma collection
- 批量调用减少 HTTP 请求次数
- 错误重试 + 指数退避
- 分块按 Markdown 标题天然切分，过滤无效块
"""

import hashlib
import hmac
import base64
import time
import json
import os
import requests


# =====================================================
# 密钥加载（复用 agent_demo.py 同款逻辑）
# =====================================================

def _load_local_env(path: str = ".env.local") -> None:
    """从同目录 .env.local 读取 KEY=VALUE 并注入 os.environ（已有的不覆盖）。"""
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value

_load_local_env()


def _env(name: str, default: str = "") -> str:
    """Read a non-empty environment value with a default fallback."""
    value = os.environ.get(name, "").strip()
    return value if value else default


def _normalise_provider(provider: str) -> str:
    p = (provider or "zhipu").strip().lower().replace("-", "_")
    aliases = {
        "dashscope": "bailian",
        "aliyun": "bailian",
        "ali": "bailian",
        "zhipuai": "zhipu",
        "bigmodel": "zhipu",
        "openai": "openai_compatible",
        "openai_compat": "openai_compatible",
    }
    return aliases.get(p, p)


EMBEDDING_PROVIDER = _normalise_provider(_env("EMBEDDING_PROVIDER", "zhipu"))


def _default_embedding_model(provider: str) -> str:
    if provider == "bailian":
        return "text-embedding-v4"
    if provider == "openai_compatible":
        return "text-embedding-3-small"
    return "embedding-3"


def _default_embedding_base_url(provider: str) -> str:
    if provider == "bailian":
        return "https://dashscope.aliyuncs.com/compatible-mode/v1"
    if provider == "openai_compatible":
        return "https://api.openai.com/v1"
    return "https://open.bigmodel.cn/api/paas/v4"


def _default_embedding_dimensions(provider: str, model: str) -> int | None:
    if provider == "bailian":
        return 1024
    if provider == "zhipu" and model == "embedding-3":
        return 2048
    return None


def _default_embedding_batch_size(provider: str) -> int:
    # 百炼 text-embedding 系列单次批量上限随模型变化，10 是稳妥默认值。
    return 10 if provider == "bailian" else 50


def _optional_int(name: str, default: int | None = None) -> int | None:
    value = _env(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} 应为整数，当前值: {value!r}") from exc


def _slug(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")


def get_embedding_config() -> dict:
    """Return the active embedding provider config from environment variables."""
    provider = _normalise_provider(_env("EMBEDDING_PROVIDER", EMBEDDING_PROVIDER))
    model = _env("EMBEDDING_MODEL", _default_embedding_model(provider))
    base_url = _env("EMBEDDING_BASE_URL", _default_embedding_base_url(provider)).rstrip("/")
    dimensions = _optional_int(
        "EMBEDDING_DIMENSIONS",
        _default_embedding_dimensions(provider, model),
    )
    batch_size = _optional_int(
        "EMBEDDING_BATCH_SIZE",
        _default_embedding_batch_size(provider),
    )
    return {
        "provider": provider,
        "model": model,
        "base_url": base_url,
        "endpoint": f"{base_url}/embeddings",
        "dimensions": dimensions,
        "batch_size": batch_size or _default_embedding_batch_size(provider),
    }


def get_collection_name() -> str:
    """Return the Chroma collection name for the active embedding provider.

    The legacy Zhipu embedding-3 collection stays as offerclaw_docs for
    backwards compatibility. Other providers get isolated collections so
    vectors from different embedding spaces are never mixed.
    """
    configured = _env("RAG_COLLECTION_NAME")
    if configured:
        return configured

    cfg = get_embedding_config()
    if cfg["provider"] == "zhipu" and cfg["model"] == "embedding-3":
        return "offerclaw_docs"

    dim = f"_{cfg['dimensions']}" if cfg.get("dimensions") else ""
    return f"offerclaw_{_slug(cfg['provider'])}_{_slug(cfg['model'])}{dim}"


def _get_provider_api_key(provider: str) -> str:
    generic = _env("EMBEDDING_API_KEY")
    if generic:
        return generic
    if provider == "bailian":
        return _env("DASHSCOPE_API_KEY") or _env("BAILIAN_API_KEY")
    if provider == "openai_compatible":
        return _env("OPENAI_API_KEY")
    return _env("ZHIPU_API_KEY")


def has_embedding_api_key() -> bool:
    cfg = get_embedding_config()
    return bool(_get_provider_api_key(cfg["provider"]))


def describe_embedding_config() -> str:
    cfg = get_embedding_config()
    dim = f", dim={cfg['dimensions']}" if cfg.get("dimensions") else ""
    key_state = "key=已配置" if has_embedding_api_key() else "key=未配置"
    return f"{cfg['provider']}/{cfg['model']}{dim}, {key_state}, collection={get_collection_name()}"


def _get_embedding_api_key(provider: str) -> str:
    key = _get_provider_api_key(provider)
    if key:
        return key
    if provider == "bailian":
        hint = "DASHSCOPE_API_KEY=你的百炼API Key"
    elif provider == "openai_compatible":
        hint = "OPENAI_API_KEY=你的 API Key"
    else:
        hint = "ZHIPU_API_KEY=你的key_id.你的signing_secret"
    raise RuntimeError(f"未找到 embedding API Key。请在 .env.local 里加一行：\n  {hint}")


def _get_api_key() -> str:
    """读取智谱 API Key（格式：<key_id>.<signing_secret>）。"""
    return _get_embedding_api_key("zhipu")


# 模型配置
_EMBEDDING_CFG = get_embedding_config()
EMBEDDING_MODEL = _EMBEDDING_CFG["model"]
LLM_MODEL = "glm-4-flash"                  # 问答用
EMBEDDING_ENDPOINT = _EMBEDDING_CFG["endpoint"]
CHAT_ENDPOINT = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

# 分块配置
CHUNK_SIZE = 800
CHUNK_OVERLAP = 80
MIN_CHUNK_CHARS = 50  # 小于此字符数的块将被过滤

# =====================================================
# 1. JWT Bearer Token 签名（纯标准库实现，无 PyJWT 依赖）
# =====================================================

def _base64url_encode(data: bytes) -> str:
    """URL-safe Base64 编码，去掉尾部 ="""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def generate_zhipu_token(exp_seconds: int = 3600) -> str:
    """
    生成智谱 API 的 JWT Bearer Token。
    纯标准库实现，无 PyJWT 依赖。与 agent_demo.py 行为完全一致：
      - 从 ZHIPU_API_KEY 环境变量读取，格式 "<key_id>.<signing_secret>"
      - exp / timestamp 用毫秒（智谱要求）
    """
    raw_key = _get_api_key()
    try:
        api_key_id, signing_secret = raw_key.split(".", 1)
    except ValueError:
        raise ValueError("ZHIPU_API_KEY 格式应为 '<key_id>.<signing_secret>'，请检查 .env.local")

    header = {"alg": "HS256", "sign_type": "SIGN"}
    now_ms = int(round(time.time() * 1000))           # 毫秒，与智谱要求一致
    payload = {
        "api_key": api_key_id,
        "exp": now_ms + exp_seconds * 1000,
        "timestamp": now_ms,
    }

    header_b64 = _base64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode())

    signing_input = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        signing_secret.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    signature_b64 = _base64url_encode(signature)

    return f"{signing_input}.{signature_b64}"


# =====================================================
# 2. Embedding API 调用
# =====================================================

def get_embedding(
    text: str,
    model: str | None = None,
    max_retries: int = 3,
) -> list[float]:
    """
    获取单段文本的 embedding 向量。
    失败自动重试，指数退避。
    """
    return get_embeddings_batch([text], model=model, max_retries=max_retries)[0]


def get_embeddings_batch(
    texts: list[str],
    model: str | None = None,
    batch_size: int | None = None,
    max_retries: int = 6,
    throttle: float = 0.5,
) -> list[list[float]]:
    """
    批量获取 embedding 向量。
    Embedding API 支持 input 数组，一次调用可处理多条文本。
    如果文本量超过 batch_size，自动分批。

    限流处理：
    - 每个成功批次之间 sleep ``throttle`` 秒，平滑请求速率
    - 429（Too Many Requests）使用更长的指数退避（10s, 20s, 40s...）
    - 其它网络错误使用较短退避（2s, 4s, 8s...）
    """
    cfg = get_embedding_config()
    provider = cfg["provider"]
    batch_size = batch_size or int(cfg["batch_size"])
    model = model or cfg["model"]
    endpoint = cfg["endpoint"]
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]

        for attempt in range(max_retries):
            try:
                if provider == "zhipu":
                    token = generate_zhipu_token()  # 每次重试都重签，避免 token 过期
                else:
                    token = _get_embedding_api_key(provider)

                payload: dict = {
                    "model": model,
                    "input": batch,
                    "encoding_format": "float",
                }
                if provider == "bailian" and cfg.get("dimensions"):
                    payload["dimensions"] = cfg["dimensions"]

                resp = requests.post(
                    endpoint,
                    headers={"Authorization": f"Bearer {token}"},
                    json=payload,
                    timeout=60,
                )
                resp.raise_for_status()
                data = resp.json()
                batch_embeddings = [d["embedding"] for d in data["data"]]
                all_embeddings.extend(batch_embeddings)
                break
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise
                # 429 限流：更长退避；其它错误：标准退避
                is_rate_limit = (
                    getattr(e, "response", None) is not None
                    and e.response.status_code == 429
                )
                if is_rate_limit:
                    wait = 10 * (2 ** attempt)
                    print(f"  [WARN] 触发限流 429 (attempt {attempt+1}/{max_retries})")
                else:
                    wait = (2 ** attempt) * 2
                    print(f"  [WARN] 批量 Embedding 请求失败 (attempt {attempt+1}/{max_retries}): {e}")
                print(f"  [INFO] {wait}s 后重试...")
                time.sleep(wait)

        # 批次间节流，平滑速率，避免连续 burst 触发 429
        if throttle:
            time.sleep(throttle)

    return all_embeddings


def fake_embedding(text: str, dim: int | None = None) -> list[float]:
    """Deterministic fake vector for offline ingest/query smoke tests."""
    import struct

    dim = dim or get_embedding_config().get("dimensions") or 384
    h = hashlib.sha256(text.encode("utf-8")).digest()
    extended = b""
    while len(extended) < dim * 4:
        h = hashlib.sha256(h).digest()
        extended += h
    floats = struct.unpack(f"{dim}f", extended[: dim * 4])
    mn, mx = min(floats), max(floats)
    if mx == mn:
        return [0.5] * dim
    return [(v - mn) / (mx - mn) for v in floats]


# =====================================================
# 3. Markdown 文档分块
# =====================================================

def split_markdown_document(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    min_chars: int = MIN_CHUNK_CHARS,
) -> list[dict]:
    """
    按 Markdown 二级标题（##）智能切分文档。
    返回 list[dict]，每个 dict 包含：
    - "text": 块内容
    - "metadata": {"char_len": int, "title": str}
    """
    chunks = []

    # 按 ## 二级标题分段
    lines = text.split("\n")
    sections: list[tuple[str, list[str]]] = []
    current_title = "__header__"  # 标记文件开头无标题部分
    current_lines: list[str] = []

    for line in lines:
        if line.startswith("## ") and not line.startswith("### "):
            # 保存上一段
            if current_lines:
                sections.append((current_title, current_lines))
            current_title = line.strip().lstrip("#").strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_title, current_lines))

    # 对每个 section 切块
    import re as _re
    for title, section_lines in sections:
        # 跳过纯图片素材段落（标题含"图片素材"）
        if "图片素材" in title:
            continue

        # 过滤图片 markdown 行：直接丢弃，不保留占位
        cleaned_lines = [
            ln for ln in section_lines
            if not ln.strip().startswith("![")
            and not _re.match(r"^\[图[:：]", ln.strip())
        ]
        section_text = "\n".join(cleaned_lines).strip()

        if title == "__header__":
            title = ""  # 清除标记

        if not section_text or len(section_text) < min_chars:
            continue

        if len(section_text) <= chunk_size:
            chunks.append({
                "text": section_text,
                "metadata": {"char_len": len(section_text), "title": title}
            })
        else:
            paragraphs = section_text.split("\n\n")
            buf: list[str] = []
            buf_len = 0
            for para in paragraphs:
                add_len = len(para) + (2 if buf else 0)
                if buf_len + add_len > chunk_size and buf:
                    chunk_text = "\n\n".join(buf).strip()
                    if len(chunk_text) >= min_chars:
                        chunks.append({
                            "text": chunk_text,
                            "metadata": {"char_len": len(chunk_text), "title": title}
                        })
                    buf = [para]
                    buf_len = len(para)
                else:
                    buf.append(para)
                    buf_len += add_len
            if buf:
                chunk_text = "\n\n".join(buf).strip()
                if len(chunk_text) >= min_chars:
                    chunks.append({
                        "text": chunk_text,
                        "metadata": {"char_len": len(chunk_text), "title": title}
                    })

    return chunks


# =====================================================
# 4. LLM 问答（问答阶段使用）
# =====================================================

def chat_with_llm(
    messages: list[dict],
    model: str = LLM_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> str:
    """
    调用当前配置的 OpenAI 兼容 LLM 进行对话。
    messages 格式：[{"role": "system"|"user"|"assistant", "content": "..."}]
    """
    from day1_api_starter import build_zhipu_jwt, get_llm_config

    cfg = get_llm_config()
    token = build_zhipu_jwt(cfg["api_key"]) if cfg["is_zhipu"] else cfg["api_key"]

    resp = requests.post(
        f"{cfg['api_base']}/chat/completions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "model": model if model != LLM_MODEL else cfg["model"],
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]
