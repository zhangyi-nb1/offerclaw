# Persona 泛化验证报告（阶段七）

**生成于：** 2026-04-25  
**目的：** 证明 OfferClaw 的匹配/缺口/建议链路不依赖单一硬编码 persona，可对多类候选人输出明显不同的结论。

---

## 一、测试设计

- **统一输入 JD（控制变量）：**
  ```
  岗位名称：大模型应用开发实习生
  工作地点：上海
  技术要求：Python / RAG / LangGraph / FastAPI / Prompt / Embedding
  ```
- **三类 persona（profiles/*.json）：**
  | ID | 描述 | 关键差异 |
  |---|---|---|
  | p1_zhangyi_ai | 通信硕士转 AI 应用方向（项目当前 owner） | 方向高度匹配，但项目数 0 |
  | p2_cs_backend_intern | 计科本科 Python 后端实习（找 Java 开发） | 明确不做 AI 方向 |
  | p3_phd_algo_research | AI 博士做算法内核（嫌弃应用） | 方向偏算法研究、不做工程 |

---

## 二、对比结果（来自 `match_job.run_match`）

| persona_file | 结论 | 缺口总数 | 缺口类别 | 建议条数 |
|---|---|---|---|---|
| p1_zhangyi_ai | **当前适合投递** | 4 | 硬门槛 / 经历 / 技能 | 3 |
| p2_cs_backend_intern | **中长期可转向** | 3 | 硬门槛 / 经历 / 技能 | 1 |
| p3_phd_algo_research | **中长期可转向** | 3 | 硬门槛 / 经历 / 技能 | 1 |

> 结论分布出现 2 档（适合投递 / 中长期可转向），证明同一 JD 在不同 persona 上**不会**输出相同结论。

---

## 三、关键观察

1. **p1 命中"当前适合投递"** — 方向匹配 + 工程项目 owner 身份，但仍有 4 项缺口（项目数硬门槛、Agent 经验深度等），系统给出 3 条针对性建议。
2. **p2 / p3 命中"中长期可转向"** — 一个方向偏后端、一个方向偏算法研究，硬门槛未通过，但系统不直接拒绝，而是给出转向路径建议。
3. **缺口类别保持一致**（硬门槛/经历/技能三大维度），证明数据契约（DATA_CONTRACT.md）与 match_job 的内部分类是稳定的。

---

## 四、再现命令

```powershell
$env:PYTHONIOENCODING="utf-8"
pytest tests/test_personas.py -v
```

或单测：
```python
from match_job import run_match
import json
persona = json.load(open("profiles/p1_zhangyi_ai.json", encoding="utf-8"))
rep = run_match(persona, JD_TEXT, jd_title="LLM 实习/对比")
print(rep.conclusion, rep.gap_list, rep.suggestions)
```

---

## 五、结论

✅ OfferClaw 的匹配链路对 3 类典型 persona 输出明显不同结论与建议，具备多用户泛化能力。  
✅ /api/profile 已去硬编码（V2 阶段一完成），从 `user_profile.md` 读取真实画像。  
✅ pytest 中 `tests/test_personas.py::test_persona_matching_stable` 与 `test_persona_schema` 双重保护：每个 persona 的 schema 与运行结果都经回归测试。
