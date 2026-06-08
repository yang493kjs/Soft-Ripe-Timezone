# -*- coding: utf-8 -*-
"""
SQLite 数据库模块 — 替代 messages.json / agents.json / monologues.json
"""
import os
import sqlite3
import json
import threading
from datetime import datetime
from typing import Optional, List, Dict

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "app.db")

# 线程本地存储，每个线程独立连接
_local = threading.local()

def get_conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
    return _local.conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            content TEXT NOT NULL,
            sender_id TEXT NOT NULL CHECK(sender_id IN ('user', 'ai')),
            timestamp TEXT NOT NULL,
            date TEXT NOT NULL DEFAULT '',
            status TEXT DEFAULT 'read',
            extra TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_messages_agent_time ON messages(agent_id, created_at);

        CREATE TABLE IF NOT EXISTS agents (
            agent_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            persona_id TEXT NOT NULL,
            persona_name TEXT DEFAULT '',
            system_prompt TEXT DEFAULT '',
            phase TEXT DEFAULT 'acquaintance',
            intimacy REAL DEFAULT 10,
            passion REAL DEFAULT 5,
            commitment REAL DEFAULT 5,
            relationship_days INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_agents_user_persona ON agents(user_id, persona_id);

        CREATE TABLE IF NOT EXISTS monologues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            data_json TEXT NOT NULL,
            timestamp TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_monologues_agent ON monologues(agent_id, id DESC);
    """)
    conn.commit()


# ===================== Messages =====================

def load_messages(agent_id: str) -> list:
    """返回前端兼容的消息列表"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM messages WHERE agent_id=? ORDER BY created_at ASC",
        (agent_id,)
    ).fetchall()
    result = []
    for r in rows:
        msg = {
            "_id": r["id"],
            "content": r["content"],
            "senderId": r["sender_id"],
            "timestamp": r["timestamp"],
            "date": r["date"],
            "status": r["status"],
        }
        extra = json.loads(r["extra"] or "{}")
        if extra:
            msg.update(extra)
        result.append(msg)
    return result


def load_messages_paginated(agent_id: str, limit: int = 50, before_id: str = None) -> list:
    """分页加载消息，返回前端兼容格式"""
    conn = get_conn()
    if before_id:
        rows = conn.execute(
            """SELECT * FROM messages WHERE agent_id=? AND created_at < (
                SELECT created_at FROM messages WHERE id=?
            ) ORDER BY created_at ASC LIMIT ?""",
            (agent_id, before_id, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM messages WHERE agent_id=? ORDER BY created_at ASC LIMIT ?",
            (agent_id, limit)
        ).fetchall()
    result = []
    for r in rows:
        msg = {
            "_id": r["id"],
            "content": r["content"],
            "senderId": r["sender_id"],
            "timestamp": r["timestamp"],
            "date": r["date"],
            "status": r["status"],
        }
        extra = json.loads(r["extra"] or "{}")
        if extra:
            msg.update(extra)
        result.append(msg)
    return result


def save_message(agent_id: str, msg: dict):
    """追加单条消息"""
    conn = get_conn()
    extra = {}
    for k in list(msg.keys()):
        if k not in ("_id", "content", "senderId", "timestamp", "date", "status"):
            extra[k] = msg[k]
    conn.execute(
        """INSERT INTO messages (id, agent_id, content, sender_id, timestamp, date, status, extra)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            msg.get("_id", ""),
            agent_id,
            msg.get("content", ""),
            msg.get("senderId", ""),
            msg.get("timestamp", ""),
            msg.get("date", ""),
            msg.get("status", "read"),
            json.dumps(extra, ensure_ascii=False)
        )
    )
    conn.commit()


def clear_messages(agent_id: str):
    conn = get_conn()
    conn.execute("DELETE FROM messages WHERE agent_id=?", (agent_id,))
    conn.commit()


def get_message_count(agent_id: str) -> int:
    conn = get_conn()
    row = conn.execute("SELECT COUNT(*) as cnt FROM messages WHERE agent_id=?", (agent_id,)).fetchone()
    return row["cnt"] if row else 0


def get_last_n_messages(agent_id: str, n: int = 20) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT content, sender_id FROM messages WHERE agent_id=? ORDER BY created_at DESC LIMIT ?",
        (agent_id, n)
    ).fetchall()
    return [{"role": "user" if r["sender_id"] == "user" else "assistant", "content": r["content"]} for r in reversed(rows)]


# ===================== Agents =====================

def load_agents() -> dict:
    """返回 {key: agent_dict} 格式，兼容旧接口"""
    conn = get_conn()
    rows = conn.execute("SELECT * FROM agents").fetchall()
    result = {}
    for r in rows:
        key = f"{r['user_id']}_{r['persona_id']}"
        result[key] = {
            "agent_id": r["agent_id"],
            "user_id": r["user_id"],
            "persona_id": r["persona_id"],
            "persona_name": r["persona_name"],
            "system_prompt": r["system_prompt"],
            "created_at": r["created_at"],
            "relationship_days": r["relationship_days"],
            "phase": r["phase"],
            "intimacy": r["intimacy"],
            "passion": r["passion"],
            "commitment": r["commitment"],
        }
    return result


def save_agent(agent: dict):
    """插入或更新 agent"""
    conn = get_conn()
    conn.execute(
        """INSERT INTO agents (agent_id, user_id, persona_id, persona_name, system_prompt,
           phase, intimacy, passion, commitment, relationship_days, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(agent_id) DO UPDATE SET
           persona_name=excluded.persona_name,
           system_prompt=excluded.system_prompt,
           phase=excluded.phase,
           intimacy=excluded.intimacy,
           passion=excluded.passion,
           commitment=excluded.commitment,
           relationship_days=excluded.relationship_days""",
        (
            agent.get("agent_id", ""),
            agent.get("user_id", ""),
            agent.get("persona_id", ""),
            agent.get("persona_name", ""),
            agent.get("system_prompt", ""),
            agent.get("phase", "acquaintance"),
            agent.get("intimacy", 10),
            agent.get("passion", 5),
            agent.get("commitment", 5),
            agent.get("relationship_days", 1),
            agent.get("created_at", datetime.now().isoformat()),
        )
    )
    conn.commit()


def insert_agent(agent: dict):
    """插入新 agent（不更新已有）"""
    conn = get_conn()
    conn.execute(
        """INSERT OR IGNORE INTO agents (agent_id, user_id, persona_id, persona_name, system_prompt,
           phase, intimacy, passion, commitment, relationship_days, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            agent.get("agent_id", ""),
            agent.get("user_id", ""),
            agent.get("persona_id", ""),
            agent.get("persona_name", ""),
            agent.get("system_prompt", ""),
            agent.get("phase", "acquaintance"),
            agent.get("intimacy", 10),
            agent.get("passion", 5),
            agent.get("commitment", 5),
            agent.get("relationship_days", 1),
            agent.get("created_at", datetime.now().isoformat()),
        )
    )
    conn.commit()


def delete_agent_from_db(agent_id: str):
    conn = get_conn()
    conn.execute("DELETE FROM agents WHERE agent_id=?", (agent_id,))
    conn.commit()


# ===================== Monologues =====================

def load_monologues(agent_id: str) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT data_json FROM monologues WHERE agent_id=? ORDER BY id DESC LIMIT 100",
        (agent_id,)
    ).fetchall()
    return [json.loads(r["data_json"]) for r in reversed(rows)]


def save_monologue(agent_id: str, entry: dict):
    conn = get_conn()
    entry["timestamp"] = datetime.now().isoformat()
    conn.execute(
        "INSERT INTO monologues (agent_id, data_json, timestamp) VALUES (?, ?, ?)",
        (agent_id, json.dumps(entry, ensure_ascii=False), entry["timestamp"])
    )
    conn.commit()

    # 保持最多 100 条
    conn.execute("""
        DELETE FROM monologues WHERE agent_id=? AND id NOT IN (
            SELECT id FROM monologues WHERE agent_id=? ORDER BY id DESC LIMIT 100
        )
    """, (agent_id, agent_id))
    conn.commit()


def get_latest_monologue(agent_id: str) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute(
        "SELECT data_json FROM monologues WHERE agent_id=? ORDER BY id DESC LIMIT 1",
        (agent_id,)
    ).fetchone()
    return json.loads(row["data_json"]) if row else None


def get_monologue_history(agent_id: str, limit: int = 10) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT data_json FROM monologues WHERE agent_id=? ORDER BY id DESC LIMIT ?",
        (agent_id, limit)
    ).fetchall()
    return [json.loads(r["data_json"]) for r in reversed(rows)]


def clear_monologues(agent_id: str):
    conn = get_conn()
    conn.execute("DELETE FROM monologues WHERE agent_id=?", (agent_id,))
    conn.commit()