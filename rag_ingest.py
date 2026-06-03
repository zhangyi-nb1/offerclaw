# -*- coding: utf-8 -*-
"""
OfferClaw · RAG Ingest 脚本

功能：
1. 读取指定 .md 文件
2. 按标题智能分块
3. 批量调用当前配置的 Embedding API 生成向量
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
    describe_embedding_config,
    fake_embedding,
    get_collection_name,
    get_embeddings_batch,
    has_embedding_api_key,
    split_markdown_document,
)

# =====================================================
# 配置
# =====================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "chroma_db")
COLLECTION_NAME = get_collection_name()

# 默认 ingest 的文件列表（按优先级排序，每条带 source_type 标签）
DEFAULT_FILES = [
    ("user_profile.md", "profile"),
    ("daily_log.md", "log"),
    ("SOUL.md", "system"),
    ("target_rules.md", "system"),
    ("source_policy.md", "system"),
    ("onboarding_prompt.md", "system"),
    ("job_match_prompt.md", "system"),
    ("plan_prompt.md", "system"),
    ("summary_prompt.md", "system"),
    ("DATA_CONTRACT.md", "doc"),
    ("applications.md", "application"),
    ("interview_story_bank.md", "story"),
    ("jd_candidates.md", "jd"),
    ("docs/resume_pitch.md", "resume"),
    ("docs/project_one_pager.md", "doc"),
    ("docs/verification_report.md", "verification"),
]


_KB_SUBDIR_TYPE = {
    "career_paths": "career_knowledge",
    "experience_posts": "experience",
    "learning_resources": "resource",
    "project_context": "project_context",   # 已有项目先验（localflow 等），只读上下文
}


def _infer_source_type(path: str) -> str:
    """按文件所在 knowledge_base 子目录推断 source_type；推断不出按 doc。"""
    norm = path.replace("\\", "/")
    for subdir, st in _KB_SUBDIR_TYPE.items():
        if f"knowledge_base/{subdir}/" in norm:
            return st
    return "doc"


def _discover_knowledge_base() -> list[tuple[str, str]]:
    """Scan knowledge_base/ for .md files (excluding templates and README)."""
    kb_dir = os.path.join(BASE_DIR, "knowledge_base")
    if not os.path.isdir(kb_dir):
        return []
    type_map = dict(_KB_SUBDIR_TYPE)
    found = []
    for subdir, source_type in type_map.items():
        dirpath = os.path.join(kb_dir, subdir)
        if not os.path.isdir(dirpath):
            continue
        for fname in sorted(os.listdir(dirpath)):
            if fname.endswith(".md") and not fname.startswith("_"):
                relpath = os.path.join("knowledge_base", subdir, fname)
                found.append((relpath, source_type))
    return found


def build_collection_name(file_path: str) -> str:
    """从文件路径生成 collection 中的 source 标记"""
    return os.path.basename(file_path)


def ingest_file(
    file_path: str,
    collection,
    source_type: str = "doc",
    seen_hashes: set | None = None,
) -> dict:
    """
    读取单个 .md 文件，分块 → 向量化 → 入库。
    返回统计信息。

    ``seen_hashes``：跨文件共享的内容哈希集合。若某 chunk 的归一化文本
    已在集合中出现，则视为重复并跳过（避免飞书多章节复用同一节导致
    向量库存重复块、检索结果占满 top-k）。
    """
    import hashlib

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

    # Step 1.5: 图转文（IMAGE_CAPTION=1 时）—— ![](img) → [图: 描述+OCR]，让图片可检索
    try:
        from image_caption import caption_enabled, caption_markdown
        if caption_enabled() and "![" in raw_text:
            st = {}
            raw_text = caption_markdown(raw_text, md_path=full_path, stats=st)
            if st.get("captioned") or st.get("cached"):
                print(f"  [图转文] 新描述 {st.get('captioned',0)} · 缓存命中 "
                      f"{st.get('cached',0)} · 丢弃 {st.get('dropped',0)}")
    except Exception as _e:
        print(f"  [图转文] 跳过（{_e}）")

    # Step 2: 分块
    chunks = split_markdown_document(raw_text)
    print(f"  [SPLIT] {len(chunks)} 块")

    # Step 2.5: 跨文件内容去重
    # 飞书多章节常复用同一节（含轻微改写），故用「归一化前缀哈希」判重：
    # 取去空白后前 100 字符做 key，能同时抓住完全重复与章节变体近重复。
    if seen_hashes is not None:
        deduped = []
        dup_count = 0
        for c in chunks:
            norm = "".join(c["text"].split())  # 去掉所有空白
            key = hashlib.md5(norm[:100].encode("utf-8")).hexdigest()
            if key in seen_hashes:
                dup_count += 1
                continue
            seen_hashes.add(key)
            deduped.append(c)
        if dup_count:
            print(f"  [DEDUP] 跳过 {dup_count} 个与已入库内容重复/近重复的块")
        chunks = deduped

    if not chunks:
        print(f"  [WARN] 无有效块，跳过")
        return {"file": filename, "status": "empty", "chunks": 0, "tokens": 0}

    # 打印分块摘要
    for i, chunk in enumerate(chunks):
        title = chunk["metadata"].get("title", "N/A")
        print(f"    Block {i+1:02d}: {chunk['metadata']['char_len']:4d} 字 | "
              f"[{title}] | {chunk['text'][:50].replace(chr(10), ' ')}...")

    # Step 3: 计算稳定 ID（内容哈希）→ 跳过已入库的块（可断点续传）
    stem = filename[:-3]
    all_ids = [
        f"{stem}_{hashlib.md5(c['text'].encode('utf-8')).hexdigest()[:12]}"
        for c in chunks
    ]
    existing = collection.get(ids=all_ids)
    existing_ids = set(existing["ids"]) if existing and existing["ids"] else set()

    todo = [
        (cid, c) for cid, c in zip(all_ids, chunks)
        if cid not in existing_ids
    ]
    if existing_ids:
        print(f"  [SKIP] {len(existing_ids)} 个块已入库，跳过 embedding")
    if not todo:
        print(f"  [OK] 全部 {len(chunks)} 块已是最新，无需重新 embedding")
        return {
            "file": filename, "status": "ok",
            "chunks": len(chunks), "tokens": sum(len(c["text"]) for c in chunks),
            "embed_time": 0.0,
        }

    todo_ids = [t[0] for t in todo]
    texts = [t[1]["text"] for t in todo]
    print(f"\n  [EMBEDDING] 调用 Embedding API（{len(texts)} 条待入库，批量）...")
    t0 = time.time()

    if not has_embedding_api_key():
        print(f"  [WARN] API Key 未配置，使用 SHA256 伪向量作为占位")
        # 用伪向量占位，验证入库流程
        embeddings = [fake_embedding(t) for t in texts]
    else:
        embeddings = get_embeddings_batch(texts)

    embed_time = time.time() - t0
    print(f"  [EMBEDDING] 完成，耗时 {embed_time:.1f}s")

    # Step 4: 入库（仅新块）
    ids = todo_ids
    metadatas = []
    for _cid, chunk in todo:
        metadatas.append({
            "source": filename,
            "source_type": source_type,
            "char_len": chunk["metadata"]["char_len"],
            "title": chunk["metadata"].get("title", ""),
        })

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )

    new_tokens = sum(len(t) for t in texts)
    print(f"  [DB] 新入库 {len(ids)} 条（本文件共 {len(chunks)} 块），新增字符 {new_tokens}")

    return {
        "file": filename,
        "status": "ok",
        "chunks": len(chunks),
        "tokens": sum(len(c["text"]) for c in chunks),
        "embed_time": round(embed_time, 2),
    }


def main():
    parser = argparse.ArgumentParser(description="OfferClaw RAG Ingest")
    parser.add_argument("--files", nargs="+", help="指定要 ingest 的文件名")
    parser.add_argument("--rebuild", action="store_true", help="清空旧库重建")
    parser.add_argument("--add", help="增量添加单个文件到现有库（不重建、不影响原有内容）")
    parser.add_argument("--source-type", help="配合 --add 指定 source_type（默认按子目录推断）")
    parser.add_argument(
        "--collection",
        default=COLLECTION_NAME,
        help="Chroma collection 名称（默认按 embedding provider/model 自动选择）",
    )
    args = parser.parse_args()
    collection_name = args.collection

    if args.add:
        # 增量模式：只把这一个文件加入现有 collection，不删除/不重建任何已有内容
        st = args.source_type or _infer_source_type(args.add)
        files = [(args.add, st)]
        print(f"[增量] 仅添加 1 个文件：{args.add}（source_type={st}）")
    elif args.files:
        files = [(f, "doc") for f in args.files]
    else:
        kb_files = _discover_knowledge_base()
        files = DEFAULT_FILES + kb_files
        if kb_files:
            print(f"[知识库] 自动发现 {len(kb_files)} 个 knowledge_base 文件")

    print("=" * 60)
    print("OfferClaw RAG Ingest")
    print(f"数据库目录: {DB_DIR}")
    print(f"Collection: {collection_name}")
    print(f"Embedding: {describe_embedding_config()}")
    print(f"API Key: {'已配置' if has_embedding_api_key() else '⚠️ 未配置（使用伪向量占位）'}")
    print("=" * 60)

    # 初始化 ChromaDB
    client = chromadb.PersistentClient(path=DB_DIR)

    # 处理 collection（--add 增量模式下绝不重建，保护已有内容）
    if args.rebuild and not args.add:
        print("\n[REBUILD] 清空旧 collection...")
        try:
            client.delete_collection(collection_name)
        except Exception:
            pass

    try:
        collection = client.get_collection(collection_name)
        print(f"[DB] 使用已有 collection，当前记录数: {collection.count()}")
    except Exception:
        collection = client.create_collection(name=collection_name)
        print(f"[DB] 新建 collection")

    # 逐个文件 ingest（跨文件共享内容哈希集合，去重）
    stats = []
    seen_hashes: set = set()
    for f, st in files:
        result = ingest_file(f, collection, source_type=st, seen_hashes=seen_hashes)
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
