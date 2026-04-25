# OfferClaw · 面试问答卡

> 8-10 题，覆盖技术深度 + 项目动机 + 反问准备。

---

## Q1: 为什么用 LangGraph 而不是直接 if/else 编排？

**A**：手写编排有 3 个痛点：① 工具调用循环要自己写终止条件；② 状态在函数间传递混乱；③ 不可视化没法跟人讲清楚。LangGraph 把"节点 + 边 + 条件分支"声明式建模，4 节点（retrieve / build_prompt / call_llm / execute_tools）+ 1 条件边（是否还有 tool_calls）就描述清楚了整个 RAG-Agent。
**踩过的坑**：`add_messages` 注解会自动把 dict 转成 `BaseMessage` 对象，传给智谱 API 时 `json.dumps` 序列化失败（SystemMessage 不可 JSON 化）→ 我加了一个 `_msg_to_dict()` 适配层。

---

## Q2: 为什么自己写 JWT 而不用 PyJWT？

**A**：智谱的 JWT 规范有两点特殊：① payload 时间戳是**毫秒**不是秒；② signing secret 与 key_id 用 `.` 分隔成单一环境变量。引第三方包要么版本绑定、要么得自己适配——纯标准库 `hmac+hashlib+base64url` 实现 30 行就够，对依赖更可控。

---

## Q3: ChromaDB 50 chunks 性能够吗？后续怎么扩？

**A**：当前是个人项目，全量 50 chunks 单次查询 < 50ms，PersistentClient SQLite 落盘足够。扩展路径：① chunks > 10 万走 HNSW 索引调参（M、ef_construction）；② chunks > 100 万切到 Milvus / Qdrant；③ 加 metadata filter（按 source 预筛）减小搜索域。

---

## Q4: Recall@5=0.75 意味着什么？怎么把它提到 0.9+？

**A**：8 题里 6 题 top-5 命中期望源。两个 miss 都是 prompt 类问题（"如何生成 4 周路线"，"留痕复盘偏离度"）—— 根因是 `plan_prompt.md` / `summary_prompt.md` 在 ingest 时被分块切碎，关键词分散到不同 chunk。
**优化方案**：① 调小 chunk_overlap，按 ## 标题强制保留语义单元；② 加 LLM rerank（先 top-20 召回，再让小模型按"与查询的相关性"打分，取 top-5）；③ 扩评估集到 30+ 题做 ablation。

---

## Q5: SSE 流式输出 vs WebSocket 怎么选？

**A**：① 单向推流（LLM token 单向往前端推）SSE 足够，WebSocket 是双向；② SSE 走 HTTP，无需额外协议握手，反向代理穿透更友好；③ SSE 自动重连。我这里只需要"一个问题→一段流式回答"，所以 SSE。如果做多轮 stream-in/stream-out 才上 WebSocket。

---

## Q6: 为什么硬门槛规则版要 Python 写、4 周计划要 LLM 写？

**A**：分清"确定性问题"和"生成性问题"。
- **硬门槛**（学历、地域、专业）= 业务规则 → Python 显式判断，可解释、可单测、不允许 LLM 脑补；
- **4 周计划**（叙事、节奏、内容编排）= 生成性 → LLM 拿手；规则写不出来。
这是项目里最重要的设计原则之一：**让 LLM 做它擅长的，规则做它擅长的，别混在一起。**

---

## Q7: 怎么保证 API Key 不进 Git？

**A**：① 把 key 写在 `.env.local`（双扩展名）；② `.gitignore` 加 `.env*` + 常用变体；③ `rag_tools._load_local_env()` 在 import 时读取写到 `os.environ`；④ 加一份 `.env.example` 给协作者参考。**踩过的坑**：`.gitignore` 不支持行内注释，`chroma_db/  # 注释` 会被解析成"忽略名为 chroma_db/  # 注释 的目录"，导致规则失效，要单独成行。

---

## Q8: pytest 17 个用例，哪些是真正"防御性"的？

**A**：核心防御性用例 3 类：
1. **三档结论枚举校验**（`test_match_demo_runs`）—— 防止有人改了规则把结论字符串写错；
2. **persona schema 校验**（`test_persona_schema`）—— 防止新增 persona JSON 漏字段，跑到 run_match 才崩；
3. **multi-persona × multi-JD 参数化**（12 用例）—— 任何人改 match_job 规则后能立即看到副作用。
其余几个是工具函数 unit test。下一步会加 API 接口的 httpx + pytest-asyncio 集成测。

---

## Q9: 这个项目实际用没用？跑了多久？

**A**：从 2026-04-15 开 SOUL.md 起到现在 ~10 天，我每天用它来：① 看我新发现的 JD 适合不适合投；② 把 4 周路线写进 daily_log；③ 周日跑 weekly summary。GitHub commit 历史就是真实使用日志。它**首先**是一个解决我自己问题的产品，**其次**才是一份简历项目——这是我和很多"为了简历而做"的项目最大的区别。

---

## Q10（反问对方）

可以问招聘官的：
- 团队当前在 RAG 上的主要瓶颈是检索质量、生成质量、工程化，还是评估方法？
- 蔚来内部 LLM 应用的链路编排是用 LangGraph、自研 DAG，还是 LangChain Expression Language？
- 实习生有机会接触从 0 到 1 的工作流落地，还是更多在已有系统上做局部优化？
- 评估部分（RAGAS / 自定义指标）有没有标准化的内部工具，还是每个项目自己造？
