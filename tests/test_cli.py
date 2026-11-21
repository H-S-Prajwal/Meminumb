"""Tests for the meminumb CLI (issue #17)."""

import time

from meminumb import Memory
from meminumb.cli import main


def _db(tmp_path, name="test.db") -> str:
    return str(tmp_path / name)


def _seed(db: str, user: str = "alice", facts: list[str] | None = None) -> None:
    mem = Memory(db_path=db)
    mem.add(facts or ["Alice likes jazz", "Alice is a developer"], user_id=user)


def _run(args: list[str], capsys) -> tuple[str, str]:
    """Run the CLI with given args, return (stdout, stderr)."""
    import sys
    old = sys.argv
    sys.argv = ["meminumb"] + args
    try:
        main()
    except SystemExit:
        pass
    finally:
        sys.argv = old
    captured = capsys.readouterr()
    return captured.out, captured.err


# ── list ──────────────────────────────────────────────────────────────────────


def test_list_shows_memories(tmp_path, capsys):
    db = _db(tmp_path)
    _seed(db)
    out, _ = _run(["list", "--db", db, "--user", "alice"], capsys)
    assert "Alice likes jazz" in out
    assert "Alice is a developer" in out


def test_list_empty(tmp_path, capsys):
    db = _db(tmp_path)
    _seed(db)
    out, _ = _run(["list", "--db", db, "--user", "nobody"], capsys)
    assert "No memories found" in out


def test_list_shows_expiry_for_ttl_memories(tmp_path, capsys):
    db = _db(tmp_path)
    mem = Memory(db_path=db)
    mem.add(["temp fact"], user_id="u1", ttl_seconds=3600)
    out, _ = _run(["list", "--db", db, "--user", "u1"], capsys)
    assert "expires" in out


# ── search ────────────────────────────────────────────────────────────────────


def test_search_returns_results(tmp_path, capsys):
    db = _db(tmp_path)
    _seed(db)
    out, _ = _run(["search", "music", "--db", db, "--user", "alice"], capsys)
    assert "result" in out.lower()


def test_search_no_results(tmp_path, capsys):
    db = _db(tmp_path)
    _seed(db)
    mem = Memory(db_path=db)
    mem.clear(user_id="alice")
    out, _ = _run(["search", "music", "--db", db, "--user", "alice"], capsys)
    assert "No results" in out


# ── stats ─────────────────────────────────────────────────────────────────────


def test_stats_shows_counts(tmp_path, capsys):
    db = _db(tmp_path)
    _seed(db)
    out, _ = _run(["stats", "--db", db], capsys)
    assert "Total" in out
    assert "Users" in out


def test_stats_counts_expired(tmp_path, capsys):
    db = _db(tmp_path)
    mem = Memory(db_path=db)
    mem.add(["perm"], user_id="u1")
    mem.add(["temp"], user_id="u1", ttl_seconds=0)
    time.sleep(0.01)
    out, _ = _run(["stats", "--db", db], capsys)
    assert "1 expired" in out


# ── clear-expired ─────────────────────────────────────────────────────────────


def test_clear_expired_removes_expired(tmp_path, capsys):
    db = _db(tmp_path)
    mem = Memory(db_path=db)
    mem.add(["keep"], user_id="u1")
    mem.add(["lose"], user_id="u1", ttl_seconds=0)
    time.sleep(0.01)
    out, _ = _run(["clear-expired", "--db", db], capsys)
    assert "1" in out
    assert len(mem.get_all(user_id="u1")) == 1


# ── clear ─────────────────────────────────────────────────────────────────────


def test_clear_user(tmp_path, capsys):
    db = _db(tmp_path)
    _seed(db, user="alice")
    _seed(db, user="bob", facts=["Bob fact"])
    out, _ = _run(["clear", "--db", db, "--user", "alice"], capsys)
    assert "Cleared" in out
    mem = Memory(db_path=db)
    assert mem.get_all(user_id="alice") == []
    assert len(mem.get_all(user_id="bob")) == 1
