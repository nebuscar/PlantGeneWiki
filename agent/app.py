"""
Chainlit 聊天入口

认证：自定义用户名/密码（用户信息存 SQLite）
会话记忆：Chainlit user_session + SQLite 持久化
API Key：用户可在设置面板中自行输入，优先于服务器环境变量
"""
from __future__ import annotations

import hashlib
import os
import sqlite3
from pathlib import Path

import chainlit as cl
from chainlit.input_widget import Select, TextInput

import orchestrator
import skills as _skills_registry
from config import SESSION_DB, SESSION_WINDOW
from db.data_layer import SQLiteDataLayer, load_api_settings, save_api_settings


@cl.data_layer
def _get_data_layer() -> SQLiteDataLayer:
    return SQLiteDataLayer()

# ── 用户数据库 ────────────────────────────────────────────────────────────────

USER_DB = Path(__file__).parent / "db" / "users.db"


def _init_user_db():
    conn = sqlite3.connect(str(USER_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username      TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            role          TEXT NOT NULL DEFAULT 'user',
            created_at    TEXT DEFAULT (datetime('now'))
        )
    """)
    admin_hash = hashlib.sha256("admin123".encode()).hexdigest()
    conn.execute(
        "INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)",
        ("admin", admin_hash, "admin"),
    )
    guest_hash = hashlib.sha256("guest".encode()).hexdigest()
    conn.execute(
        "INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)",
        ("guest", guest_hash, "guest"),
    )
    conn.commit()
    conn.close()


def _check_user(username: str, password: str) -> dict | None:
    conn = sqlite3.connect(str(USER_DB))
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    row = conn.execute(
        "SELECT username, role FROM users WHERE username=? AND password_hash=?",
        (username, pw_hash),
    ).fetchone()
    conn.close()
    return {"username": row[0], "role": row[1]} if row else None


_init_user_db()


# ── 会话历史 ──────────────────────────────────────────────────────────────────

def _init_session_db():
    conn = sqlite3.connect(str(SESSION_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role       TEXT NOT NULL,
            content    TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()


def _save_message(session_id: str, role: str, content: str):
    conn = sqlite3.connect(str(SESSION_DB))
    conn.execute(
        "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
        (session_id, role, content),
    )
    conn.commit()
    conn.close()


def _load_history(session_id: str) -> list[dict]:
    conn = sqlite3.connect(str(SESSION_DB))
    rows = conn.execute(
        "SELECT role, content FROM messages WHERE session_id=? "
        "ORDER BY created_at DESC LIMIT ?",
        (session_id, SESSION_WINDOW),
    ).fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]


_init_session_db()


# ── 认证 ──────────────────────────────────────────────────────────────────────

@cl.set_starters
async def set_starters() -> list[cl.Starter]:
    return _skills_registry.get_starters()


@cl.password_auth_callback
def auth_callback(username: str, password: str) -> cl.User | None:
    user_info = _check_user(username, password)
    if user_info:
        return cl.User(
            identifier=username,
            metadata={"role": user_info["role"]},
        )
    return None


# ── 会话启动 ──────────────────────────────────────────────────────────────────

@cl.on_chat_start
async def on_start():
    user = cl.user_session.get("user")
    username = user.identifier if user else "guest"
    role = user.metadata.get("role", "guest") if user else "guest"
    cl.user_session.set("role", role)
    cl.user_session.set("query_count", 0)

    # 服务器配置的 key（可为空）
    server_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    has_server_key = bool(server_key) and not server_key.startswith("placeholder")

    # 从数据库加载已保存的 API 设置
    saved = load_api_settings(username)
    cl.user_session.set("api_key",  saved["api_key"]  or None)
    cl.user_session.set("base_url", saved["base_url"] or None)
    cl.user_session.set("model",    saved["model"]    or None)
    cl.user_session.set("mode",     saved["mode"]     or "anthropic")

    # 设置面板：填入已保存的值作为初始值
    saved_mode    = saved["mode"]     or "anthropic"
    saved_key     = saved["api_key"]  or ""
    saved_url     = saved["base_url"] or ""
    saved_model   = saved["model"]    or ""

    await cl.ChatSettings(
        [
            Select(
                id="api_mode",
                label="API 类型",
                values=["anthropic", "openai"],
                initial_index=1 if saved_mode == "openai" else 0,
                description=(
                    "anthropic：官方 Claude API 或兼容代理（默认）。"
                    "openai：OpenAI 兼容接口（OpenRouter、本地模型等）。"
                ),
            ),
            TextInput(
                id="api_base_url",
                label="API Base URL",
                placeholder="留空使用官方地址，如 https://openrouter.ai/api/v1",
                description="自定义 API 端点，留空使用官方默认地址。",
                initial=saved_url,
            ),
            TextInput(
                id="api_key",
                label="API Key",
                placeholder="sk-ant-..." if not has_server_key else "（服务器已配置，可留空）",
                description="你的 API Key。留空时使用服务器配置的 Key。",
                initial=saved_key,
            ),
            TextInput(
                id="model_name",
                label="模型名称",
                placeholder="claude-sonnet-4-6",
                description=(
                    "Anthropic 模式：claude-sonnet-4-6 / claude-opus-4-7 等。"
                    "OpenAI 模式：gpt-4o / anthropic/claude-3-5-sonnet 等。"
                ),
                initial=saved_model,
            ),
        ]
    ).send()

    role_label = {"admin": "管理员", "user": "注册用户", "guest": "游客"}.get(role, "游客")
    has_user_key = bool(saved_key)
    if has_server_key:
        key_status = "✅ 服务器已配置 API Key"
    elif has_user_key:
        key_status = "✅ 已使用上次保存的 API Key"
    else:
        key_status = "⚠️ 请在右上角 ⚙️ 设置中填入 API Key"

    await cl.Message(
        content=(
            f"你好！我是 **PlantsDB AI 助手**，当前身份：{role_label}\n\n"
            f"{key_status}\n\n"
            "可以问我：\n"
            "- 某个基因的功能注释、蛋白性质、同源基因\n"
            "- 特定物种中含某结构域的基因家族\n"
            "- 基因在各组织的表达模式\n"
            "- 一批基因的 GO/KEGG 富集分析\n"
            "- 已上传文献中的研究结论\n\n"
            + ("⚠️ 游客每日限 10 次查询，登录后无限制。\n" if role == "guest" else "")
        )
    ).send()


@cl.on_settings_update
async def on_settings_update(settings: dict):
    """用户在设置面板修改 API 配置时触发。"""
    api_key  = (settings.get("api_key")      or "").strip() or None
    base_url = (settings.get("api_base_url") or "").strip() or None
    model    = (settings.get("model_name")   or "").strip() or None
    mode     = (settings.get("api_mode")     or "anthropic").strip()

    cl.user_session.set("api_key",  api_key)
    cl.user_session.set("base_url", base_url)
    cl.user_session.set("model",    model)
    cl.user_session.set("mode",     mode)

    # 持久化到数据库
    user = cl.user_session.get("user")
    if user:
        save_api_settings(user.identifier, mode, api_key or "", base_url or "", model or "")

    parts = [f"API 类型：{mode}"]
    if base_url:
        parts.append(f"Base URL：{base_url}")
    if model:
        parts.append(f"模型：{model}")
    parts.append("API Key：" + ("已设置" if api_key else "使用服务器配置"))

    await cl.Message(content="✅ API 配置已更新\n" + "\n".join(f"  • {p}" for p in parts)).send()


# ── 消息处理 ──────────────────────────────────────────────────────────────────

@cl.on_message
async def on_message(message: cl.Message):
    role       = cl.user_session.get("role", "guest")
    session_id = cl.user_session.get("id", "anon")

    # 确定本次使用的 API 配置（用户输入 > 服务器环境变量）
    server_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    api_key    = cl.user_session.get("api_key") or (
                     server_key if server_key and not server_key.startswith("placeholder") else None
                 )
    base_url   = cl.user_session.get("base_url") or None
    model      = cl.user_session.get("model")    or None
    mode       = cl.user_session.get("mode")     or "anthropic"

    if not api_key:
        await cl.Message(
            content=(
                "❌ 未配置 API Key。\n\n"
                "请点击右上角 **⚙️** 图标，在设置面板中填入：\n"
                "  • **API 类型**（Anthropic 或 OpenAI 兼容）\n"
                "  • **API Key**\n"
                "  • **模型名称**（可选，留空用默认）\n"
                "  • **Base URL**（使用自定义端点时填写）"
            )
        ).send()
        return

    # guest 限流
    if role == "guest":
        count = cl.user_session.get("query_count", 0)
        if count >= 10:
            await cl.Message(content="游客每日查询限额已用完，请登录后继续使用。").send()
            return
        cl.user_session.set("query_count", count + 1)

    # 加载会话历史
    if role != "guest":
        history = _load_history(session_id)
        _save_message(session_id, "user", message.content)
    else:
        history = cl.user_session.get("history", [])

    # 流式回复
    reply_msg  = cl.Message(content="")
    await reply_msg.send()

    full_reply = ""
    async for chunk in orchestrator.run(
        message.content, history, role,
        api_key=api_key, model=model, base_url=base_url, mode=mode,
    ):
        full_reply += chunk
        await reply_msg.stream_token(chunk)

    await reply_msg.update()

    # 保存历史
    if role != "guest":
        _save_message(session_id, "assistant", full_reply)
    else:
        history = history + [
            {"role": "user",      "content": message.content},
            {"role": "assistant", "content": full_reply},
        ]
        cl.user_session.set("history", history[-SESSION_WINDOW:])


# ── 会话恢复 ──────────────────────────────────────────────────────────────────

@cl.on_chat_resume
async def on_resume(thread: dict):
    """用户打开历史会话时触发，恢复角色与 API 配置。"""
    user = cl.user_session.get("user")
    username = user.identifier if user else "guest"
    role = user.metadata.get("role", "guest") if user else "guest"
    cl.user_session.set("role", role)
    cl.user_session.set("query_count", 0)

    saved = load_api_settings(username)
    cl.user_session.set("api_key",  saved["api_key"]  or None)
    cl.user_session.set("base_url", saved["base_url"] or None)
    cl.user_session.set("model",    saved["model"]    or None)
    cl.user_session.set("mode",     saved["mode"]     or "anthropic")
