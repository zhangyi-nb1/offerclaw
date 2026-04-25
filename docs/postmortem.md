# OfferClaw · 技术复盘（Postmortem）

> 用途：记录 V1 阶段的关键技术取舍、踩过的坑、未解决的问题。  
> 面试当问"这个项目最难的部分是什么 / 如果重做你会怎么改"时，从这里挑答案。

---

## 1. 关键技术取舍（Trade-offs）

### 1.1 规则版岗位匹配 vs 端到端 LLM
**选了规则**。  
- LLM 在 JD 长文本上的语义理解优于规则，但 (a) 同一 JD 不同 Prompt 给不同结论，(b) 没法回归测试，(c) Token 成本高
- 把"硬否决"（地点 / Java 主线 / 不接受日常实习）抽到 `target_rules.md` + `match_job.py`，LLM 只在规则放行后做"软评估"
- 代价：对 JD 的语义模糊地带（例如"Java 优先但 Python 也行"）要靠人工运维规则
- **如重做**：保留双通路；增加一个规则覆盖率监控（每周看有多少 JD 走到 LLM 兜底，> 50% 就该重写规则）

### 1.2 文件级 RAG vs 数据库 RAG
**选了文件级**。  
- 项目状态全是 markdown，文件级 + ChromaDB 单机部署够用
- 规模到 100+ markdown 时再考虑迁 PostgreSQL + pgvector
- **如重做**：从一开始就用 `rag_ingest.py --watch` 模式自动监听文件变更（现在是手动跑）

### 1.3 LangGraph vs 自写状态机
**选了 LangGraph**（晚引入）。  
- 一开始 `pipeline.py` 是 Python 函数顺序调用，三个分支后开始变成 if/else 地狱
- LangGraph 的强制"显式 State"反而帮我把隐式状态全暴露
- 代价：BaseMessage 序列化要写适配层（`_msg_to_dict`），原生不支持
- **如重做**：可能直接用 LangGraph，不会先走顺序脚本

### 1.4 FastAPI 何时引入
**选在 RAG 完成后引入**。  
- 早引入 → 还没核心功能就在写接口契约，浪费
- 晚引入 → 来不及做前端 demo
- 时机：RAG 跑出第一个 Recall@5 数字后立刻封 API
- **如重做**：同样时机，但接口的 Pydantic Schema 更早冻结，避免后期改 contract

### 1.5 前端：Streamlit vs Vanilla HTML
**选了 Vanilla HTML**。  
- Streamlit 引入 200+ MB 依赖，跟主项目（FastAPI + 智谱）不搭
- Gradio 同理
- 一个零依赖单文件 `static/index.html`，跟 repo 同步推 GitHub
- 代价：要自己处理 SSE（POST + EventSource 不兼容，被迫 fetch + ReadableStream）
- **如重做**：同样选 Vanilla；若上多用户再考虑 React + Vite

### 1.6 评估集只 8 题
**承认是不足**。  
- 8 题黄金集是手工标注，覆盖"硬否决规则 / 三档定义 / 4 周计划格式"等元问题
- 当前 Recall@5 = 0.75 / MRR = 0.69 在 8 题级别有参考价值，但**统计置信度低**
- **下一步**：扩到 50+ 题；引入分桶（事实型 / 解释型 / 跨文档组合型）

---

## 2. 踩过的坑

### 2.1 中文 markdown 切 chunk
- 一开始用 token-based（每 256 token 一切），结果中文章节边界被破坏，Recall@5 卡在 0.50
- 改为 markdown-header-based（`#` `##` `###` 切），不破坏语义单元，立刻 +25 个百分点
- **教训**：RAG 90% 的瓶颈在 ingest，不在 retrieval / rerank

### 2.2 智谱 JWT 时间戳必须毫秒
- 用秒级时间戳 401 鉴权失败；查源码发现要 `int(time.time() * 1000)`
- **教训**：第三方 API 集成必读 SDK 源码或官方示例的 timestamp 实现

### 2.3 LangGraph BaseMessage 序列化
- 原生 `state.dict()` 会把 BaseMessage 字段 dump 失败
- 加 `_msg_to_dict()` 把每个 message 转成 `{"type":..., "content":...}` 再 dump
- **教训**：LangGraph 的 State 字段如果含 LangChain 对象，要自己写 serializer

### 2.4 FastAPI POST + SSE 浏览器侧
- 浏览器原生 `EventSource` 只支持 GET
- 前端用 fetch + reader.read() + TextDecoder 自己解析 `event:`/`data:` 块
- **教训**：SSE 标准没说 POST 不行，是浏览器实现限制

### 2.5 Windows 终端编码 cp936
- subprocess.stdout 默认 cp936，print 含 emoji 直接 `UnicodeEncodeError`
- 全部 emoji 替换 ASCII，subprocess decode 加 `errors="replace"`
- **教训**：Windows 上的 Python 项目，默认假设 UTF-8 是错的

### 2.6 用户画像 API 硬编码
- 早期 `/api/profile` 把 `name = "Zhang Yi"` 写死在代码里
- 后来加 `_parse_profile()` 用正则从 `user_profile.md` 抽
- **教训**：任何"演示用"的硬编码必须在 PR 标题里加 `XXX: hardcoded for demo`，避免上线时漏改

---

## 3. 未解决的问题

| 问题 | 影响 | 计划 |
|---|---|---|
| 评估集 8 题 → 50+ 题 | 当前指标统计意义弱 | V2 扩集 + 分桶 |
| 没有 LLM Reranker | 长尾召回偏低 | V2 加 BGE-reranker |
| applications.md 是手维护表 | 真实投递跟踪难规模化 | V2 迁 SQLite |
| 没有 CI / Docker | 无法证明跨环境可复现 | V2 GitHub Actions + Dockerfile |
| 单用户 | 不能多人共用 | V3 用户隔离 |
| Memory.json 无 TTL | 长期会膨胀 | V2 加过期 + 摘要压缩 |
| 没有自动 JD 失效检测 | 可能匹配已下架的岗位 | V2 加 URL 健康检查 |

---

## 4. 给"下一个 V2 起点"的提示

如果你（或一年后的我）要继续做 V2：

1. **先扩 RAG 评估集到 50+ 题**，否则一切优化都是凭感觉
2. **再加 LLM Reranker**（BGE-reranker-v2-m3 或 GLM-4 二阶段），不要先调 chunk size
3. **applications.md 迁 SQLite** 之前先把字段冻结；当前字段已经够 V2 用
4. **CI 在 doctor.py + verify_pipeline.py 之上加一层 GitHub Actions**，跑 pytest + verify
5. **Docker 不要一开始打全栈镜像**，先 `python:3.13-slim` + 项目代码，ChromaDB 用 volume 挂载

---

## 5. 我从这个项目学到的（个人）

- **闭环优于功能数**：6 周里我两次想加新技术（多模态 / Function Calling Marketplace），都砍了
- **deterministic first**：能用规则解的别交给 LLM
- **eval 是 RAG 的必须项**：没有黄金集的 RAG 系统等于在黑箱调参
- **状态分层**：用户层 / 系统层 / 运行时层一旦分清，整个项目的可维护性上一个台阶（见 `DATA_CONTRACT.md`）
- **工程可信度 ≠ 功能数**：`doctor.py` + `verify_pipeline.py` 比再加 3 个 FastAPI 接口更能让别人相信这个项目能跑
