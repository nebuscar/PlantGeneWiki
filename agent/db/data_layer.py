"""
SQLite 自定义数据层：实现 Chainlit BaseDataLayer 接口

负责：
  - 会话（Thread）持久化与列表
  - 消息/步骤（Step）持久化
  - 用户持久化
  - API 设置持久化（per user）
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from chainlit.data.base import BaseDataLayer
from chainlit.types import (
    Feedback, PageInfo, PaginatedResponse, Pagination,
    ThreadDict, ThreadFilter,
)
from chainlit.user import PersistedUser, User

if TYPE_CHECKING:
    from chainlit.step import StepDict

DB_PATH = Path(__file__).parent / "chainlit.db"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS cl_users (
            id           TEXT PRIMARY KEY,
            identifier   TEXT UNIQUE NOT NULL,
            display_name TEXT,
            metadata     TEXT DEFAULT '{}',
            created_at   TEXT
        );

        CREATE TABLE IF NOT EXISTS threads (
            id              TEXT PRIMARY KEY,
            created_at      TEXT,
            name            TEXT,
            user_id         TEXT,
            user_identifier TEXT,
            metadata        TEXT DEFAULT '{}',
            tags            TEXT DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS steps (
            id           TEXT PRIMARY KEY,
            thread_id    TEXT NOT NULL,
            parent_id    TEXT,
            type         TEXT,
            name         TEXT,
            input        TEXT,
            output       TEXT,
            metadata     TEXT DEFAULT '{}',
            tags         TEXT DEFAULT '[]',
            created_at   TEXT,
            start_time   TEXT,
            end_time     TEXT,
            is_error     INTEGER DEFAULT 0,
            FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_steps_thread ON steps(thread_id);

        CREATE TABLE IF NOT EXISTS api_settings (
            username   TEXT PRIMARY KEY,
            api_mode   TEXT DEFAULT 'anthropic',
            api_key    TEXT DEFAULT '',
            base_url   TEXT DEFAULT '',
            model      TEXT DEFAULT '',
            updated_at TEXT
        );
    """)
    conn.commit()
    conn.close()


init_db()


# ── API 设置（独立于 Chainlit 数据层，供 app.py 直接调用）────────────────────

def save_api_settings(username: str, mode: str, api_key: str, base_url: str, model: str):
    conn = _conn()
    conn.execute("""
        INSERT INTO api_settings (username, api_mode, api_key, base_url, model, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(username) DO UPDATE SET
            api_mode=excluded.api_mode, api_key=excluded.api_key,
            base_url=excluded.base_url, model=excluded.model,
            updated_at=excluded.updated_at
    """, (username, mode, api_key, base_url, model, _now()))
    conn.commit()
    conn.close()


def load_api_settings(username: str) -> dict:
    conn = _conn()
    row = conn.execute(
        "SELECT api_mode, api_key, base_url, model FROM api_settings WHERE username=?",
        (username,)
    ).fetchone()
    conn.close()
    if row:
        return {"mode": row["api_mode"], "api_key": row["api_key"],
                "base_url": row["base_url"], "model": row["model"]}
    return {"mode": "anthropic", "api_key": "", "base_url": "", "model": ""}


# ── Chainlit 数据层实现 ───────────────────────────────────────────────────────

class SQLiteDataLayer(BaseDataLayer):

    # ── 用户 ──────────────────────────────────────────────────────────────────

    async def get_user(self, identifier: str) -> Optional[PersistedUser]:
        conn = _conn()
        row = conn.execute(
            "SELECT id, identifier, display_name, metadata, created_at FROM cl_users WHERE identifier=?",
            (identifier,)
        ).fetchone()
        conn.close()
        if not row:
            return None
        return PersistedUser(
            id           = row["id"],
            createdAt    = row["created_at"],
            identifier   = row["identifier"],
            display_name = row["display_name"],
            metadata     = json.loads(row["metadata"] or "{}"),
        )

    async def create_user(self, user: User) -> Optional[PersistedUser]:
        uid = str(uuid.uuid4())
        now = _now()
        conn = _conn()
        conn.execute("""
            INSERT OR IGNORE INTO cl_users (id, identifier, display_name, metadata, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (uid, user.identifier, user.display_name,
              json.dumps(user.metadata or {}), now))
        conn.commit()
        # 若已存在，返回已有记录
        row = conn.execute(
            "SELECT id, created_at FROM cl_users WHERE identifier=?",
            (user.identifier,)
        ).fetchone()
        conn.close()
        return PersistedUser(
            id=row["id"], createdAt=row["created_at"],
            identifier=user.identifier, display_name=user.display_name,
            metadata=user.metadata or {},
        )

    # ── 线程（会话）──────────────────────────────────────────────────────────

    async def update_thread(
        self, thread_id: str,
        name: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
    ):
        conn = _conn()

        # 通过 user_id (UUID) 查出 identifier（用户名），供展示用
        user_identifier = None
        if user_id:
            row = conn.execute(
                "SELECT identifier FROM cl_users WHERE id=?", (user_id,)
            ).fetchone()
            if row:
                user_identifier = row["identifier"]

        conn.execute("""
            INSERT OR IGNORE INTO threads
                (id, created_at, name, user_id, user_identifier, metadata, tags)
            VALUES (?, ?, ?, ?, ?, '{}', '[]')
        """, (thread_id, _now(), name or "新对话", user_id or "",
              user_identifier or ""))

        updates, params = [], []
        if name            is not None: updates.append("name=?");            params.append(name)
        if user_id         is not None: updates.append("user_id=?");         params.append(user_id)
        if user_identifier is not None: updates.append("user_identifier=?"); params.append(user_identifier)
        if metadata        is not None: updates.append("metadata=?");        params.append(json.dumps(metadata))
        if tags            is not None: updates.append("tags=?");            params.append(json.dumps(tags))

        if updates:
            params.append(thread_id)
            conn.execute(f"UPDATE threads SET {', '.join(updates)} WHERE id=?", params)
        conn.commit()
        conn.close()

    async def get_thread(self, thread_id: str) -> Optional[ThreadDict]:
        conn = _conn()
        row = conn.execute(
            "SELECT * FROM threads WHERE id=?", (thread_id,)
        ).fetchone()
        if not row:
            conn.close()
            return None

        steps = conn.execute(
            "SELECT * FROM steps WHERE thread_id=? ORDER BY created_at ASC",
            (thread_id,)
        ).fetchall()
        conn.close()

        return {
            "id":             row["id"],
            "createdAt":      row["created_at"],
            "name":           row["name"] or "对话",
            "userId":         row["user_id"],
            "userIdentifier": row["user_identifier"],
            "tags":           json.loads(row["tags"] or "[]"),
            "metadata":       json.loads(row["metadata"] or "{}"),
            "steps":          [_row_to_step(s) for s in steps],
            "elements":       [],
        }

    async def get_thread_author(self, thread_id: str) -> str:
        conn = _conn()
        row = conn.execute(
            "SELECT user_identifier FROM threads WHERE id=?", (thread_id,)
        ).fetchone()
        conn.close()
        return (row["user_identifier"] or "") if row else ""

    async def delete_thread(self, thread_id: str):
        conn = _conn()
        conn.execute("DELETE FROM steps   WHERE thread_id=?", (thread_id,))
        conn.execute("DELETE FROM threads WHERE id=?",        (thread_id,))
        conn.commit()
        conn.close()

    async def list_threads(
        self, pagination: Pagination, filters: ThreadFilter
    ) -> PaginatedResponse[ThreadDict]:
        conn = _conn()
        conditions, params = ["1=1"], []

        if filters.userId:
            conditions.append("user_id=?"); params.append(filters.userId)
        if filters.search:
            conditions.append("name LIKE ?"); params.append(f"%{filters.search}%")

        where = " AND ".join(conditions)

        # cursor 分页（按 created_at 倒序）
        if pagination.cursor:
            conditions.append("created_at < (SELECT created_at FROM threads WHERE id=?)")
            params.append(pagination.cursor)
            where = " AND ".join(conditions)

        limit = pagination.first or 20
        rows  = conn.execute(
            f"SELECT * FROM threads WHERE {where} ORDER BY created_at DESC LIMIT ?",
            params + [limit + 1]
        ).fetchall()
        conn.close()

        has_next  = len(rows) > limit
        rows      = rows[:limit]
        threads   = [
            ThreadDict(
                id=r["id"], createdAt=r["created_at"], name=r["name"] or "对话",
                userId=r["user_id"], userIdentifier=r["user_identifier"],
                tags=json.loads(r["tags"] or "[]"),
                metadata=json.loads(r["metadata"] or "{}"),
                steps=[], elements=[],
            )
            for r in rows
        ]
        end_cursor = rows[-1]["id"] if rows else None
        return PaginatedResponse(
            data     = threads,
            pageInfo = PageInfo(hasNextPage=has_next, startCursor=None, endCursor=end_cursor),
        )

    # ── 步骤（消息）──────────────────────────────────────────────────────────

    async def create_step(self, step_dict: "StepDict"):
        conn = _conn()
        conn.execute("""
            INSERT OR REPLACE INTO steps
            (id, thread_id, parent_id, type, name, input, output,
             metadata, tags, created_at, start_time, end_time, is_error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            step_dict.get("id",       str(uuid.uuid4())),
            step_dict.get("threadId", ""),
            step_dict.get("parentId"),
            step_dict.get("type",     ""),
            step_dict.get("name",     ""),
            step_dict.get("input",    ""),
            step_dict.get("output",   ""),
            json.dumps(step_dict.get("metadata", {})),
            json.dumps(step_dict.get("tags",     [])),
            step_dict.get("createdAt", _now()),
            step_dict.get("start"),
            step_dict.get("end"),
            int(step_dict.get("isError", False)),
        ))
        conn.commit()
        conn.close()

    async def update_step(self, step_dict: "StepDict"):
        await self.create_step(step_dict)   # REPLACE 语义相同

    async def delete_step(self, step_id: str):
        conn = _conn()
        conn.execute("DELETE FROM steps WHERE id=?", (step_id,))
        conn.commit()
        conn.close()

    # ── 元素（忽略，暂不支持附件）────────────────────────────────────────────

    async def create_element(self, element_for_db: Any): pass
    async def get_element(self, thread_id: str, element_id: str): return None
    async def delete_element(self, element_id: str, thread_id: Optional[str] = None): pass

    # ── 反馈（忽略）──────────────────────────────────────────────────────────

    async def upsert_feedback(self, feedback: Feedback) -> str: return ""
    async def delete_feedback(self, feedback_id: str): pass

    # ── 其他 ──────────────────────────────────────────────────────────────────

    async def get_favorite_steps(self): return []
    async def set_step_favorite(self, step_id: str, is_favorite: bool): pass
    async def build_debug_url(self) -> Optional[str]: return None
    async def close(self): pass


def _row_to_step(row: sqlite3.Row) -> "StepDict":
    return {
        "id":        row["id"],
        "threadId":  row["thread_id"],
        "parentId":  row["parent_id"],
        "type":      row["type"]  or "run",
        "name":      row["name"]  or "",
        "input":     row["input"] or "",
        "output":    row["output"] or "",
        "metadata":  json.loads(row["metadata"] or "{}"),
        "tags":      json.loads(row["tags"]     or "[]"),
        "createdAt": row["created_at"],
        "start":     row["start_time"],
        "end":       row["end_time"],
        "isError":   bool(row["is_error"]),
    }
