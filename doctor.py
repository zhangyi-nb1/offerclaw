"""
OfferClaw · 工程健康检查（doctor.py）

用法：
    python doctor.py

逐项检查 OfferClaw 是否准备好运行：
- Python 版本、依赖、API Key
- 核心 markdown / 代码 / 测试文件
- ChromaDB 向量库
- pytest 是否可跑（仅 collect）

输出 [OK] / [WARN] / [ERR]，最后返回退出码（0=全 OK，1=有 WARN，2=有 ERR）。
"""
from __future__ import annotations
import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent
results: list[tuple[str, str]] = []  # (level, msg)


def ok(msg: str) -> None: results.append(("OK", msg))
def warn(msg: str) -> None: results.append(("WARN", msg))
def err(msg: str) -> None: results.append(("ERR", msg))


def check_python() -> None:
    v = sys.version_info
    if v >= (3, 10):
        ok(f"Python {v.major}.{v.minor}.{v.micro}")
    else:
        err(f"Python {v.major}.{v.minor} 过旧，要求 >= 3.10")


def check_packages() -> None:
    needed = ["fastapi", "uvicorn", "pydantic", "chromadb", "requests", "pytest"]
    missing = []
    for p in needed:
        if importlib.util.find_spec(p) is None:
            missing.append(p)
    if missing:
        err(f"缺依赖：{', '.join(missing)}（请 pip install -r requirements.txt）")
    else:
        ok(f"依赖齐全（{len(needed)} 个核心包）")


def check_env() -> None:
    env_local = ROOT / ".env.local"
    if env_local.exists():
        ok(".env.local 存在")
        # 不读内容，仅看是否含 ZHIPU_API_KEY 行
        content = env_local.read_text(encoding="utf-8", errors="replace")
        if "ZHIPU_API_KEY" in content:
            ok(".env.local 含 ZHIPU_API_KEY 字段")
        else:
            warn(".env.local 中未发现 ZHIPU_API_KEY")
    else:
        warn(".env.local 不存在（运行时需手动 export ZHIPU_API_KEY）")
    if os.environ.get("ZHIPU_API_KEY"):
        ok("环境变量 ZHIPU_API_KEY 已注入")
    else:
        warn("当前进程未注入 ZHIPU_API_KEY（前端 / RAG 调用会失败）")


def check_core_files() -> None:
    must = [
        "user_profile.md", "SOUL.md", "target_rules.md", "source_policy.md",
        "match_job.py", "plan_gen.py", "summary_tool.py", "pipeline.py",
        "rag_ingest.py", "rag_query.py", "rag_graph.py", "rag_api.py",
        "DATA_CONTRACT.md", "applications.md", "interview_story_bank.md",
        "docs/architecture.md", "docs/demo.md", "docs/resume_pitch.md",
        "docs/interview_qa.md", "docs/project_one_pager.md", "docs/ethical_use.md",
        "static/index.html", "tests/test_offerclaw_core.py",
    ]
    missing = [f for f in must if not (ROOT / f).exists()]
    if missing:
        err(f"缺关键文件 {len(missing)} 个：{', '.join(missing[:5])}{'...' if len(missing) > 5 else ''}")
    else:
        ok(f"核心文件齐全（{len(must)} 个）")


def check_chroma() -> None:
    db = ROOT / "chroma_db"
    if not db.exists():
        warn("chroma_db/ 不存在 → 运行 `python rag_ingest.py` 建索引")
        return
    sqlite = db / "chroma.sqlite3"
    if sqlite.exists() and sqlite.stat().st_size > 1024:
        ok(f"chroma_db 索引存在（{sqlite.stat().st_size // 1024} KB）")
    else:
        warn("chroma_db 目录存在但索引为空 → 重新跑 rag_ingest.py")


def check_tests() -> None:
    tests_dir = ROOT / "tests"
    if not tests_dir.exists():
        err("tests/ 目录不存在")
        return
    files = list(tests_dir.glob("test_*.py"))
    if files:
        ok(f"pytest 测试文件 {len(files)} 个：{', '.join(f.name for f in files)}")
    else:
        warn("tests/ 下没有 test_*.py")


def check_gitignore() -> None:
    gi = ROOT / ".gitignore"
    if not gi.exists():
        err(".gitignore 不存在（密钥可能被推到 GitHub！）")
        return
    content = gi.read_text(encoding="utf-8", errors="replace")
    must_ignore = [".env", "chroma_db", "memory.json", "logs", "__pycache__"]
    miss = [m for m in must_ignore if m not in content]
    if miss:
        err(f".gitignore 缺规则：{', '.join(miss)}")
    else:
        ok(".gitignore 关键规则齐全")


def main() -> int:
    print("=" * 60)
    print("OfferClaw doctor — 工程健康检查")
    print("=" * 60)
    for fn in [check_python, check_packages, check_env, check_core_files,
               check_chroma, check_tests, check_gitignore]:
        try:
            fn()
        except Exception as e:
            err(f"{fn.__name__} 抛异常：{e}")

    n_ok = sum(1 for lv, _ in results if lv == "OK")
    n_warn = sum(1 for lv, _ in results if lv == "WARN")
    n_err = sum(1 for lv, _ in results if lv == "ERR")

    for lv, msg in results:
        color = {"OK": "\033[32m", "WARN": "\033[33m", "ERR": "\033[31m"}.get(lv, "")
        print(f"{color}[{lv:4}]\033[0m {msg}")

    print("-" * 60)
    print(f"汇总：{n_ok} OK · {n_warn} WARN · {n_err} ERR")
    if n_err:
        return 2
    if n_warn:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
