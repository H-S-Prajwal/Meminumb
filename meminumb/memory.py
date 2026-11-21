from __future__ import annotations

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
    ) -> AddResult:
        """
        Store a list of facts. Returns an AddResult describing the outcome
        of every individual fact — stored, skipped, or failed.

        Args:
            facts:    Plain-text facts to remember.
            user_id:  Scope the memory to a specific user.
            agent_id: Scope the memory to a specific agent (optional).
            metadata: Extra key/value pairs stored alongside each fact.
        """
        result = AddResult()
        base_meta = {"user_id": user_id, "agent_id": agent_id, **(metadata or {})}

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
                item = MemoryItem(id=fid, content=fact, metadata=base_meta)
                self._store.add_atomic(item, embedding)
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
        top_k: int = 5,
    ) -> list[MemoryItem]:
        """
        Return the top_k most relevant memories for the given query.

        Uses cosine similarity between the query embedding and stored
        embeddings. Scoped to user_id when provided.
        """
        query_embedding = self._embedder.embed(query)
        return self._store.search(query_embedding, top_k=top_k, user_id=user_id or None)

    def get_all(self, user_id: str = "") -> list[MemoryItem]:
        """Return all stored memories, optionally filtered by user_id."""
        return self._store.all(user_id=user_id or None)
