# -*- coding: utf-8 -*-
"""
OfferClaw · RAG 工具模块

提供：
1. 智谱 JWT Bearer Token 签名（纯标准库，无 PyJWT）
2. Embedding API 调用（单条 + 批量）
3. Markdown 文档分块（LangChain + 自定义过滤）
4. ChromaDB 入库 / 检索封装

设计原则：
- 复用项目 1 的手写 JWT 风格，不引入 PyJWT
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


def _get_api_key() -> str:
    """读取智谱 API Key（格式：<key_id>.<signing_secret>）。"""
    key = os.environ.get("ZHIPU_API_KEY", "")
    if not key:
        raise RuntimeError(
            "未找到 ZHIPU_API_KEY。\n"
            "请在 .env.local 里加一行：\n"
            "  ZHIPU_API_KEY=你的key_id.你的signing_secret"
        )
    return key


# 模型配置
EMBEDDING_MODEL = "embedding-3"            # 2048 维（智谱 embedding-3 实际输出）
LLM_MODEL = "glm-4-flash"                  # 问答用
EMBEDDING_ENDPOINT = "https://open.bigmodel.cn/api/paas/v4/embeddings"
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
    model: str = EMBEDDING_MODEL,
    max_retries: int = 3,
) -> list[float]:
    """
    获取单段文本的 embedding 向量。
    失败自动重试，指数退避。
    """
    token = generate_zhipu_token()
    
    for attempt in range(max_retries):
        try:
            resp = requests.post(
                EMBEDDING_ENDPOINT,
                headers={"Authorization": f"Bearer {token}"},
                json={"model": model, "input": [text]},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["data"][0]["embedding"]
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise
            wait = (2 ** attempt) * 2  # 2s, 4s, 8s
            print(f"  [WARN] Embedding 请求失败 (attempt {attempt+1}/{max_retries}): {e}")
            print(f"  [INFO] {wait}s 后重试...")
            time.sleep(wait)
    return []  # never reached


def get_embeddings_batch(
    texts: list[str],
    model: str = EMBEDDING_MODEL,
    batch_size: int = 50,
    max_retries: int = 3,
) -> list[list[float]]:
    """
    批量获取 embedding 向量。
    智谱 API 支持 input 数组，一次调用可处理多条文本。
    如果文本量超过 batch_size，自动分批。
    """
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        token = generate_zhipu_token()
        
        for attempt in range(max_retries):
            try:
                resp = requests.post(
                    EMBEDDING_ENDPOINT,
                    headers={"Authorization": f"Bearer {token}"},
                    json={"model": model, "input": batch},
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
                wait = (2 ** attempt) * 2
                print(f"  [WARN] 批量 Embedding 请求失败 (attempt {attempt+1}/{max_retries})")
                print(f"  [INFO] {wait}s 后重试...")
                time.sleep(wait)

    return all_embeddings


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
    for title, section_lines in sections:
        section_text = "\n".join(section_lines).strip()

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
    调用智谱 LLM 进行对话。
    messages 格式：[{"role": "system"|"user"|"assistant", "content": "..."}]
    """
    token = generate_zhipu_token()
    
    resp = requests.post(
        CHAT_ENDPOINT,
        headers={"Authorization": f"Bearer {token}"},
        json={
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]
