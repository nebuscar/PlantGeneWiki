"""
摘要生成器：对某主题的文献生成综述摘要（预生成或实时生成）

由 get_lit_summary 工具调用（缓存 miss 时），
以及文献上传后的批量预生成任务调用。
"""
from __future__ import annotations

import sqlite3

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from lit_pipeline.processor import PAPER_DB
from tools.lit_tools import search_literature

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SUMMARY_PROMPT = """你是植物基因研究领域的专家。
请基于以下文献段落，对主题「{topic}」撰写一段简明的研究综述。

文献段落（已按相关度排序）：
{passages}

要求：
1. 用中文撰写，约 200-300 字
2. 提炼 3-5 个核心研究发现作为要点列表
3. 每个结论必须能追溯到具体文献
4. 不要凭空推断文献未提及的内容
5. 以 JSON 格式返回：
{{
  "summary": "综述正文...",
  "key_findings": ["发现1（来源：作者 年份）", "发现2...", ...]
}}
"""


def generate_summary(topic: str, filters: dict | None = None) -> dict:
    """
    实时生成文献综述摘要。
    先检索最相关的 10 篇段落，再用 LLM 整合。
    """
    passages = search_literature(query=topic, filters=filters, top_k=10)

    if not passages:
        return {
            "summary":      f"数据库中暂无与「{topic}」相关的文献。",
            "key_findings": [],
            "papers_cited": [],
        }

    # 构建 passage 文本（含来源标注）
    passage_texts = []
    for p in passages:
        citation = f"{p['authors'][0] if p['authors'] else '未知'} {p['year'] or ''}"
        passage_texts.append(f"[{citation}] {p['content'][:600]}")

    prompt = SUMMARY_PROMPT.format(
        topic=topic,
        passages="\n\n".join(passage_texts),
    )

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw   = response.content[0].text.strip()
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        data  = __import__("json").loads(raw[start:end])
    except Exception as e:
        data = {
            "summary":      f"摘要生成失败（{e}），请查看原始检索结果。",
            "key_findings": [],
        }

    # 收集引用的文献信息（去重）
    seen_dois, cited = set(), []
    for p in passages:
        doi = p.get("doi", "")
        if doi and doi not in seen_dois:
            seen_dois.add(doi)
            cited.append({
                "title":  p.get("title", ""),
                "doi":    doi,
                "year":   p.get("year"),
            })

    return {
        "summary":      data.get("summary", ""),
        "key_findings": data.get("key_findings", []),
        "papers_cited": cited,
    }


def pregenerate_summaries() -> list[dict]:
    """
    批量预生成摘要：为所有出现在 paper_tags 中的 gene 和 species 标签生成摘要。
    供文献上传流水线的最后一步调用。
    """
    conn = sqlite3.connect(str(PAPER_DB))
    gene_tags    = [r[0] for r in conn.execute(
        "SELECT DISTINCT tag_value FROM paper_tags WHERE tag_type='gene'"
    ).fetchall()]
    species_tags = [r[0] for r in conn.execute(
        "SELECT DISTINCT tag_value FROM paper_tags WHERE tag_type='species'"
    ).fetchall()]
    conn.close()

    results = []
    topics  = [f"gene:{g}" for g in gene_tags] + [f"species:{s}" for s in species_tags]

    for topic_key in topics:
        try:
            kind, value = topic_key.split(":", 1)
            result = generate_summary(value)
            # 写入缓存（直接调用 lit_tools 的写缓存逻辑）
            _write_cache(topic_key, result)
            results.append({"topic": topic_key, "success": True,
                            "papers_cited": len(result["papers_cited"])})
        except Exception as e:
            results.append({"topic": topic_key, "success": False, "error": str(e)})

    return results


def _write_cache(cache_key: str, result: dict):
    """直接写摘要缓存（不经过 get_lit_summary 的读-写路径）。"""
    import json
    from datetime import datetime
    from tools.lit_tools import _get_summary_db
    conn = _get_summary_db()
    conn.execute(
        "INSERT OR REPLACE INTO lit_summary_cache "
        "(cache_key, summary, key_findings, paper_ids, generated_at, is_stale) "
        "VALUES (?, ?, ?, ?, ?, 0)",
        (
            cache_key,
            result["summary"],
            json.dumps(result["key_findings"], ensure_ascii=False),
            json.dumps(result["papers_cited"], ensure_ascii=False),
            datetime.now().isoformat(),
        )
    )
    conn.commit()
    conn.close()
