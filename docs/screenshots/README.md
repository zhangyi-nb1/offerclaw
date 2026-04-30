# OfferClaw Screenshots

> 投递前必补的 7 张证据截图。计划与命名规范见 [`../verification_report.md`](../verification_report.md) §7。

| # | 文件名 | 内容 | 截图前置 |
|---|---|---|---|
| 01 | `01_doctor_all_green.png` | 终端 `python doctor.py` 输出 **10 OK · 0 WARN · 0 ERR** | 无需手动 set——doctor.py 会自动读 `.env.local`（已 `.gitignore`） |
| 02 | `02_verify_pipeline_all_green.png` | `python verify_pipeline.py` **6/6** 通过 | rag_api 已启 8000 |
| 03 | `03_pytest_37_passed.png` | `pytest -v` **37 passed, 3 skipped**（V3 后实际 58 / 3，截图保留作为 V2 基线证据） | 无 |
| 04 | `04_eval_rag_recall_0.96.png` | `python eval_rag.py` overall 表（Recall=0.960 / MRR=0.673） | 无 |
| 05 | `05_ui_six_cards.png` | 浏览器访问 `http://127.0.0.1:8000/ui` 的 6 卡片 + 顶部 RAG 问答条 + 今日建议横条 | rag_api 启动 + 真画像 |
| 06 | `06_swagger_23_routes.png` | `http://127.0.0.1:8000/docs` 折叠后能看见 **20 API 路由 + 4 系统/UI 入口**（V3 阶段二/三/四/五新增 4 路由） | rag_api 启动 |
| 07 | `07_ui_console_careerflow_stepper.png` | `http://127.0.0.1:8000/ui/console` CareerFlow 8 步 Stepper：profile→job_input→match→gap→plan→today→resume→application_suggest 全 done | rag_api 启动 + 真画像 |

> 截图存为 PNG，分辨率不低于 1280×800，内容字号清晰可读。

