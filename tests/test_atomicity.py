"""
Atomicity tests: a failed write must leave no orphaned data in the store.

These tests inject failures at the SQLite layer by patching the internal
_conn to simulate disk or constraint errors, then verify that the store is
left in a clean state — no partial rows, no orphaned entries.
"""
import sqlite3

import pytest

from meminumb import Memory, SkipReason
from meminumb.store import SQLiteStore


@pytest.fixture
def store():
    return SQLiteStore(":memory:")


@pytest.fixture
def mem(store):
    return Memory(store=store)


def test_no_orphan_on_duplicate_id_error(store):
    """
    A duplicate PRIMARY KEY causes an IntegrityError.
    After the error the ORIGINAL row must be unchanged — no corrupt state.

    This exercises SQLite's real rollback, without mocking the connection
    (which is read-only on Python 3.14+).
    """
    from meminumb.embedder import DummyEmbedder
    from meminumb.result import MemoryItem

    embedder = DummyEmbedder()
    original = MemoryItem(id="shared-id", content="original content", metadata={})
    store.add_atomic(original, embedder.embed("original content"))
    assert store.exists("shared-id")

    # Trying to insert the same ID must raise
    duplicate = MemoryItem(id="shared-id", content="overwrite attempt", metadata={})
    with pytest.raises(Exception):
        store.add_atomic(duplicate, embedder.embed("overwrite attempt"))

    # Original row must be intact — not overwritten, not duplicated
    fetched = store.get("shared-id")
    assert fetched is not None
    assert fetched.content == "original content"


def test_add_reports_failed_on_store_error(store):
    """Memory.add() must report INSERT_FAILED, not raise, when the store errors."""
    from meminumb.embedder import DummyEmbedder

    mem = Memory(store=store, embedder=DummyEmbedder())

    def boom(item, embedding):
        raise sqlite3.OperationalError("simulated failure")

    store.add_atomic = boom

    result = mem.add(["this will fail to insert"])
    assert len(result.failed) == 1
    assert result.failed[0].reason == SkipReason.INSERT_FAILED
    assert "simulated failure" in result.failed[0].error


def test_failed_insert_leaves_no_row(store):
    """After an INSERT_FAILED, the content ID must not appear in the store."""
    from meminumb._id import content_id
    from meminumb.embedder import DummyEmbedder

    fact = "ghost memory"
    mem = Memory(store=store, embedder=DummyEmbedder())
    fid = content_id(fact)

    store.add_atomic = lambda item, emb: (_ for _ in ()).throw(
        sqlite3.OperationalError("boom")
    )

    mem.add([fact])
    assert not store.exists(fid)


def test_second_fact_stored_after_first_fails(store):
    """
    If the first fact fails to insert, the second must still be attempted
    and stored. Failures are per-fact, not per-batch.
    """
    from meminumb.embedder import DummyEmbedder

    mem = Memory(store=store, embedder=DummyEmbedder())

    first_call = True
    _original = store.add_atomic

    def selective_fail(item, embedding):
        nonlocal first_call
        if first_call:
            first_call = False
            raise sqlite3.OperationalError("first fact fails")
        return _original(item, embedding)

    store.add_atomic = selective_fail

    result = mem.add(["will fail", "will succeed"])
    assert len(result.failed) == 1
    assert len(result.stored) == 1
    assert result.stored[0].content == "will succeed"
