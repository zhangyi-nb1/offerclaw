# -*- coding: utf-8 -*-
"""
OfferClaw · RAG Ingest 脚本

功能：
1. 读取指定 .md 文件
2. 按标题智能分块
3. 批量调用智谱 Embedding API 生成向量
4. 写入 ChromaDB

用法：
  python rag_ingest.py                          # ingest 默认文件列表
  python rag_ingest.py --files user_profile.md daily_log.md  # 指定文件
  python rag_ingest.py --rebuild                # 清空旧库重建
"""

import os
import sys
import argparse
import time

import chromadb

from rag_tools import (
    get_embeddings_batch,
    split_markdown_document,
)

# =====================================================
# 配置
# =====================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "chroma_db")
COLLECTION_NAME = "offerclaw_docs"

# 默认 ingest 的文件列表（按优先级排序）
DEFAULT_FILES = [
    "user_profile.md",
    "daily_log.md",
    "SOUL.md",
    "target_rules.md",
    "source_policy.md",
]


def build_collection_name(file_path: str) -> str:
    """从文件路径生成 collection 中的 source 标记"""
    return os.path.basename(file_path)


def ingest_file(
    file_path: str,
    collection,
) -> dict:
    """
    读取单个 .md 文件，分块 → 向量化 → 入库。
    返回统计信息。
    """
    filename = os.path.basename(file_path)
    full_path = os.path.join(BASE_DIR, file_path) if not os.path.isabs(file_path) else file_path

    print(f"\n{'='*60}")
    print(f"[INGEST] {filename}")
    print(f"{'='*60}")

    # Step 1: 读取
    if not os.path.exists(full_path):
        print(f"  [SKIP] 文件不存在: {full_path}")
        return {"file": filename, "status": "not_found", "chunks": 0, "tokens": 0}

    with open(full_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    print(f"  [READ] {len(raw_text)} 字符, {raw_text.count(chr(10))} 行")

    # Step 2: 分块
    chunks = split_markdown_document(raw_text)
    print(f"  [SPLIT] {len(chunks)} 块")

    if not chunks:
        print(f"  [WARN] 无有效块，跳过")
        return {"file": filename, "status": "empty", "chunks": 0, "tokens": 0}

    # 打印分块摘要
    for i, chunk in enumerate(chunks):
        title = chunk["metadata"].get("title", "N/A")
        print(f"    Block {i+1:02d}: {chunk['metadata']['char_len']:4d} 字 | "
              f"[{title}] | {chunk['text'][:50].replace(chr(10), ' ')}...")

    # Step 3: 批量 Embedding
    texts = [c["text"] for c in chunks]
    print(f"\n  [EMBEDDING] 调用智谱 API（{len(texts)} 条，批量）...")
    t0 = time.time()

    if not os.environ.get("ZHIPU_API_KEY", ""):
        print(f"  [WARN] API Key 未配置，使用 SHA256 伪向量作为占位")
        # 用伪向量占位，验证入库流程
        def _fake_embed(text: str) -> list[float]:
            import hashlib, struct
            h = hashlib.sha256(text.encode("utf-8")).digest()
            extended = b""
            while len(extended) < 384 * 4:
                h = hashlib.sha256(h).digest()
                extended += h
            floats = struct.unpack("384f", extended[:384 * 4])
            mn, mx = min(floats), max(floats)
            if mx == mn:
                return [0.5] * 384
            return [(v - mn) / (mx - mn) for v in floats]

        embeddings = [_fake_embed(t) for t in texts]
    else:
        embeddings = get_embeddings_batch(texts)

    embed_time = time.time() - t0
    print(f"  [EMBEDDING] 完成，耗时 {embed_time:.1f}s")

    # Step 4: 入库
    ids = [f"{filename[:-3]}_block_{i+1:02d}" for i in range(len(chunks))]
    metadatas = []
    for chunk in chunks:
        metadatas.append({
            "source": filename,
            "char_len": chunk["metadata"]["char_len"],
            "title": chunk["metadata"].get("title", ""),
        })

    # 如果已存在同 ID 的块，先删除
    existing = collection.get(ids=ids)
    if existing and existing["ids"]:
        print(f"  [UPDATE] 删除 {len(existing['ids'])} 条旧记录")
        collection.delete(ids=existing["ids"])

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )

    total_tokens = sum(len(t) for t in texts)
    print(f"  [DB] 入库 {len(chunks)} 条，总字符 {total_tokens}")

    return {
        "file": filename,
        "status": "ok",
        "chunks": len(chunks),
        "tokens": total_tokens,
        "embed_time": round(embed_time, 2),
    }


def main():
    parser = argparse.ArgumentParser(description="OfferClaw RAG Ingest")
    parser.add_argument("--files", nargs="+", help="指定要 ingest 的文件名")
    parser.add_argument("--rebuild", action="store_true", help="清空旧库重建")
    args = parser.parse_args()

    files = args.files if args.files else DEFAULT_FILES

    print("=" * 60)
    print("OfferClaw RAG Ingest")
    print(f"数据库目录: {DB_DIR}")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"API Key: {'已配置' if os.environ.get('ZHIPU_API_KEY', '') else '⚠️ 未配置（使用伪向量占位）'}")
    print("=" * 60)

    # 初始化 ChromaDB
    client = chromadb.PersistentClient(path=DB_DIR)

    # 处理 collection
    if args.rebuild:
        print("\n[REBUILD] 清空旧 collection...")
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass

    try:
        collection = client.get_collection(COLLECTION_NAME)
        print(f"[DB] 使用已有 collection，当前记录数: {collection.count()}")
    except Exception:
        collection = client.create_collection(name=COLLECTION_NAME)
        print(f"[DB] 新建 collection")

    # 逐个文件 ingest
    stats = []
    for f in files:
        result = ingest_file(f, collection)
        stats.append(result)

    # 汇总
    print(f"\n{'='*60}")
    print("Ingest 完成汇总")
    print(f"{'='*60}")
    
    total_chunks = 0
    total_tokens = 0
    ok_files = 0
    
    for s in stats:
        status_icon = "[OK]" if s["status"] == "ok" else ("[MISS]" if s["status"] == "not_found" else "[ERR]")
        print(f"  {status_icon} {s['file']}: {s['chunks']} 块, {s.get('tokens', 0)} 字符")
        if s["status"] == "ok":
            total_chunks += s["chunks"]
            total_tokens += s["tokens"]
            ok_files += 1

    print(f"\n  总计: {ok_files}/{len(files)} 文件成功, {total_chunks} 块, {total_tokens} 字符")
    print(f"  Collection 总记录数: {collection.count()}")
    print(f"\n下一步: python rag_query.py  <你的问题>")


if __name__ == "__main__":
    main()
