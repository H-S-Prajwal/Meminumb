"""
Outcome tests: every add() call must classify each fact as stored/skipped/failed
with a machine-readable reason. Nothing is silently dropped.
"""
import pytest

from meminumb import Memory, SkipReason
from meminumb.embedder import DummyEmbedder


@pytest.fixture
def mem():
    return Memory(embedder=DummyEmbedder())


# ------------------------------------------------------------------
# Duplicate detection
# ------------------------------------------------------------------


def test_same_fact_twice_is_skipped(mem):
    mem.add(["Alice likes jazz"], user_id="u1")
    result = mem.add(["Alice likes jazz"], user_id="u1")

    assert len(result.stored) == 0
    assert len(result.skipped) == 1
    assert result.skipped[0].reason == SkipReason.DUPLICATE


def test_duplicate_reports_existing_id(mem):
    first = mem.add(["Bob owns a cat"], user_id="u2")
    fid = first.stored[0].id

    second = mem.add(["Bob owns a cat"], user_id="u2")
    assert second.skipped[0].existing_id == fid


def test_same_fact_different_users_not_duplicate(mem):
    r1 = mem.add(["shared fact"], user_id="user-a")
    r2 = mem.add(["shared fact"], user_id="user-b")
    assert len(r1.stored) == 1
    assert len(r2.stored) == 1


def test_case_and_whitespace_normalized_for_dedup(mem):
    mem.add(["Carol likes hiking"], user_id="u3")
    result = mem.add(["  CAROL LIKES HIKING  "], user_id="u3")
    assert result.skipped[0].reason == SkipReason.DUPLICATE


# ------------------------------------------------------------------
# Embed failure
# ------------------------------------------------------------------


def test_embed_failure_reported_in_failed(mem):
    class BrokenEmbedder(DummyEmbedder):
        def embed(self, text: str) -> list[float]:
            raise RuntimeError("model unavailable")

    mem._embedder = BrokenEmbedder()
    result = mem.add(["this should fail"])

    assert len(result.failed) == 1
    assert result.failed[0].reason == SkipReason.EMBED_FAILED
    assert "model unavailable" in result.failed[0].error


def test_embed_failure_does_not_store_anything(mem):
    class BrokenEmbedder(DummyEmbedder):
        def embed(self, text: str) -> list[float]:
            raise RuntimeError("broken")

    mem._embedder = BrokenEmbedder()
    mem.add(["ghost fact"])
    assert mem.get_all() == []


# ------------------------------------------------------------------
# AddResult structure
# ------------------------------------------------------------------


def test_add_result_all_succeeded_true_when_no_failures(mem):
    result = mem.add(["clean fact"])
    assert result.all_succeeded is True


def test_add_result_all_succeeded_false_when_failed(mem):
    class BrokenEmbedder(DummyEmbedder):
        def embed(self, text: str) -> list[float]:
            raise RuntimeError("broken")

    mem._embedder = BrokenEmbedder()
    result = mem.add(["will fail"])
    assert result.all_succeeded is False


def test_add_result_repr(mem):
    result = mem.add(["a", "b"])
    r = repr(result)
    assert "stored=2" in r
    assert "skipped=0" in r
    assert "failed=0" in r


def test_mixed_batch(mem):
    """A batch with new, duplicate, and failing facts is classified correctly."""

    class SelectiveBrokenEmbedder(DummyEmbedder):
        def embed(self, text: str) -> list[float]:
            if text == "embed this will fail":
                raise RuntimeError("boom")
            return super().embed(text)

    mem._embedder = SelectiveBrokenEmbedder()

    mem.add(["existing fact"], user_id="mix")

    result = mem.add(
        ["new fact", "existing fact", "embed this will fail"],
        user_id="mix",
    )

    assert len(result.stored) == 1
    assert result.stored[0].content == "new fact"

    assert len(result.skipped) == 1
    assert result.skipped[0].reason == SkipReason.DUPLICATE

    assert len(result.failed) == 1
    assert result.failed[0].reason == SkipReason.EMBED_FAILED


def test_skipped_item_has_content(mem):
    mem.add(["repeat"], user_id="sc")
    result = mem.add(["repeat"], user_id="sc")
    assert result.skipped[0].content == "repeat"


def test_failed_item_has_content_and_error(mem):
    class BrokenEmbedder(DummyEmbedder):
        def embed(self, text: str) -> list[float]:
            raise ValueError("bad input")

    mem._embedder = BrokenEmbedder()
    result = mem.add(["failing fact"])
    item = result.failed[0]
    assert item.content == "failing fact"
    assert item.error is not None
