"""Happy-path tests: add, get, search, delete, clear."""
import pytest

from meminumb import Memory


@pytest.fixture
def mem():
    return Memory()


def test_add_returns_add_result(mem):
    result = mem.add(["Alice likes jazz"])
    assert len(result.stored) == 1
    assert len(result.skipped) == 0
    assert len(result.failed) == 0
    assert result.all_succeeded


def test_stored_item_has_id_and_content(mem):
    result = mem.add(["Bob is a developer"])
    item = result.stored[0]
    assert item.id
    assert item.content == "Bob is a developer"


def test_get_by_id(mem):
    result = mem.add(["Carol prefers Python"])
    fid = result.stored[0].id
    fetched = mem.get(fid)
    assert fetched is not None
    assert fetched.content == "Carol prefers Python"


def test_get_nonexistent_returns_none(mem):
    assert mem.get("does-not-exist") is None


def test_delete_returns_true_for_existing(mem):
    result = mem.add(["Dave enjoys hiking"])
    fid = result.stored[0].id
    assert mem.delete(fid) is True
    assert mem.get(fid) is None


def test_delete_returns_false_for_missing(mem):
    assert mem.delete("ghost-id") is False


def test_get_all(mem):
    mem.add(["fact one", "fact two", "fact three"], user_id="u1")
    items = mem.get_all(user_id="u1")
    assert len(items) == 3


def test_clear_returns_count(mem):
    mem.add(["x", "y"], user_id="u2")
    deleted = mem.clear(user_id="u2")
    assert deleted == 2
    assert mem.get_all(user_id="u2") == []


def test_clear_all(mem):
    mem.add(["a"], user_id="ua")
    mem.add(["b"], user_id="ub")
    total = mem.clear()
    assert total == 2


def test_search_returns_items(mem):
    mem.add(["Eve loves coffee", "Frank hates coffee", "Grace likes tea"], user_id="s1")
    hits = mem.search("coffee", user_id="s1", top_k=2)
    assert len(hits) == 2
    contents = [h.content for h in hits]
    assert "Eve loves coffee" in contents or "Frank hates coffee" in contents


def test_search_respects_top_k(mem):
    mem.add(["a", "b", "c", "d", "e"], user_id="topk")
    hits = mem.search("query", user_id="topk", top_k=3)
    assert len(hits) == 3


def test_empty_facts_are_ignored(mem):
    result = mem.add(["", "   ", "real fact"])
    assert len(result.stored) == 1


def test_user_scoping(mem):
    mem.add(["user1 fact"], user_id="user1")
    mem.add(["user2 fact"], user_id="user2")
    u1_items = mem.get_all(user_id="user1")
    assert len(u1_items) == 1
    assert u1_items[0].content == "user1 fact"


def test_metadata_stored_with_item(mem):
    result = mem.add(["tagged fact"], user_id="u", metadata={"source": "test"})
    fid = result.stored[0].id
    item = mem.get(fid)
    assert item.metadata["source"] == "test"
    assert item.metadata["user_id"] == "u"
