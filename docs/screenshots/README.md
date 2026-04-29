# OfferClaw Screenshots

> 投递前必补的 6 张证据截图。计划与命名规范见 [`../verification_report.md`](../verification_report.md) §7。

| # | 文件名 | 内容 | 截图前置 |
|---|---|---|---|
| 01 | `01_doctor_all_green.png` | 终端 `python doctor.py` 输出 **10 OK · 0 WARN · 0 ERR** | 先注入 `ZHIPU_API_KEY` |
| 02 | `02_verify_pipeline_all_green.png` | `python verify_pipeline.py` **6/6** 通过 | rag_api 已启 8000 |
| 03 | `03_pytest_37_passed.png` | `pytest -v` **37 passed, 3 skipped** | 无 |
| 04 | `04_eval_rag_recall_0.96.png` | `python eval_rag.py` overall 表（Recall=0.960 / MRR=0.673） | 无 |
| 05 | `05_ui_six_cards.png` | 浏览器访问 `http://127.0.0.1:8000/ui` 的 6 卡片 + 顶部 RAG 问答条 + 今日建议横条 | rag_api 启动 + 真画像 |
| 06 | `06_swagger_19_routes.png` | `http://127.0.0.1:8000/docs` 折叠后能看见 **19 业务路由** | rag_api 启动 |

> 截图存为 PNG，分辨率不低于 1280×800，内容字号清晰可读。
