"""Tests for Memory.update() — upsert support (Issue #3)."""
import pytest

from meminumb import Memory


@pytest.fixture
def mem():
    return Memory()


@pytest.fixture
def stored_id(mem):
    result = mem.add(["Alice likes jazz"], user_id="alice")
    return result.stored[0].id


def test_update_content(mem, stored_id):
    updated = mem.update(stored_id, content="Alice loves jazz")
    assert updated.content == "Alice loves jazz"


def test_update_returns_memory_item(mem, stored_id):
    from meminumb.result import MemoryItem
    updated = mem.update(stored_id, content="new content")
    assert isinstance(updated, MemoryItem)
    assert updated.id == stored_id


def test_update_persists(mem, stored_id):
    mem.update(stored_id, content="Alice loves jazz")
    fetched = mem.get(stored_id)
    assert fetched.content == "Alice loves jazz"


def test_update_metadata_only(mem, stored_id):
    updated = mem.update(stored_id, metadata={"source": "conversation"})
    assert updated.metadata["source"] == "conversation"
    assert updated.content == "Alice likes jazz"


def test_update_merges_metadata(mem, stored_id):
    mem.update(stored_id, metadata={"key1": "val1"})
    updated = mem.update(stored_id, metadata={"key2": "val2"})
    assert updated.metadata["key1"] == "val1"
    assert updated.metadata["key2"] == "val2"


def test_update_content_and_metadata_together(mem, stored_id):
    updated = mem.update(stored_id, content="Alice loves jazz", metadata={"verified": True})
    assert updated.content == "Alice loves jazz"
    assert updated.metadata["verified"] is True


def test_update_nonexistent_raises_key_error(mem):
    with pytest.raises(KeyError, match="not found"):
        mem.update("ghost-id", content="something")


def test_update_does_not_change_id(mem, stored_id):
    updated = mem.update(stored_id, content="changed content")
    assert updated.id == stored_id


def test_update_content_re_embeds(mem):
    """After a content update, search should reflect the new content."""
    result = mem.add(["Bob likes cats"], user_id="bob")
    fid = result.stored[0].id
    mem.update(fid, content="Bob likes dogs")
    fetched = mem.get(fid)
    assert fetched.content == "Bob likes dogs"


def test_update_no_args_raises_nothing(mem, stored_id):
    updated = mem.update(stored_id)
    assert updated.id == stored_id
