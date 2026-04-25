# OfferClaw · 演示流程 (Demo Walkthrough)

> 用一条命令链跑通"匹配 → 计划 → 复盘 → 流式问答"全链路。
> 适合录屏 / 现场演示。

## 0. 环境准备（一次性）

```bash
git clone https://github.com/zhangyi-nb1/offerclaw.git
cd offerclaw
pip install -r requirements.txt
echo "ZHIPU_API_KEY=<your_key_id>.<your_signing_secret>" > .env.local
python rag_ingest.py        # 把 12 个 md 文件灌入 ChromaDB
```

预期输出：`[OK] ingested 118 chunks into chroma_db/offerclaw_docs`

## 0.5 一键体检（演示前必跑）

```bash
python doctor.py            # 7 类健康检查（API Key / 关键文件 / Chroma / 评估集 / 端口 / Python / Git）
python verify_pipeline.py   # 6 步主链路冒烟（profile → match → plan → summary → rag → /health）
```

预期：`doctor.py` → `8 OK / 1 WARN / 0 ERR`；`verify_pipeline.py` → `6/6 通过`。任何一项红立即停演。

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
python eval_rag.py --k 5
python eval_rag.py --k 5 --baseline tests/rag_eval_baseline.json    # 与基线回归对比
```

预期（自建 50 题 3 桶集）：
```
Recall@5 = 0.960  (48/50)
MRR        = 0.740
桶级：cross_doc 1.000 · explain 0.944 · fact 0.941
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

浏览器入口：
- `http://127.0.0.1:8000/`     → 自动 302 到 `/ui`（友好 Web 控制台）
- `http://127.0.0.1:8000/docs` → Swagger UI（11 个接口可点击试）

## 6. 测试套件

```bash
python -m pytest tests/ -v
```

预期：`37 passed, 3 skipped`（含 12 个 multi-persona × multi-JD 参数化 + FastAPI TestClient 接口测 + 6 步主链路冒烟；3 e2e 默认跳过，需 `OFFERCLAW_E2E=1` 才跑真智谱 API）。

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
