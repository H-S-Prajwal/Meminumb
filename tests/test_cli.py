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


# ── add ───────────────────────────────────────────────────────────────────────


def test_add_stores_fact(tmp_path, capsys):
    db = _db(tmp_path)
    out, _ = _run(["add", "New CLI fact", "--db", db, "--user", "alice"], capsys)
    assert "Stored" in out
    mem = Memory(db_path=db)
    items = mem.get_all(user_id="alice")
    assert len(items) == 1
    assert items[0].content == "New CLI fact"


def test_add_reports_duplicate(tmp_path, capsys):
    db = _db(tmp_path)
    _run(["add", "Same fact", "--db", db, "--user", "alice"], capsys)
    out, _ = _run(["add", "Same fact", "--db", db, "--user", "alice"], capsys)
    assert "Skipped" in out or "duplicate" in out.lower()


def test_add_with_agent(tmp_path, capsys):
    db = _db(tmp_path)
    out, _ = _run(
        ["add", "Agent-scoped fact", "--db", db, "--user", "alice", "--agent", "bot1"],
        capsys,
    )
    assert "Stored" in out
    mem = Memory(db_path=db)
    items = mem.get_all(user_id="alice", agent_id="bot1")
    assert len(items) == 1


def test_add_with_ttl(tmp_path, capsys):
    db = _db(tmp_path)
    out, _ = _run(["add", "Temp fact", "--db", db, "--user", "u1", "--ttl", "3600"], capsys)
    assert "Stored" in out
    mem = Memory(db_path=db)
    items = mem.get_all(user_id="u1")
    assert items[0].expires_at is not None


# ── delete ────────────────────────────────────────────────────────────────────


def test_delete_existing(tmp_path, capsys):
    db = _db(tmp_path)
    mem = Memory(db_path=db)
    result = mem.add(["delete me"], user_id="u1")
    fid = result.stored[0].id
    out, _ = _run(["delete", fid, "--db", db], capsys)
    assert "Deleted" in out
    assert mem.get(fid) is None


def test_delete_nonexistent(tmp_path, capsys):
    db = _db(tmp_path)
    _seed(db)
    out, _ = _run(["delete", "ghost-id-000000", "--db", db], capsys)
    assert "Not found" in out


# ── recent ────────────────────────────────────────────────────────────────────


def test_recent_returns_memories(tmp_path, capsys):
    db = _db(tmp_path)
    _seed(db)
    out, _ = _run(["recent", "--db", db, "--user", "alice"], capsys)
    assert "Alice likes jazz" in out or "Alice is a developer" in out


def test_recent_respects_n(tmp_path, capsys):
    db = _db(tmp_path)
    _seed(db)
    out, _ = _run(["recent", "1", "--db", db, "--user", "alice"], capsys)
    lines = [line for line in out.splitlines() if line.strip().startswith("[")]
    assert len(lines) == 1


def test_recent_empty(tmp_path, capsys):
    db = _db(tmp_path)
    _seed(db)
    out, _ = _run(["recent", "--db", db, "--user", "nobody"], capsys)
    assert "No memories found" in out


def test_recent_filtered_by_agent(tmp_path, capsys):
    db = _db(tmp_path)
    mem = Memory(db_path=db)
    mem.add(["bot1 fact"], user_id="u1", agent_id="bot1")
    mem.add(["bot2 fact"], user_id="u1", agent_id="bot2")
    out, _ = _run(["recent", "--db", db, "--user", "u1", "--agent", "bot1"], capsys)
    assert "bot1 fact" in out
    assert "bot2 fact" not in out

    db = _db(tmp_path)
    _seed(db, user="alice")
    _seed(db, user="bob", facts=["Bob fact"])
    out, _ = _run(["clear", "--db", db, "--user", "alice"], capsys)
    assert "Cleared" in out
    mem = Memory(db_path=db)
    assert mem.get_all(user_id="alice") == []
    assert len(mem.get_all(user_id="bob")) == 1
