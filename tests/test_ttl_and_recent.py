"""Tests for Memory TTL/expiry (issue #14) and get_recent (issue #15)."""

import time

from meminumb import Memory

# ── Helpers ───────────────────────────────────────────────────────────────────


def mem() -> Memory:
    return Memory(db_path=":memory:")


# ── TTL / expiry ──────────────────────────────────────────────────────────────


def test_ttl_memory_visible_before_expiry():
    m = mem()
    m.add(["session flag"], user_id="u1", ttl_seconds=60)
    items = m.get_all(user_id="u1")
    assert len(items) == 1
    assert items[0].content == "session flag"


def test_ttl_memory_invisible_after_expiry():
    m = mem()
    result = m.add(["short-lived fact"], user_id="u1", ttl_seconds=0)
    fid = result.stored[0].id
    # expires_at is in the past (ttl=0 means now), so the row is already expired
    time.sleep(0.01)
    assert m.get(fid) is None
    assert m.get_all(user_id="u1") == []


def test_ttl_memory_not_found_via_search():
    m = mem()
    m.add(["fleeting thought"], user_id="u1", ttl_seconds=0)
    time.sleep(0.01)
    hits = m.search("fleeting", user_id="u1")
    assert hits == []


def test_ttl_memory_expires_at_field_set():
    m = mem()
    before = time.time()
    result = m.add(["expiring fact"], user_id="u1", ttl_seconds=300)
    after = time.time()
    item = result.stored[0]
    assert item.expires_at is not None
    assert before + 300 <= item.expires_at <= after + 300


def test_permanent_memory_expires_at_is_none():
    m = mem()
    result = m.add(["permanent fact"], user_id="u1")
    assert result.stored[0].expires_at is None


def test_expired_memory_can_be_re_added():
    """After TTL, the same fact can be stored again (expired row is replaced)."""
    m = mem()
    r1 = m.add(["re-add me"], user_id="u1", ttl_seconds=0)
    fid = r1.stored[0].id
    time.sleep(0.01)
    r2 = m.add(["re-add me"], user_id="u1")
    assert len(r2.stored) == 1
    assert r2.stored[0].id == fid  # same content-addressed ID


def test_clear_expired_removes_only_expired():
    m = mem()
    m.add(["keep me"], user_id="u1")
    m.add(["lose me"], user_id="u1", ttl_seconds=0)
    time.sleep(0.01)
    removed = m.clear_expired()
    assert removed == 1
    remaining = m.get_all(user_id="u1")
    assert len(remaining) == 1
    assert remaining[0].content == "keep me"


def test_clear_expired_returns_zero_when_nothing_expired():
    m = mem()
    m.add(["permanent"], user_id="u1")
    assert m.clear_expired() == 0


def test_ttl_does_not_affect_other_users():
    m = mem()
    m.add(["alice's fleeting note"], user_id="alice", ttl_seconds=0)
    m.add(["bob's permanent note"], user_id="bob")
    time.sleep(0.01)
    assert m.get_all(user_id="alice") == []
    assert len(m.get_all(user_id="bob")) == 1


# ── get_recent ────────────────────────────────────────────────────────────────


def test_get_recent_returns_newest_first():
    m = mem()
    m.add(["first"], user_id="u1")
    time.sleep(0.001)
    m.add(["second"], user_id="u1")
    time.sleep(0.001)
    m.add(["third"], user_id="u1")

    items = m.get_recent(3, user_id="u1")
    assert [i.content for i in items] == ["third", "second", "first"]


def test_get_recent_respects_n():
    m = mem()
    for i in range(5):
        m.add([f"fact {i}"], user_id="u1")
        time.sleep(0.001)
    items = m.get_recent(2, user_id="u1")
    assert len(items) == 2


def test_get_recent_fewer_than_n():
    m = mem()
    m.add(["only one"], user_id="u1")
    items = m.get_recent(10, user_id="u1")
    assert len(items) == 1


def test_get_recent_empty():
    m = mem()
    assert m.get_recent(5, user_id="u1") == []


def test_get_recent_scoped_to_user():
    m = mem()
    m.add(["alice fact"], user_id="alice")
    m.add(["bob fact"], user_id="bob")
    items = m.get_recent(10, user_id="alice")
    assert len(items) == 1
    assert items[0].content == "alice fact"


def test_get_recent_excludes_expired():
    m = mem()
    m.add(["expired fact"], user_id="u1", ttl_seconds=0)
    time.sleep(0.001)
    m.add(["live fact"], user_id="u1")
    items = m.get_recent(10, user_id="u1")
    assert len(items) == 1
    assert items[0].content == "live fact"
