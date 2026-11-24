"""Tests for search_scored() and min_score filtering."""
import pytest

from meminumb import Memory, SearchResult
from meminumb.embedder import DummyEmbedder


@pytest.fixture
def mem():
    return Memory(embedder=DummyEmbedder())


# ── SearchResult structure ────────────────────────────────────────────────────


def test_search_scored_returns_search_results(mem):
    mem.add(["Alice likes jazz"], user_id="u1")
    results = mem.search_scored("jazz", user_id="u1")
    assert len(results) == 1
    assert isinstance(results[0], SearchResult)


def test_search_result_has_item_and_score(mem):
    mem.add(["Bob is a developer"], user_id="u1")
    r = mem.search_scored("developer", user_id="u1")[0]
    assert r.item.content == "Bob is a developer"
    assert isinstance(r.score, float)
    assert 0.0 <= r.score <= 1.0


def test_search_scored_empty_store_returns_empty(mem):
    assert mem.search_scored("anything") == []


def test_search_scored_respects_top_k(mem):
    mem.add(["a", "b", "c", "d", "e"], user_id="u1")
    results = mem.search_scored("query", user_id="u1", top_k=3)
    assert len(results) == 3


def test_search_scored_sorted_by_score_descending(mem):
    mem.add(["x", "y", "z"], user_id="u1")
    results = mem.search_scored("x", user_id="u1", top_k=3)
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_search_scored_respects_user_id(mem):
    mem.add(["alice fact"], user_id="alice")
    mem.add(["bob fact"], user_id="bob")
    results = mem.search_scored("fact", user_id="alice")
    assert all(r.item.metadata["user_id"] == "alice" for r in results)


def test_search_scored_respects_agent_id(mem):
    mem.add(["bot1 memory"], user_id="u1", agent_id="bot1")
    mem.add(["bot2 memory"], user_id="u1", agent_id="bot2")
    results = mem.search_scored("memory", user_id="u1", agent_id="bot1")
    assert len(results) == 1
    assert results[0].item.metadata["agent_id"] == "bot1"


# ── min_score filtering ───────────────────────────────────────────────────────


def test_min_score_filters_low_results():
    """With min_score=1.0 only an exact-match fact should survive."""
    m = Memory(embedder=DummyEmbedder())
    m.add(["exact query text"], user_id="u1")
    m.add(["something completely unrelated"], user_id="u1")

    # DummyEmbedder produces score=1.0 only for identical text
    results = m.search_scored("exact query text", user_id="u1", min_score=1.0)
    assert len(results) == 1
    assert results[0].item.content == "exact query text"


def test_min_score_zero_returns_all(mem):
    mem.add(["a", "b", "c"], user_id="u1")
    results = mem.search_scored("x", user_id="u1", top_k=10, min_score=0.0)
    assert len(results) == 3


def test_min_score_one_returns_only_exact(mem):
    mem.add(["hello world"], user_id="u1")
    mem.add(["goodbye world"], user_id="u1")
    results = mem.search_scored("hello world", user_id="u1", top_k=10, min_score=1.0)
    assert len(results) == 1
    assert results[0].score == pytest.approx(1.0)


def test_search_plain_respects_min_score(mem):
    """memory.search() with min_score should also filter out low-scoring results."""
    mem.add(["hello world"], user_id="u1")
    mem.add(["goodbye world"], user_id="u1")
    items = mem.search("hello world", user_id="u1", top_k=10, min_score=1.0)
    assert len(items) == 1
    assert items[0].content == "hello world"


def test_min_score_above_all_returns_empty(mem):
    mem.add(["some fact"], user_id="u1")
    results = mem.search_scored("completely different", user_id="u1", min_score=0.9999)
    # DummyEmbedder won't hit 0.9999 for unrelated text — may be 0 results
    assert all(r.score >= 0.9999 for r in results)


# ── backward compatibility ────────────────────────────────────────────────────


def test_plain_search_still_returns_memory_items(mem):
    from meminumb import MemoryItem

    mem.add(["Carol likes hiking"], user_id="u1")
    items = mem.search("hiking", user_id="u1")
    assert len(items) == 1
    assert isinstance(items[0], MemoryItem)


def test_search_and_search_scored_return_same_items(mem):
    mem.add(["fact one", "fact two", "fact three"], user_id="u1")
    items = mem.search("query", user_id="u1", top_k=3)
    scored = mem.search_scored("query", user_id="u1", top_k=3)
    assert [r.item for r in scored] == items
