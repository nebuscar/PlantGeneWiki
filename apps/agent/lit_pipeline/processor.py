"""
PDF 处理器：PDF → 文本 → chunks → embeddings → Chroma

流程：
  upload_paper(pdf_path, metadata) → paper_id
  process_paper(paper_id)          → 异步，可后台执行
"""
from __future__ import annotations

import json
import re
import sqlite3
import uuid
from pathlib import Path

import fitz   # PyMuPDF
from sentence_transformers import SentenceTransformer

from config import PAPERS_DIR, CHROMA_DIR, EMBED_MODEL

CHUNK_SIZE    = 500    # token 近似（按字符 ÷ 4 估算）
CHUNK_OVERLAP = 50

PAPER_DB = Path(__file__).parent.parent / "db" / "papers.db"


# ── 论文元数据库 ─────────────────────────────────────────────────────────────

def _init_paper_db():
    conn = sqlite3.connect(str(PAPER_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS papers (
            paper_id   TEXT PRIMARY KEY,
            title      TEXT,
            authors    TEXT,         -- semicolon 分隔
            year       INTEGER,
            doi        TEXT,
            journal    TEXT,
            abstract   TEXT,
            file_path  TEXT,
            status     TEXT DEFAULT 'pending',
            uploaded_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS paper_tags (
            paper_id   TEXT,
            tag_type   TEXT,         -- gene / species / research_type / keyword
            tag_value  TEXT,
            confidence REAL,
            PRIMARY KEY (paper_id, tag_type, tag_value)
        )
    """)
    conn.commit()
    conn.close()


_init_paper_db()


def upload_paper(
    pdf_path: str | Path,
    title:    str = "",
    authors:  list[str] | None = None,
    year:     int | None = None,
    doi:      str = "",
    journal:  str = "",
    abstract: str = "",
) -> str:
    """注册文献到数据库，返回 paper_id。不立即处理，等待 process_paper()。"""
    paper_id = str(uuid.uuid4())
    dest     = PAPERS_DIR / f"{paper_id}.pdf"

    import shutil
    shutil.copy2(str(pdf_path), str(dest))

    conn = sqlite3.connect(str(PAPER_DB))
    conn.execute(
        "INSERT INTO papers (paper_id, title, authors, year, doi, journal, abstract, file_path, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')",
        (paper_id, title, ";".join(authors or []), year, doi, journal, abstract, str(dest))
    )
    conn.commit()
    conn.close()
    return paper_id


def process_paper(paper_id: str) -> dict:
    """
    处理单篇文献：提取文本 → 分块 → embedding → 存入 Chroma。
    返回处理状态。
    """
    conn = sqlite3.connect(str(PAPER_DB))
    row = conn.execute(
        "SELECT title, authors, year, doi, file_path, abstract FROM papers WHERE paper_id=?",
        (paper_id,)
    ).fetchone()
    conn.close()

    if not row:
        return {"success": False, "error": f"paper_id {paper_id} 不存在"}

    title, authors, year, doi, file_path, abstract = row

    # 1. 提取文本
    try:
        text = _extract_text(file_path)
    except Exception as e:
        _set_status(paper_id, "failed")
        return {"success": False, "error": f"PDF 提取失败：{e}"}

    # 2. 分块
    chunks = _chunk_text(text)
    if not chunks:
        _set_status(paper_id, "failed")
        return {"success": False, "error": "未能从 PDF 提取到文本"}

    # 3. Embedding + 存 Chroma
    try:
        _embed_and_store(paper_id, chunks, {
            "paper_id": paper_id,
            "title":    title or "",
            "authors":  authors or "",
            "year":     int(year) if year else 0,
            "doi":      doi or "",
        })
    except Exception as e:
        _set_status(paper_id, "failed")
        return {"success": False, "error": f"Embedding 失败：{e}"}

    _set_status(paper_id, "done")
    return {"success": True, "paper_id": paper_id, "chunk_count": len(chunks)}


def _extract_text(file_path: str) -> str:
    """用 PyMuPDF 提取 PDF 文本，合并所有页面。"""
    doc  = fitz.open(file_path)
    pages = [page.get_text("text") for page in doc]
    doc.close()
    return "\n".join(pages)


def _chunk_text(text: str) -> list[str]:
    """按段落拆分，再按 CHUNK_SIZE 合并，保留 CHUNK_OVERLAP 字符重叠。"""
    paragraphs = [p.strip() for p in re.split(r'\n{2,}', text) if p.strip()]
    chunks, current, current_len = [], [], 0
    char_limit = CHUNK_SIZE * 4   # 约 500 token → 2000 字符

    for para in paragraphs:
        para_len = len(para)
        if current_len + para_len > char_limit and current:
            chunks.append(" ".join(current))
            # 保留最后一段作重叠
            overlap_para = current[-1] if current else ""
            current = [overlap_para] if overlap_para else []
            current_len = len(overlap_para)
        current.append(para)
        current_len += para_len

    if current:
        chunks.append(" ".join(current))

    return chunks


def _embed_and_store(paper_id: str, chunks: list[str], meta: dict):
    """生成 embedding 并存入 Chroma。"""
    import chromadb
    client     = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_or_create_collection(
        name="literature",
        metadata={"hnsw:space": "cosine"},
    )

    model      = SentenceTransformer(EMBED_MODEL)
    embeddings = model.encode(chunks, show_progress_bar=False).tolist()

    ids       = [f"{paper_id}_{i}" for i in range(len(chunks))]
    metadatas = [{**meta, "chunk_index": i} for i in range(len(chunks))]

    # 分批写入，避免单次太大
    batch_size = 50
    for i in range(0, len(chunks), batch_size):
        collection.add(
            ids        = ids[i:i+batch_size],
            documents  = chunks[i:i+batch_size],
            embeddings = embeddings[i:i+batch_size],
            metadatas  = metadatas[i:i+batch_size],
        )


def _set_status(paper_id: str, status: str):
    conn = sqlite3.connect(str(PAPER_DB))
    conn.execute("UPDATE papers SET status=? WHERE paper_id=?", (status, paper_id))
    conn.commit()
    conn.close()


def list_papers(status: str | None = None) -> list[dict]:
    """列出所有文献，可按 status 过滤。"""
    conn = sqlite3.connect(str(PAPER_DB))
    if status:
        rows = conn.execute(
            "SELECT paper_id, title, authors, year, doi, status, uploaded_at FROM papers WHERE status=?",
            (status,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT paper_id, title, authors, year, doi, status, uploaded_at FROM papers"
        ).fetchall()
    conn.close()
    return [
        {"paper_id": r[0], "title": r[1], "authors": r[2],
         "year": r[3], "doi": r[4], "status": r[5], "uploaded_at": r[6]}
        for r in rows
    ]


def delete_paper(paper_id: str) -> bool:
    """从 Chroma 和数据库中删除一篇文献。"""
    import chromadb
    try:
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        col    = client.get_or_create_collection("literature")
        # 删除该 paper 的所有 chunks
        existing = col.get(where={"paper_id": paper_id})
        if existing["ids"]:
            col.delete(ids=existing["ids"])
    except Exception:
        pass

    conn = sqlite3.connect(str(PAPER_DB))
    conn.execute("DELETE FROM paper_tags WHERE paper_id=?", (paper_id,))
    conn.execute("DELETE FROM papers WHERE paper_id=?", (paper_id,))
    conn.commit()
    conn.close()

    pdf = PAPERS_DIR / f"{paper_id}.pdf"
    if pdf.exists():
        pdf.unlink()
    return True
