from __future__ import annotations

import json
import math
import sqlite3
import time
from pathlib import Path
from typing import Optional

from meminumb.result import MemoryItem

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    id         TEXT PRIMARY KEY,
    content    TEXT NOT NULL,
    metadata   TEXT NOT NULL DEFAULT '{}',
    embedding  TEXT NOT NULL DEFAULT '[]',
    created_at REAL NOT NULL,
    expires_at REAL
);
"""

# Active-row filter: row has no TTL, or its TTL has not passed yet.
_ACTIVE = "(expires_at IS NULL OR expires_at > ?)"


class SQLiteStore:
    """
    SQLite-backed memory store.

    All writes use a context-manager transaction so a partial failure
    (e.g. a constraint violation mid-write) automatically rolls back,
    leaving no orphaned rows.
    """

    def __init__(self, path: str = ":memory:") -> None:
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(_SCHEMA)
        self._migrate()
        self._conn.commit()

    def _migrate(self) -> None:
        """Add expires_at column to existing databases that pre-date TTL support."""
        try:
            self._conn.execute("ALTER TABLE memories ADD COLUMN expires_at REAL")
        except sqlite3.OperationalError:
            pass  # column already exists

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def add_atomic(
        self,
        item: MemoryItem,
        embedding: list[float],
        expires_at: Optional[float] = None,
    ) -> None:
        """
        Write a memory and its embedding in one atomic transaction.

        If an expired row with the same ID exists it is replaced.
        If anything fails (constraint error, disk full, …) the connection's
        context manager rolls back automatically — no orphan is left behind.
        """
        now = time.time()
        with self._conn:
            # Remove any same-ID row that has already expired so the INSERT below
            # can succeed. If the same-ID row is still active, this DELETE is a
            # no-op and the INSERT will raise a constraint error (correct).
            self._conn.execute(
                "DELETE FROM memories WHERE id = ? AND expires_at IS NOT NULL AND expires_at <= ?",
                (item.id, now),
            )
            self._conn.execute(
                "INSERT INTO memories (id, content, metadata, embedding, created_at, expires_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    item.id,
                    item.content,
                    json.dumps(item.metadata),
                    json.dumps(embedding),
                    now,
                    expires_at,
                ),
            )

    def update_atomic(
        self,
        memory_id: str,
        content: Optional[str],
        embedding: Optional[list[float]],
        metadata: Optional[dict],
    ) -> bool:
        """
        Update content, embedding, and/or metadata for an existing memory.

        Returns False if the memory_id does not exist, True on success.
        The update is atomic — a failure leaves the original row unchanged.
        """
        existing = self.get(memory_id)
        if existing is None:
            return False

        new_content = content if content is not None else existing.content
        new_embedding = embedding if embedding is not None else json.loads(
            self._conn.execute(
                "SELECT embedding FROM memories WHERE id = ?", (memory_id,)
            ).fetchone()[0]
        )
        new_metadata = {**existing.metadata, **(metadata or {})}

        with self._conn:
            self._conn.execute(
                "UPDATE memories SET content = ?, embedding = ?, metadata = ? WHERE id = ?",
                (new_content, json.dumps(new_embedding), json.dumps(new_metadata), memory_id),
            )
        return True

    def delete(self, memory_id: str) -> bool:
        with self._conn:
            cur = self._conn.execute(
                "DELETE FROM memories WHERE id = ?", (memory_id,)
            )
        return cur.rowcount > 0

    def clear(self, user_id: Optional[str] = None) -> int:
        with self._conn:
            if user_id:
                cur = self._conn.execute(
                    "DELETE FROM memories WHERE json_extract(metadata, '$.user_id') = ?",
                    (user_id,),
                )
            else:
                cur = self._conn.execute("DELETE FROM memories")
        return cur.rowcount

    def clear_expired(self) -> int:
        """Delete all rows whose TTL has passed. Returns the number of rows removed."""
        with self._conn:
            cur = self._conn.execute(
                "DELETE FROM memories WHERE expires_at IS NOT NULL AND expires_at <= ?",
                (time.time(),),
            )
        return cur.rowcount

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def exists(self, memory_id: str) -> bool:
        cur = self._conn.execute(
            f"SELECT 1 FROM memories WHERE id = ? AND {_ACTIVE}",
            (memory_id, time.time()),
        )
        return cur.fetchone() is not None

    def get(self, memory_id: str) -> Optional[MemoryItem]:
        cur = self._conn.execute(
            f"SELECT id, content, metadata, expires_at FROM memories "
            f"WHERE id = ? AND {_ACTIVE}",
            (memory_id, time.time()),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return MemoryItem(id=row[0], content=row[1], metadata=json.loads(row[2]), expires_at=row[3])

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> list[MemoryItem]:
        """Return top_k memories ranked by cosine similarity to query_embedding."""
        now = time.time()
        where, params = _scope_filter(user_id, agent_id, now)
        cur = self._conn.execute(
            f"SELECT id, content, metadata, embedding, expires_at FROM memories WHERE {where}",
            params,
        )
        rows = cur.fetchall()
        if not rows:
            return []

        scored = []
        for row_id, content, metadata_json, embedding_json, expires_at in rows:
            emb = json.loads(embedding_json)
            score = _cosine(query_embedding, emb)
            scored.append((score, row_id, content, metadata_json, expires_at))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            MemoryItem(id=r[1], content=r[2], metadata=json.loads(r[3]), expires_at=r[4])
            for r in scored[:top_k]
        ]

    def all(
        self, user_id: Optional[str] = None, agent_id: Optional[str] = None
    ) -> list[MemoryItem]:
        now = time.time()
        where, params = _scope_filter(user_id, agent_id, now)
        cur = self._conn.execute(
            f"SELECT id, content, metadata, expires_at FROM memories WHERE {where}",
            params,
        )
        return [
            MemoryItem(id=r[0], content=r[1], metadata=json.loads(r[2]), expires_at=r[3])
            for r in cur.fetchall()
        ]

    def recent(
        self, n: int, user_id: Optional[str] = None, agent_id: Optional[str] = None
    ) -> list[MemoryItem]:
        """Return the n most recently added active memories, newest first."""
        now = time.time()
        where, params = _scope_filter(user_id, agent_id, now)
        cur = self._conn.execute(
            f"SELECT id, content, metadata, expires_at FROM memories "
            f"WHERE {where} ORDER BY created_at DESC LIMIT ?",
            (*params, n),
        )
        return [
            MemoryItem(id=r[0], content=r[1], metadata=json.loads(r[2]), expires_at=r[3])
            for r in cur.fetchall()
        ]

    def count(self, user_id: Optional[str] = None, agent_id: Optional[str] = None) -> int:
        """Return the number of active memories, optionally scoped by user_id and/or agent_id."""
        now = time.time()
        where, params = _scope_filter(user_id, agent_id, now)
        cur = self._conn.execute(
            f"SELECT COUNT(*) FROM memories WHERE {where}",
            params,
        )
        return cur.fetchone()[0]


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _scope_filter(
    user_id: Optional[str],
    agent_id: Optional[str],
    now: float,
) -> tuple[str, tuple]:
    """Build a WHERE clause + params tuple for active-row + optional scope filters."""
    clauses = [_ACTIVE]
    params: list = [now]
    if user_id:
        clauses.append("json_extract(metadata, '$.user_id') = ?")
        params.append(user_id)
    if agent_id:
        clauses.append("json_extract(metadata, '$.agent_id') = ?")
        params.append(agent_id)
    return " AND ".join(clauses), tuple(params)


def _cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)
