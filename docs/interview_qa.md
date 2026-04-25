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

## Q3: ChromaDB 118 chunks 性能够吗？后续怎么扩？

**A**：当前是个人项目，全量 118 chunks 单次查询 < 50ms，PersistentClient SQLite 落盘足够。扩展路径：① chunks > 10 万走 HNSW 索引调参（M、ef_construction）；② chunks > 100 万切到 Milvus / Qdrant；③ 加 metadata filter（按 source 预筛）减小搜索域。

---

## Q4: Recall@5 = 0.96 意味着什么？怎么把它提到 1.0？

**A**：自建 50 题 3 桶集（fact / explain / cross_doc）共 50 题，48 题 top-5 命中期望源；分桶看 cross_doc 1.000、explain 0.944、fact 0.941。
**两个 miss 案例已定位**：① `f03`（"目标方向第一优先级"）被 SOUL.md 抢占；② `e05`（"识别伪造信息"）被 DATA_CONTRACT.md 抢占。两者根因都是 chunk 边界把关键句切碎了。
**下一步**：① 调小 chunk_overlap，按 ## 二级标题强制保留语义单元；② 加 LLM rerank（top-20 → top-5）；③ 扩评估集到 100 题做 ablation；④ baseline 写进 `tests/rag_eval_baseline.json` 实现回归对比。

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

## Q8: pytest 37 个用例，哪些是真正"防御性"的？

**A**：核心防御性用例 4 类：
1. **三档结论枚举校验**（`test_match_demo_runs`）—— 防止改规则把结论字符串写错；
2. **persona schema 校验**（`test_persona_schema`）—— 防止新增 persona JSON 漏字段；
3. **multi-persona × multi-JD 参数化**（12 用例）—— 改 match_job 规则后立即看到副作用；
4. **FastAPI TestClient 接口测 + 主链路冒烟**（`tests/test_api.py` + `tests/test_pipeline.py`，新增 19 用例）—— 不依赖 LLM 的 8 个离线 + 3 个 e2e（默认跳过，OFFERCLAW_E2E=1 才跑）+ 6 步主链路 smoke。

总计 37 通过，3 e2e 待 flag 触发。

---

## Q9: 这个项目实际用没用？跑了多久？

**A**：从 2026-04-15 开 SOUL.md 起到现在 ~10 天，我每天用它来：① 看我新发现的 JD 适合不适合投；② 把 4 周路线写进 daily_log；③ 周日跑 weekly summary。GitHub commit 历史就是真实使用日志。它**首先**是一个解决我自己问题的产品，**其次**才是一份简历项目——这是我和很多"为了简历而做"的项目最大的区别。

---

## Q10～Q15: 高频追问（六连问）

### Q10: 为什么不直接用 LangChain Agent / LlamaIndex？
**A**：① LangChain Agent 黑盒太多，工具循环和 prompt 拼装藏在内部，调试困难；② LlamaIndex 偏向"知识库 + RAG"重场景，我这里需要"规则 + LLM + RAG"混合编排，LangGraph 的状态机更直白；③ 项目要写进简历，需要"我能讲清每一步为什么"——黑盒越少越好。LangGraph + 直调 requests + 手写 JWT 让每一行都可解释。

### Q11: 为什么评估集只有 50 题？是不是太少？
**A**：完全同意小，所以 README/简历都标了"**自建小规模评估集**"，不冒充通用基准。50 题是单人项目能负担的标注成本天花板（每题要写 q + 至少一个 expected_source）。3 桶设计是为了能看到分项弱点（fact / explain / cross_doc）。下一步 100 题，再下一步引入合成数据 + 人工抽检。

### Q12: `/api/profile` 是不是写死的 demo 数据？
**A**：之前是，现在不是。当前实现 `_parse_profile()` 用正则从 `user_profile.md` 解析 name / direction / skills / updated_at，user_profile.md 改名（比如 Zhang Yi → 张三）API 返回会跟着变。可以现场 demo：改文件 → curl /api/profile 立刻看到新值。这是"画像驱动"主张的最小证据。

### Q13: ChromaDB vs FAISS / Milvus / Qdrant 怎么选的？
**A**：① 单人项目 100~10000 chunks 量级，FAISS 要自己管持久化和元数据，麻烦；② Milvus / Qdrant 要起 server，部署成本高；③ ChromaDB PersistentClient 直接 SQLite 落盘，自带元数据 filter，单文件可移植。**取舍**：放弃了"分布式 / 千万级"，换"零部署 / 直接可演示"。这是写在 `docs/postmortem.md` 的第 1 条取舍。

### Q14: Agent 会不会乱改我的画像？怎么保证？
**A**：写在 `DATA_CONTRACT.md` 的 7 条不变量第 1 条：**Agent 永不直接修改 `user_profile.md`**。所有"画像更新建议"通过两条路径：① 写到 `summaries/` 让用户人工确认后回写；② 写到 `memory.json` 作为 Agent 短期记忆，和 user 层物理隔离。User Layer / System Layer / Runtime Layer 的边界写在 contract 里，doctor.py 会检查这三层目录是否齐全。

### Q15: 智谱 `embedding-3` 为什么选这个？换 OpenAI / BGE 行不行？
**A**：① 国产合规，对个人项目演示场景没出海/付款心智成本；② 2048 维语义足够，比 text-embedding-3-small 的 1536 还多；③ 与 GLM-4-Flash 同栈一份 JWT 签名搞定。**换不行吗？** 完全可以，`rag_tools.py` 把 embedding 调用收敛到一个函数 `get_embedding()`，换 BGE 只要改这一处 + 重新 ingest 一次 chroma。这是"接口收敛"的好处。

---

## Q16（反问对方）

可以问招聘官的：
- 团队当前在 RAG 上的主要瓶颈是检索质量、生成质量、工程化，还是评估方法？
- 蔚来内部 LLM 应用的链路编排是用 LangGraph、自研 DAG，还是 LangChain Expression Language？
- 实习生有机会接触从 0 到 1 的工作流落地，还是更多在已有系统上做局部优化？
- 评估部分（RAGAS / 自定义指标）有没有标准化的内部工具，还是每个项目自己造？
