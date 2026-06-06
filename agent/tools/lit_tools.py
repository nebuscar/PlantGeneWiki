"""
文献工具：search_literature / get_lit_summary

依赖 Chroma 向量库和 SQLite 摘要缓存。
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from config import CHROMA_DIR, SUMMARY_DB, EMBED_MODEL

# ── 单例初始化 ───────────────────────────────────────────────────────────────

_embed_model = None
_chroma_client = None
_collection = None


def _get_embed_model():
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer
        _embed_model = SentenceTransformer(EMBED_MODEL)
    return _embed_model


def _get_collection():
    global _chroma_client, _collection
    if _collection is None:
        import chromadb
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _collection = _chroma_client.get_or_create_collection(
            name="literature",
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def _get_summary_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(SUMMARY_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS lit_summary_cache (
            cache_key    TEXT PRIMARY KEY,
            summary      TEXT,
            key_findings TEXT,   -- JSON array
            paper_ids    TEXT,   -- JSON array
            generated_at TEXT,
            is_stale     INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    return conn


# ── 对外工具 ────────────────────────────────────────────────────────────────

def search_literature(
    query: str,
    filters: dict | None = None,
    top_k: int = 5,
) -> list[dict]:
    """
    向量语义检索已上传文献。

    filters 可包含：gene / species / year_from / year_to
    返回按相关度排序的段落列表，每条附带来源信息。
    """
    collection = _get_collection()
    if collection.count() == 0:
        return []

    model     = _get_embed_model()
    embedding = model.encode([query])[0].tolist()

    # 构建 Chroma where 条件
    where_clauses = []
    if filters:
        if filters.get("gene"):
            where_clauses.append({"genes": {"$contains": filters["gene"].upper()}})
        if filters.get("species"):
            where_clauses.append({"species": {"$contains": filters["species"]}})
        if filters.get("year_from"):
            where_clauses.append({"year": {"$gte": int(filters["year_from"])}})
        if filters.get("year_to"):
            where_clauses.append({"year": {"$lte": int(filters["year_to"])}})

    where = {"$and": where_clauses} if len(where_clauses) > 1 else \
            where_clauses[0]        if len(where_clauses) == 1 else None

    kwargs = dict(
        query_embeddings=[embedding],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )
    if where:
        kwargs["where"] = where

    results = collection.query(**kwargs)

    out = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        out.append({
            "content":   doc,
            "paper_id":  meta.get("paper_id", ""),
            "title":     meta.get("title", ""),
            "authors":   meta.get("authors", "").split(";"),
            "year":      meta.get("year"),
            "doi":       meta.get("doi", ""),
            "relevance": round(1 - float(dist), 4),   # cosine distance → similarity
        })
    return out


def get_lit_summary(
    topic: str,
    filters: dict | None = None,
) -> dict:
    """
    获取某主题的文献综述摘要，优先返回预生成缓存。

    缓存 miss 时实时生成（由 summarizer 模块处理），结果写入缓存。
    """
    cache_key = _make_cache_key(topic, filters)
    conn = _get_summary_db()

    row = conn.execute(
        "SELECT summary, key_findings, paper_ids, generated_at, is_stale "
        "FROM lit_summary_cache WHERE cache_key = ?",
        (cache_key,)
    ).fetchone()

    if row and not row[4]:   # 有缓存且未失效
        conn.close()
        return {
            "summary":      row[0],
            "key_findings": json.loads(row[1]),
            "papers_cited": json.loads(row[2]),
            "cache_hit":    True,
            "generated_at": row[3],
        }

    # 缓存 miss 或已失效 → 实时生成
    conn.close()
    from lit_pipeline.summarizer import generate_summary
    result = generate_summary(topic, filters)

    # 写入缓存
    conn2 = _get_summary_db()
    conn2.execute(
        "INSERT OR REPLACE INTO lit_summary_cache "
        "(cache_key, summary, key_findings, paper_ids, generated_at, is_stale) "
        "VALUES (?, ?, ?, ?, ?, 0)",
        (
            cache_key,
            result["summary"],
            json.dumps(result["key_findings"],   ensure_ascii=False),
            json.dumps(result["papers_cited"],   ensure_ascii=False),
            datetime.now().isoformat(),
        )
    )
    conn2.commit()
    conn2.close()

    result["cache_hit"]    = False
    result["generated_at"] = datetime.now().isoformat()
    return result


def invalidate_summary_cache(tags: list[str]) -> int:
    """
    新文献上传后，按 tag 标记相关缓存失效。
    tags 通常是 gene 名 + 物种名。返回失效条目数。
    """
    conn = _get_summary_db()
    count = 0
    for tag in tags:
        cur = conn.execute(
            "UPDATE lit_summary_cache SET is_stale = 1 "
            "WHERE cache_key LIKE ?",
            (f"%{tag.lower()}%",)
        )
        count += cur.rowcount
    conn.commit()
    conn.close()
    return count


def _make_cache_key(topic: str, filters: dict | None) -> str:
    key = topic.lower().strip()
    if filters:
        for k in sorted(filters.keys()):
            key += f"|{k}:{filters[k]}"
    return key
