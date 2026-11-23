"""Tests for agent_id scoping in read operations and count()."""
import pytest

from meminumb import Memory


@pytest.fixture
def mem():
    return Memory()


# ── agent_id filtering in get_all ────────────────────────────────────────────


def test_get_all_filtered_by_agent_id(mem):
    mem.add(["bot1 fact"], user_id="u1", agent_id="bot1")
    mem.add(["bot2 fact"], user_id="u1", agent_id="bot2")
    items = mem.get_all(user_id="u1", agent_id="bot1")
    assert len(items) == 1
    assert items[0].content == "bot1 fact"


def test_get_all_agent_id_does_not_cross_users(mem):
    mem.add(["alice bot1"], user_id="alice", agent_id="bot1")
    mem.add(["bob bot1"], user_id="bob", agent_id="bot1")
    items = mem.get_all(user_id="alice", agent_id="bot1")
    assert len(items) == 1
    assert items[0].content == "alice bot1"


def test_get_all_no_agent_id_returns_all_agents(mem):
    mem.add(["bot1 fact"], user_id="u1", agent_id="bot1")
    mem.add(["bot2 fact"], user_id="u1", agent_id="bot2")
    items = mem.get_all(user_id="u1")
    assert len(items) == 2


def test_get_all_agent_id_no_match_returns_empty(mem):
    mem.add(["bot1 fact"], user_id="u1", agent_id="bot1")
    items = mem.get_all(user_id="u1", agent_id="ghost")
    assert items == []


# ── agent_id filtering in search ─────────────────────────────────────────────


def test_search_filtered_by_agent_id(mem):
    mem.add(["bot1 memory"], user_id="u1", agent_id="bot1")
    mem.add(["bot2 memory"], user_id="u1", agent_id="bot2")
    hits = mem.search("memory", user_id="u1", agent_id="bot1")
    assert len(hits) == 1
    assert hits[0].content == "bot1 memory"


def test_search_no_agent_id_returns_all(mem):
    mem.add(["bot1 memory"], user_id="u1", agent_id="bot1")
    mem.add(["bot2 memory"], user_id="u1", agent_id="bot2")
    hits = mem.search("memory", user_id="u1")
    assert len(hits) == 2


# ── agent_id filtering in get_recent ─────────────────────────────────────────


def test_get_recent_filtered_by_agent_id(mem):
    import time
    mem.add(["bot1 recent"], user_id="u1", agent_id="bot1")
    time.sleep(0.001)
    mem.add(["bot2 recent"], user_id="u1", agent_id="bot2")
    items = mem.get_recent(10, user_id="u1", agent_id="bot2")
    assert len(items) == 1
    assert items[0].content == "bot2 recent"


def test_get_recent_no_agent_id_returns_all(mem):
    mem.add(["bot1 fact"], user_id="u1", agent_id="bot1")
    mem.add(["bot2 fact"], user_id="u1", agent_id="bot2")
    items = mem.get_recent(10, user_id="u1")
    assert len(items) == 2


# ── count() ──────────────────────────────────────────────────────────────────


def test_count_all(mem):
    mem.add(["a", "b", "c"])
    assert mem.count() == 3


def test_count_by_user_id(mem):
    mem.add(["u1 a", "u1 b"], user_id="u1")
    mem.add(["u2 a"], user_id="u2")
    assert mem.count(user_id="u1") == 2
    assert mem.count(user_id="u2") == 1


def test_count_by_agent_id(mem):
    mem.add(["bot1 a", "bot1 b"], user_id="u1", agent_id="bot1")
    mem.add(["bot2 a"], user_id="u1", agent_id="bot2")
    assert mem.count(user_id="u1", agent_id="bot1") == 2
    assert mem.count(user_id="u1", agent_id="bot2") == 1


def test_count_empty(mem):
    assert mem.count() == 0


def test_count_excludes_expired():
    import time
    m = Memory()
    m.add(["keep"], user_id="u1")
    m.add(["lose"], user_id="u1", ttl_seconds=0)
    time.sleep(0.01)
    assert m.count(user_id="u1") == 1
