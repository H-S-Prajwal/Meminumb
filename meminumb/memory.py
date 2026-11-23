from __future__ import annotations

import time
from typing import Optional

from meminumb._id import content_id
from meminumb.embedder import BaseEmbedder, DummyEmbedder
from meminumb.result import AddResult, MemoryItem, SkippedItem, SkipReason
from meminumb.store import SQLiteStore


class Memory:
    """
    Reliable memory layer for AI agents.

    Key guarantees:
    - Every add() call returns an AddResult. Nothing is silently dropped.
    - Writes are atomic: a failure leaves no orphaned data in the store.
    - Facts are content-addressed: adding the same fact twice is a no-op
      (reported as skipped, not silently ignored and not duplicated).

    Quickstart::

        from meminumb import Memory
        mem = Memory()
        result = mem.add(["Alice likes jazz", "Alice dislikes spicy food"], user_id="alice")
        print(result)   # AddResult(stored=2, skipped=0, failed=0)

        hits = mem.search("what music does Alice enjoy?", user_id="alice")
        print(hits[0].content)  # Alice likes jazz
    """

    def __init__(
        self,
        store: Optional[SQLiteStore] = None,
        embedder: Optional[BaseEmbedder] = None,
        db_path: str = ":memory:",
    ) -> None:
        self._store = store or SQLiteStore(db_path)
        self._embedder = embedder or DummyEmbedder()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def add(
        self,
        facts: list[str],
        user_id: str = "",
        agent_id: str = "",
        metadata: Optional[dict] = None,
        ttl_seconds: Optional[int] = None,
    ) -> AddResult:
        """
        Store a list of facts. Returns an AddResult describing the outcome
        of every individual fact — stored, skipped, or failed.

        Args:
            facts:       Plain-text facts to remember.
            user_id:     Scope the memory to a specific user.
            agent_id:    Scope the memory to a specific agent (optional).
            metadata:    Extra key/value pairs stored alongside each fact.
            ttl_seconds: Seconds until this memory expires. Omit for permanent storage.
        """
        result = AddResult()
        base_meta = {"user_id": user_id, "agent_id": agent_id, **(metadata or {})}
        expires_at = time.time() + ttl_seconds if ttl_seconds is not None else None

        for fact in facts:
            fact = fact.strip()
            if not fact:
                continue

            fid = content_id(fact, user_id, agent_id)

            # 1. Duplicate check — no write attempted
            if self._store.exists(fid):
                result.skipped.append(
                    SkippedItem(
                        content=fact,
                        reason=SkipReason.DUPLICATE,
                        existing_id=fid,
                    )
                )
                continue

            # 2. Embed — may fail if the embedder is unavailable
            try:
                embedding = self._embedder.embed(fact)
            except Exception as exc:
                result.failed.append(
                    SkippedItem(
                        content=fact,
                        reason=SkipReason.EMBED_FAILED,
                        error=str(exc),
                    )
                )
                continue

            # 3. Atomic write — SQLite rolls back automatically on any error
            try:
                item = MemoryItem(id=fid, content=fact, metadata=base_meta, expires_at=expires_at)
                self._store.add_atomic(item, embedding, expires_at=expires_at)
                result.stored.append(item)
            except Exception as exc:
                result.failed.append(
                    SkippedItem(
                        content=fact,
                        reason=SkipReason.INSERT_FAILED,
                        error=str(exc),
                    )
                )

        return result

    def update(
        self,
        memory_id: str,
        content: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> MemoryItem:
        """
        Update an existing memory's content and/or metadata.

        If content changes, it is re-embedded automatically.
        Returns the updated MemoryItem.
        Raises KeyError if memory_id does not exist.

        Args:
            memory_id: ID of the memory to update.
            content:   New content text. If omitted, content is unchanged.
            metadata:  Extra key/value pairs to merge into existing metadata.
        """
        if not self._store.exists(memory_id):
            raise KeyError(f"Memory '{memory_id}' not found.")

        new_embedding = None
        if content is not None:
            content = content.strip()
            new_embedding = self._embedder.embed(content)

        self._store.update_atomic(memory_id, content, new_embedding, metadata)
        return self._store.get(memory_id)

    def delete(self, memory_id: str) -> bool:
        """Remove a memory by its ID. Returns True if it existed."""
        return self._store.delete(memory_id)

    def clear(self, user_id: str = "") -> int:
        """Delete all memories (optionally scoped to a user). Returns count deleted."""
        return self._store.clear(user_id or None)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get(self, memory_id: str) -> Optional[MemoryItem]:
        """Fetch a single memory by ID, or None if not found."""
        return self._store.get(memory_id)

    def search(
        self,
        query: str,
        user_id: str = "",
        agent_id: str = "",
        top_k: int = 5,
    ) -> list[MemoryItem]:
        """
        Return the top_k most relevant memories for the given query.

        Uses cosine similarity between the query embedding and stored
        embeddings. Scoped to user_id and/or agent_id when provided.
        """
        query_embedding = self._embedder.embed(query)
        return self._store.search(
            query_embedding,
            top_k=top_k,
            user_id=user_id or None,
            agent_id=agent_id or None,
        )

    def get_all(self, user_id: str = "", agent_id: str = "") -> list[MemoryItem]:
        """Return all stored memories, optionally filtered by user_id and/or agent_id."""
        return self._store.all(user_id=user_id or None, agent_id=agent_id or None)

    def get_recent(self, n: int, user_id: str = "", agent_id: str = "") -> list[MemoryItem]:
        """
        Return the n most recently added memories, newest first.

        Args:
            n:        Maximum number of memories to return.
            user_id:  Scope to a specific user. Returns across all users if omitted.
            agent_id: Scope to a specific agent. Returns across all agents if omitted.
        """
        return self._store.recent(n, user_id=user_id or None, agent_id=agent_id or None)

    def count(self, user_id: str = "", agent_id: str = "") -> int:
        """Return the number of active memories, optionally scoped by user_id and/or agent_id."""
        return self._store.count(user_id=user_id or None, agent_id=agent_id or None)

    def clear_expired(self) -> int:
        """Delete all memories whose TTL has passed. Returns the count removed."""
        return self._store.clear_expired()
