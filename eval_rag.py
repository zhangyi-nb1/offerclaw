# -*- coding: utf-8 -*-
"""
OfferClaw · RAG 检索质量评估 (eval_rag.py)

职责：
    用一组"问题 + 期望命中来源"的 ground-truth，跑 ChromaDB 检索，
    输出 Recall@K / MRR 指标。直接对应蔚来 JD 第 3 条
    "研究与实践 RAG 相关评估方法，持续优化系统效果"。

数据集：
    内置一份 8 题的 OfferClaw 自评集（覆盖 SOUL / target_rules /
    user_profile / source_policy / job_match_prompt / plan_prompt /
    summary_prompt / README），每题指定期望命中的源文件名。

指标：
    - Recall@K：top-K 中是否至少命中一个期望源
    - MRR：第一个命中的倒数排名（未命中=0）

使用：
    python eval_rag.py                # 默认 K=5
    python eval_rag.py --k 3
    python eval_rag.py --verbose      # 打印每题命中明细
"""

import argparse
import os
import sys
from typing import List, Dict

import chromadb

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from rag_tools import get_embedding

DB_DIR = os.path.join(BASE, "chroma_db")
COLLECTION_NAME = "offerclaw_docs"


# 内置评估集：每题 → 期望命中源文件（substring 匹配）
EVAL_SET: List[Dict] = [
    {"q": "OfferClaw 的核心使命是什么？",
     "expected_sources": ["SOUL.md"]},
    {"q": "求职方向的主方向有哪些？",
     "expected_sources": ["target_rules.md", "user_profile.md"]},
    {"q": "三档投递结论分别是哪三档？",
     "expected_sources": ["target_rules.md", "job_match_prompt.md"]},
    {"q": "证据等级 A B C 分别代表什么？",
     "expected_sources": ["source_policy.md"]},
    {"q": "岗位匹配的硬门槛包括哪几项？",
     "expected_sources": ["job_match_prompt.md", "target_rules.md"]},
    {"q": "如何生成 4 周路线规划？",
     "expected_sources": ["plan_prompt.md"]},
    {"q": "学习留痕复盘的偏离度怎么判断？",
     "expected_sources": ["summary_prompt.md"]},
    {"q": "用户当前的学历和专业是什么？",
     "expected_sources": ["user_profile.md"]},
]


def evaluate(k: int = 5, verbose: bool = False):
    if not os.path.exists(DB_DIR):
        print(f"[ERROR] {DB_DIR} 不存在，请先运行 python rag_ingest.py")
        sys.exit(1)

    client = chromadb.PersistentClient(path=DB_DIR)
    try:
        collection = client.get_collection(COLLECTION_NAME)
    except Exception as e:
        print(f"[ERROR] 取不到 collection: {e}")
        sys.exit(1)

    print(f"=== OfferClaw RAG 评估 (K={k}, N={len(EVAL_SET)}, DB={collection.count()} 块) ===\n")

    recall_hits = 0
    mrr_sum = 0.0

    for i, item in enumerate(EVAL_SET, 1):
        q = item["q"]
        expected = item["expected_sources"]

        emb = get_embedding(q)
        res = collection.query(query_embeddings=[emb], n_results=k)

        sources = [m.get("source", "") for m in res["metadatas"][0]]

        # Recall@K
        hit = any(any(exp in src for exp in expected) for src in sources)
        if hit:
            recall_hits += 1

        # MRR
        rank = 0
        for j, src in enumerate(sources, 1):
            if any(exp in src for exp in expected):
                rank = j
                break
        if rank > 0:
            mrr_sum += 1.0 / rank

        status = "[HIT]" if hit else "[MISS]"
        print(f"{status} Q{i}: {q}")
        print(f"      期望: {expected}")
        print(f"      Top{k}: {sources}")
        if verbose:
            for j, (s, doc) in enumerate(zip(sources, res["documents"][0]), 1):
                print(f"        #{j} {s} :: {doc[:80].replace(chr(10), ' ')}...")
        print()

    n = len(EVAL_SET)
    recall_at_k = recall_hits / n
    mrr = mrr_sum / n

    print("=" * 60)
    print(f"Recall@{k} = {recall_at_k:.3f}  ({recall_hits}/{n})")
    print(f"MRR        = {mrr:.3f}")
    print("=" * 60)
    return {"recall_at_k": recall_at_k, "mrr": mrr, "k": k, "n": n}


def main():
    parser = argparse.ArgumentParser(description="RAG 检索质量评估")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    evaluate(k=args.k, verbose=args.verbose)


if __name__ == "__main__":
    main()
