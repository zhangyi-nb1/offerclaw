# -*- coding: utf-8 -*-
"""resume_project.py — 项目 → 简历项目经历段 生成器。

用户流程（用户定义）：
- 用户提供项目素材（三选一）：①项目仓库地址（GitHub 公开仓库，自动抓 README/docs）
  ②项目介绍 .md/.txt 文件 ③直接粘贴项目介绍文本；
- OfferClaw 分析项目要点（定位/技术栈/难点/量化结果），按"简历模板模式"输出
  **可直接粘贴进简历**的项目经历段。

模板学习：
- 用户把自己认可的简历模板（.md）放进 ``resume_templates/``，生成时会把模板
  作为**格式范例**注入 prompt，让输出严格贴合用户偏好的样式；
- 目录为空时使用内置默认模式（经典三段式）。模板属个人文件，不入 git。
"""

from __future__ import annotations

import glob
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "resume_templates")

_MAX_MATERIAL_CHARS = 16000     # 项目素材注入上限
_MAX_TEMPLATE_CHARS = 3000      # 单个模板注入上限

# 内置默认模式：用户模板未提供时的兜底格式约定
_DEFAULT_PATTERN = """（内置默认模式 · 经典三段式）
**项目名 | 角色 | 起止时间**
一句话定位：这个项目是什么、解决什么问题（含核心技术栈）。
- 要点 1：动词开头 + 做了什么 + 用了什么技术 + 量化结果（数字/比例/规模）
- 要点 2：突出难点与你的解法（如 检索召回从 X 提升到 Y）
- 要点 3：工程化/协作亮点（部署、测试、CI、文档）
成果：1 句话总结可验证的产出（线上效果 / star 数 / 用户量 / 性能指标）。"""


def load_templates() -> list[dict]:
    """读取 resume_templates/ 下用户提供的简历模板（README 除外）。"""
    out = []
    for p in sorted(glob.glob(os.path.join(TEMPLATES_DIR, "*.md"))):
        if os.path.basename(p).lower() == "readme.md":
            continue
        try:
            with open(p, encoding="utf-8") as f:
                out.append({"name": os.path.basename(p),
                            "content": f.read()[:_MAX_TEMPLATE_CHARS]})
        except OSError:
            continue
    return out


def gather_material(repo_url: str = "", text: str = "") -> dict:
    """汇集项目素材：直接文本优先；否则按仓库地址抓取（GitHub 整仓 README/docs）。

    返回 {status:"ok", material, origin} 或 {status:"error", error}。
    """
    text = (text or "").strip()
    if text:
        return {"status": "ok", "material": text[:_MAX_MATERIAL_CHARS], "origin": "用户提供文本"}
    repo_url = (repo_url or "").strip()
    if not repo_url:
        return {"status": "error", "error": "请提供 仓库地址 / 项目介绍文件 / 项目介绍文本 之一"}
    from knowledge_crawler import is_github_repo_url, fetch_repo_text
    if is_github_repo_url(repo_url):
        fetched = fetch_repo_text(repo_url)
        if fetched.get("status") != "ok":
            return {"status": "error", "error": f"仓库抓取失败：{fetched.get('error', '未知')}"}
        return {"status": "ok", "material": fetched["text"][:_MAX_MATERIAL_CHARS],
                "origin": f"GitHub 仓库（{fetched['files_captured']} 个文件）"}
    # 非 GitHub：按普通网页抓正文
    try:
        from job_discovery import fetch_url
        body = fetch_url(repo_url)
        return {"status": "ok", "material": body[:_MAX_MATERIAL_CHARS], "origin": "网页抓取"}
    except Exception as e:
        return {"status": "error", "error": f"页面抓取失败：{e}"}


def build_project_messages(material: str, project_name: str = "",
                           profile: str = "") -> list:
    """组装"项目分析 → 简历段"的 LLM messages。"""
    templates = load_templates()
    if templates:
        tpl_block = "\n\n".join(
            f"--- 模板范例 {i+1}：{t['name']} ---\n{t['content']}"
            for i, t in enumerate(templates[:3])
        )
        tpl_directive = ("以下是用户提供的简历模板范例，**严格学习其格式/语气/排版模式**，"
                         "输出必须与模板同款式：\n\n" + tpl_block)
    else:
        tpl_directive = ("用户暂未提供简历模板，按以下内置默认模式输出：\n\n" + _DEFAULT_PATTERN)

    system = (
        "你是 OfferClaw 的简历工程师，目标岗位方向：大模型应用工程师。\n"
        "任务：从项目素材中提炼要点，生成**可直接粘贴进简历**的「项目经历」段。\n\n"
        "分析方法（先内部完成，不要输出过程）：\n"
        "1) 项目定位：一句话讲清是什么、解决什么问题；\n"
        "2) 技术要点：技术栈、架构、关键实现（RAG/Agent/工程化优先突出）；\n"
        "3) 难点与解法：挑最有面试讨论价值的 1-2 个；\n"
        "4) 量化：凡素材中有数字（性能/规模/覆盖率/star）必须用上；没有就用可验证的事实描述，"
        "**绝不编造数字**。\n\n"
        + tpl_directive +
        "\n\n输出要求：只输出简历段本身（markdown），不要寒暄、不要解释；"
        "中文为主，技术名词保留英文；3-5 条要点，每条一行，动词开头。"
        + (f"\n\n用户画像（用于对齐方向与措辞）：\n{profile[:2000]}" if profile else "")
    )
    user = (f"项目名称：{project_name or '（素材中自行识别）'}\n\n"
            f"========== 项目素材 ==========\n{material}")
    return [{"role": "system", "content": system},
            {"role": "user", "content": user}]
