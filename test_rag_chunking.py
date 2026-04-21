#!/usr/bin/env python3
"""
OfferClaw RAG Quickstart — 单文档分块 + 向量化 + 检索测试
目标：验证 ChromaDB + LangChain 分片器能正确处理 user_profile.md
"""

import os
import sys

# ─── Step 1: 读取源文档 ───
PROFILE_PATH = os.path.join(os.path.dirname(__file__), "user_profile.md")

with open(PROFILE_PATH, "r", encoding="utf-8") as f:
    raw_text = f.read()

print(f"[1] 读取 user_profile.md: {len(raw_text)} 字符, {raw_text.count(chr(10))} 行")

# ─── Step 2: 用 LangChain 分块 ───
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    print("[!] langchain-text-splitters 未安装，尝试安装...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "langchain-text-splitters", "-q"])
    from langchain_text_splitters import RecursiveCharacterTextSplitter

# Markdown 友好的分块参数
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,        # 每块最大字符数
    chunk_overlap=50,      # 相邻块重叠字符数（防止边界截断）
    separators=[
        "\n## ",       # 二级标题
        "\n### ",      # 三级标题
        "\n----",      # 分隔线
        "\n\n",        # 空行
        "\n",          # 换行
        "。",           # 中文句号
        "！",           # 中文感叹号
        "？",           # 中文问号
        " ",            # 英文空格
        ""
    ],
    keep_separator=True,
)

chunks = splitter.split_text(raw_text)
print(f"[2] 分块完成: {len(chunks)} 块")

# 打印每块统计
for i, chunk in enumerate(chunks):
    lines = chunk.count("\n") + 1
    print(f"    Block {i+1:02d}: {len(chunk):4d} 字符, {lines:3d} 行 | 前 60 字: {chunk[:60].replace(chr(10), ' ')}...")

# ─── Step 3: ChromaDB 本地入库 ───
import chromadb
from chromadb.config import Settings

DB_DIR = os.path.join(os.path.dirname(__file__), "chroma_db_test")
# 清理旧测试库
if os.path.exists(DB_DIR):
    import shutil
    shutil.rmtree(DB_DIR)

client = chromadb.PersistentClient(path=DB_DIR)

# 删除可能存在的旧 collection
try:
    client.delete_collection("profile_test")
except Exception:
    pass  # collection 不存在时忽略

collection = client.create_collection(name="profile_test")

# ─── Step 4: 用简单哈希模拟 embedding 入库（不依赖 API）───
# 注意：这是 Quickstart 验证阶段，用简单向量代替真实 embedding
# 生产环境会替换为智谱 glm-4-embed 或其他 Embedding API
import hashlib
import struct

def simple_hash_embedding(text: str, dim: int = 384) -> list[float]:
    """
    用 SHA256 哈希生成固定维度伪向量，仅用于验证 ChromaDB 入库/检索流程。
    后续替换为真实 Embedding API 调用。
    """
    h = hashlib.sha256(text.encode("utf-8")).digest()
    # 扩展哈希到目标维度
    extended = b""
    while len(extended) < dim * 4:
        h = hashlib.sha256(h).digest()
        extended += h
    floats = struct.unpack(f"{dim}f", extended[:dim * 4])
    # 归一化到 [0, 1]
    mn, mx = min(floats), max(floats)
    if mx == mn:
        return [0.5] * dim
    return [(v - mn) / (mx - mn) for v in floats]

# 入库
for i, chunk in enumerate(chunks):
    embedding = simple_hash_embedding(chunk)
    collection.add(
        ids=[f"block_{i+1:02d}"],
        embeddings=[embedding],
        documents=[chunk],
        metadatas=[{"block_index": i + 1, "char_len": len(chunk)}],
    )

print(f"\n[3] ChromaDB 入库完成: {collection.count()} 条记录")
print(f"    数据库目录: {DB_DIR}")

# ─── Step 5: 检索测试 ───
test_queries = [
    "求职方向是什么？",
    "Python 技能水平如何？",
    "项目经历有哪些？",
    "可接受哪些城市？",
]

print(f"\n[4] 检索测试:")
for query in test_queries:
    query_embedding = simple_hash_embedding(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=2,  # top-2
    )

    print(f"\n  查询: 「{query}」")
    for j in range(len(results["ids"][0])):
        doc_id = results["ids"][0][j]
        distance = results["distances"][0][j]
        doc_preview = results["documents"][0][j][:100].replace("\n", " ")
        print(f"    [{doc_id}] distance={distance:.4f} | {doc_preview}...")

print(f"\n✅ Quickstart 全部通过！")
print(f"   - LangChain 分块: {len(chunks)} 块")
print(f"   - ChromaDB 入库: {collection.count()} 条")
print(f"   - 检索测试: {len(test_queries)} 组查询均返回结果")
print(f"\n下一步：接入真实 Embedding API（智谱 glm-4-embed）替换简单哈希向量。")
