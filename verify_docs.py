"""verify_docs.py — 文档指标一致性巡检

扫描 README.md / docs/verification_report.md / docs/project_one_pager.md /
PROJECT_STATUS.md，检查关键指标（Recall@5 / MRR / cross_doc / chunks /
FastAPI 路由数 / pytest / doctor）口径是否一致。

退出码：0 = 全部一致；1 = 发现不一致；2 = 找不到文件。

用法：
    python verify_docs.py
    python verify_docs.py --json    # 机器可读输出
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent

# 文件 → 标签
FILES = {
    "README.md": "README",
    "docs/verification_report.md": "verification_report",
    "docs/project_one_pager.md": "project_one_pager",
    "PROJECT_STATUS.md": "PROJECT_STATUS",
}

# 指标名 → 正则模式列表（任一命中即采集；取每个文件第一条命中）
PATTERNS = {
    "Recall@5": [
        r"Recall@5[^0-9]{0,8}([01]\.\d{2,3})",
        r"recall@5[^0-9]{0,8}([01]\.\d{2,3})",
    ],
    "MRR": [
        r"MRR[^0-9]{0,8}([01]\.\d{2,3})",
    ],
    "cross_doc": [
        r"cross_doc[^0-9]{0,12}([01]\.\d{2,3})",
    ],
    "chunks": [
        r"(\d{2,4})\s*chunks",
        r"chunks[^0-9]{0,8}(\d{2,4})",
    ],
    "routes": [
        r"(\d{1,3})\s*(?:FastAPI\s*)?(?:路由|routes|接口)",
        r"FastAPI[^0-9]{0,12}(\d{1,3})\s*(?:路由|routes|接口|个)",
    ],
    "pytest": [
        r"pytest[^0-9]{0,8}(\d{1,3})\s*/\s*\d{1,3}",
        r"(\d{1,3})\s*/\s*\d{1,3}\s*pytest",
    ],
    "doctor_ok": [
        r"doctor[^0-9]{0,12}(\d{1,2})\s*OK",
    ],
}

# 期望（V2 终态）口径——同时也是修复方向
EXPECTED = {
    "Recall@5": "0.96",
    "MRR": "0.67",
    "cross_doc": "1.00",
    "chunks": "160",
    "routes": "19",
    "doctor_ok": "9",
}


def scan_file(path: Path) -> dict:
    if not path.exists():
        return {"_error": f"missing: {path}"}
    text = path.read_text(encoding="utf-8", errors="ignore")
    out: dict = {}
    for metric, regs in PATTERNS.items():
        hits: list[str] = []
        for pat in regs:
            hits.extend(re.findall(pat, text, re.IGNORECASE))
        # 去重保序
        seen = []
        for h in hits:
            if h not in seen:
                seen.append(h)
        out[metric] = seen if seen else None
    return out


def collect() -> dict:
    return {tag: scan_file(ROOT / rel) for rel, tag in FILES.items()}


def compare(table: dict) -> list[dict]:
    """对每个指标：每个文件只要包含 expected 值就算一致。"""
    issues = []
    for m, expected in EXPECTED.items():
        bad: dict[str, list[str]] = {}
        for tag, row in table.items():
            hits = row.get(m)
            if hits is None:
                continue  # 该文件未提及，不算违规
            if expected not in hits:
                bad[tag] = hits
        if bad:
            issues.append({"metric": m, "expected": expected, "violations": bad})
    return issues


def render_text(table: dict, issues: list[dict]) -> str:
    lines = ["# verify_docs report", ""]
    lines.append("## 各文档采集到的指标值（含历史/基线注释中出现的）")
    lines.append("")
    headers = ["metric"] + list(table.keys()) + ["expected (V2)"]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join(["---"] * len(headers)) + "|")
    for m in PATTERNS.keys():
        row = [m]
        for tag in table.keys():
            hits = table[tag].get(m)
            row.append(",".join(hits) if hits else "—")
        row.append(str(EXPECTED.get(m, "—")))
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    if issues:
        lines.append(f"## ❌ 发现 {len(issues)} 处不一致")
        for it in issues:
            lines.append(f"- **{it['metric']}** → expected `{it['expected']}` not present in:")
            for tag, hits in it["violations"].items():
                lines.append(f"    - {tag}: {hits}")
    else:
        lines.append("## ✅ 所有指标在 4 份文档中均包含 V2 期望值。")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="docs metric consistency check")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    table = collect()
    missing = [tag for tag, row in table.items() if "_error" in row]
    if missing:
        print(f"missing files: {missing}", file=sys.stderr)
        return 2

    issues = compare(table)

    if args.json:
        print(json.dumps({"table": table, "issues": issues, "expected": EXPECTED},
                         ensure_ascii=False, indent=2))
    else:
        print(render_text(table, issues))

    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
