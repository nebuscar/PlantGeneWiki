"""
文献分类器：用 LLM 从 title + abstract 提取结构化标签

标签类型：gene / species / research_type / keyword
分类结果存入 paper_tags 表，并触发摘要缓存失效。
"""
from __future__ import annotations

import json
import sqlite3

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from lit_pipeline.processor import PAPER_DB, _set_status

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

CLASSIFY_PROMPT = """你是植物基因研究领域的文献分类专家。
请从以下文献的标题和摘要中，提取结构化标签，以 JSON 格式返回。

文献信息：
标题：{title}
摘要：{abstract}

请返回如下格式的 JSON（不要有其他内容）：
{{
  "genes": ["基因名1", "基因名2"],           // 涉及的基因/蛋白名称，统一大写，如 FAD2、WRKY70
  "species": ["物种1", "物种2"],             // 涉及的植物物种（学名或常用名）
  "research_types": ["类型1", "类型2"],      // 研究类型：functional_validation / QTL / GWAS / CRISPR / RNAi / expression_analysis / review / evolution / other
  "keywords": ["关键词1", "关键词2"]         // 最多 5 个核心关键词（英文）
}}

注意：
- genes 只写基因/蛋白名，不写物种前缀（如只写 FAD2，不写 AtFAD2）
- 若不确定某字段，返回空数组 []
"""


def classify_paper(paper_id: str) -> dict:
    """
    对单篇文献执行 LLM 分类，结果写入 paper_tags 表。
    同时触发相关摘要缓存失效。
    返回分类结果字典。
    """
    conn = sqlite3.connect(str(PAPER_DB))
    row = conn.execute(
        "SELECT title, abstract FROM papers WHERE paper_id=?", (paper_id,)
    ).fetchone()
    conn.close()

    if not row:
        return {"error": f"paper_id {paper_id} 不存在"}

    title, abstract = row
    title    = title    or ""
    abstract = abstract or ""

    prompt = CLASSIFY_PROMPT.format(title=title, abstract=abstract[:2000])

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        # 提取 JSON（防止 LLM 多说了几句话）
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        tags  = json.loads(raw[start:end])
    except Exception as e:
        return {"error": f"LLM 分类失败：{e}"}

    # 写入 paper_tags
    conn = sqlite3.connect(str(PAPER_DB))
    conn.execute("DELETE FROM paper_tags WHERE paper_id=?", (paper_id,))

    tag_rows = []
    for gene in tags.get("genes", []):
        tag_rows.append((paper_id, "gene", gene.upper(), 0.9))
    for sp in tags.get("species", []):
        tag_rows.append((paper_id, "species", sp, 0.9))
    for rt in tags.get("research_types", []):
        tag_rows.append((paper_id, "research_type", rt, 0.9))
    for kw in tags.get("keywords", []):
        tag_rows.append((paper_id, "keyword", kw.lower(), 0.9))

    conn.executemany(
        "INSERT OR REPLACE INTO paper_tags (paper_id, tag_type, tag_value, confidence) "
        "VALUES (?, ?, ?, ?)",
        tag_rows
    )
    conn.commit()
    conn.close()

    # 触发相关摘要缓存失效
    invalidation_tags = (
        [g.upper() for g in tags.get("genes", [])] +
        tags.get("species", []) +
        [kw.lower() for kw in tags.get("keywords", [])]
    )
    if invalidation_tags:
        from tools.lit_tools import invalidate_summary_cache
        invalidate_summary_cache(invalidation_tags)

    return tags


def classify_all_pending() -> list[dict]:
    """批量分类所有 status='done'（已 embedding）但尚无标签的文献。"""
    conn = sqlite3.connect(str(PAPER_DB))
    rows = conn.execute(
        "SELECT paper_id FROM papers WHERE status='done' "
        "AND paper_id NOT IN (SELECT DISTINCT paper_id FROM paper_tags)"
    ).fetchall()
    conn.close()

    results = []
    for (pid,) in rows:
        result = classify_paper(pid)
        results.append({"paper_id": pid, **result})
    return results


def get_paper_tags(paper_id: str) -> dict:
    """获取某文献的所有标签。"""
    conn = sqlite3.connect(str(PAPER_DB))
    rows = conn.execute(
        "SELECT tag_type, tag_value FROM paper_tags WHERE paper_id=?", (paper_id,)
    ).fetchall()
    conn.close()

    tags: dict[str, list] = {}
    for tag_type, tag_value in rows:
        tags.setdefault(tag_type, []).append(tag_value)
    return tags


def update_tags(paper_id: str, tags: dict):
    """管理员手动修正标签时调用。tags 格式同 classify_paper 返回值。"""
    conn = sqlite3.connect(str(PAPER_DB))
    conn.execute("DELETE FROM paper_tags WHERE paper_id=?", (paper_id,))
    tag_rows = []
    for tag_type, values in tags.items():
        for v in values:
            tag_rows.append((paper_id, tag_type, str(v), 1.0))   # confidence=1.0 表示人工确认
    conn.executemany(
        "INSERT OR REPLACE INTO paper_tags VALUES (?, ?, ?, ?)", tag_rows
    )
    conn.commit()
    conn.close()
