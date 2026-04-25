# OfferClaw · 演示流程 (Demo Walkthrough)

> 用一条命令链跑通"匹配 → 计划 → 复盘 → 流式问答"全链路。
> 适合录屏 / 现场演示。

## 0. 环境准备（一次性）

```bash
git clone https://github.com/zhangyi-nb1/offerclaw.git
cd offerclaw
pip install -r requirements.txt
echo "ZHIPU_API_KEY=<your_key_id>.<your_signing_secret>" > .env.local
python rag_ingest.py        # 把 7+ md 文件灌入 ChromaDB
```

预期输出：`[OK] ingested 50 chunks into chroma_db/offerclaw_docs`

## 1. 单命令端到端闭环（pipeline）

```bash
python pipeline.py
```

流程：
1. **匹配** DEMO_JD → 输出三档结论 + 缺口清单
2. **规划** LLM 基于缺口生成 4 周计划，落 `plans/plan_<ts>.md`
3. **留痕** 自动追加 `daily_log.md`

预期最后一行：`流水线完成。`

## 2. 学习留痕复盘

```bash
python summary_tool.py --weekly      # 周度
python summary_tool.py --date 2026-04-25  # 单日
```

输出：`summaries/summary_*.md`，按 summary_prompt.md 9 步走。

## 3. RAG 评估（蔚来 JD 命中点）

```bash
python eval_rag.py --k 5 --verbose
```

预期：
```
Recall@5 = 0.750  (6/8)
MRR        = 0.688
```

## 4. LangGraph 状态机（单次问答）

```bash
python rag_graph.py "求职方向的主方向有哪些？"
```

预期看到：`[GRAPH] 开始执行工作流...` → `[BOT] OfferClaw: ...`

## 5. FastAPI + SSE 流式

终端 1：
```bash
python -m uvicorn rag_api:app --host 127.0.0.1 --port 8000
```

终端 2：
```bash
curl http://127.0.0.1:8000/health
curl -N -X POST http://127.0.0.1:8000/api/stream \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"OfferClaw 主方向是什么\", \"top_k\": 3}"
```

预期：先收到一行 `event: meta`，然后逐 token `data: {"delta":"Offer"}`...

浏览器：`http://127.0.0.1:8000/docs` 看 Swagger，6 个接口可点击试。

## 6. 测试套件

```bash
python -m pytest tests/ -v
```

预期：`17 passed, 1 skipped`（含 12 个多 persona 参数化用例）。

## 7. 截图位（录屏时打）

| # | 截图标题 | 命令 |
|---|---------|------|
| 1 | 知识库灌库 | `python rag_ingest.py` |
| 2 | 三档匹配结论 | `python pipeline.py --no-plan` |
| 3 | 4 周计划落地 | `ls plans/` |
| 4 | RAG 命中率 | `python eval_rag.py` |
| 5 | LangGraph 单问 | `python rag_graph.py "..."` |
| 6 | Swagger UI | 浏览器 /docs |
| 7 | SSE 流式输出 | curl -N /api/stream |
| 8 | pytest 全绿 | `pytest tests/ -v` |
