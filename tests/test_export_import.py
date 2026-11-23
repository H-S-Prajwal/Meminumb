"""Tests for Memory.export() / Memory.import_from() and CLI export/import (issue #20)."""

import json
import sys
import time

from meminumb import Memory
from meminumb.cli import main

# ── helpers ───────────────────────────────────────────────────────────────────


def _db(tmp_path, name="test.db") -> str:
    return str(tmp_path / name)


def _run(args: list[str], capsys) -> tuple[str, str]:
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


# ── export ────────────────────────────────────────────────────────────────────


def test_export_creates_valid_json(tmp_path):
    db = _db(tmp_path)
    mem = Memory(db_path=db)
    mem.add(["Alice likes jazz", "Alice dislikes spicy food"], user_id="alice")

    out_file = str(tmp_path / "backup.json")
    count = mem.export(out_file)

    assert count == 2
    with open(out_file) as fh:
        data = json.load(fh)

    assert data["count"] == 2
    assert "meminumb_version" in data
    assert "exported_at" in data
    assert len(data["memories"]) == 2


def test_export_includes_embeddings(tmp_path):
    db = _db(tmp_path)
    mem = Memory(db_path=db)
    mem.add(["Some fact"], user_id="u1")

    out_file = str(tmp_path / "backup.json")
    mem.export(out_file)

    with open(out_file) as fh:
        data = json.load(fh)

    assert isinstance(data["memories"][0]["embedding"], list)


def test_export_scoped_to_user(tmp_path):
    db = _db(tmp_path)
    mem = Memory(db_path=db)
    mem.add(["Alice fact"], user_id="alice")
    mem.add(["Bob fact"], user_id="bob")

    out_file = str(tmp_path / "alice.json")
    count = mem.export(out_file, user_id="alice")

    assert count == 1
    with open(out_file) as fh:
        data = json.load(fh)
    assert data["memories"][0]["content"] == "Alice fact"


def test_export_empty_db(tmp_path):
    db = _db(tmp_path)
    mem = Memory(db_path=db)
    out_file = str(tmp_path / "empty.json")
    count = mem.export(out_file)

    assert count == 0
    with open(out_file) as fh:
        data = json.load(fh)
    assert data["count"] == 0
    assert data["memories"] == []


# ── import ────────────────────────────────────────────────────────────────────


def test_import_restores_memories(tmp_path):
    src_db = _db(tmp_path, "source.db")
    dst_db = _db(tmp_path, "dest.db")

    src = Memory(db_path=src_db)
    src.add(["Alice likes jazz", "Alice is a developer"], user_id="alice")

    out_file = str(tmp_path / "backup.json")
    src.export(out_file)

    dst = Memory(db_path=dst_db)
    result = dst.import_from(out_file)

    assert result["stored"] == 2
    assert result["skipped"] == 0
    assert result["failed"] == 0
    items = dst.get_all(user_id="alice")
    assert len(items) == 2
    contents = {i.content for i in items}
    assert "Alice likes jazz" in contents
    assert "Alice is a developer" in contents


def test_import_round_trip_preserves_ids(tmp_path):
    src_db = _db(tmp_path, "source.db")
    dst_db = _db(tmp_path, "dest.db")

    src = Memory(db_path=src_db)
    result = src.add(["Fact A", "Fact B"], user_id="u1")
    original_ids = {item.id for item in result.stored}

    out_file = str(tmp_path / "backup.json")
    src.export(out_file)

    dst = Memory(db_path=dst_db)
    dst.import_from(out_file)

    imported_ids = {item.id for item in dst.get_all(user_id="u1")}
    assert imported_ids == original_ids


def test_import_skips_duplicates(tmp_path):
    db = _db(tmp_path)
    mem = Memory(db_path=db)
    mem.add(["Persistent fact"], user_id="u1")

    out_file = str(tmp_path / "backup.json")
    mem.export(out_file)

    result = mem.import_from(out_file)

    assert result["stored"] == 0
    assert result["skipped"] == 1
    assert len(mem.get_all(user_id="u1")) == 1


def test_import_skips_expired_memories(tmp_path):
    src_db = _db(tmp_path, "source.db")
    dst_db = _db(tmp_path, "dest.db")

    src = Memory(db_path=src_db)
    src.add(["Keep me"], user_id="u1")
    src.add(["Expire me"], user_id="u1", ttl_seconds=0)
    time.sleep(0.01)

    out_file = str(tmp_path / "backup.json")
    # Export the raw file including the expired row (export_rows sees active rows only,
    # so we manually patch the JSON to include an expired entry for the skip test).
    src.export(out_file)
    with open(out_file) as fh:
        data = json.load(fh)

    # Inject a fake already-expired memory into the JSON
    data["memories"].append(
        {
            "id": "deadbeef00000000",
            "content": "Already expired",
            "metadata": {"user_id": "u1", "agent_id": ""},
            "embedding": [],
            "created_at": time.time() - 100,
            "expires_at": time.time() - 1,  # expired
        }
    )
    with open(out_file, "w") as fh:
        json.dump(data, fh)

    dst = Memory(db_path=dst_db)
    result = dst.import_from(out_file)

    assert result["skipped"] >= 1
    assert dst.get("deadbeef00000000") is None


def test_import_partial_missing_embedding_re_embeds(tmp_path):
    src_db = _db(tmp_path, "source.db")
    dst_db = _db(tmp_path, "dest.db")

    src = Memory(db_path=src_db)
    src.add(["No embed fact"], user_id="u1")

    out_file = str(tmp_path / "backup.json")
    src.export(out_file)

    with open(out_file) as fh:
        data = json.load(fh)
    # strip the embedding to force re-embed path
    data["memories"][0]["embedding"] = []
    with open(out_file, "w") as fh:
        json.dump(data, fh)

    dst = Memory(db_path=dst_db)
    result = dst.import_from(out_file)

    assert result["stored"] == 1


# ── CLI export/import ─────────────────────────────────────────────────────────


def test_cli_export_creates_file(tmp_path, capsys):
    db = _db(tmp_path)
    mem = Memory(db_path=db)
    mem.add(["CLI export fact"], user_id="alice")

    out_file = str(tmp_path / "out.json")
    out, _ = _run(["export", "--db", db, "--output", out_file, "--user", "alice"], capsys)

    assert "1" in out
    assert out_file in out
    with open(out_file) as fh:
        data = json.load(fh)
    assert data["count"] == 1


def test_cli_import_restores_data(tmp_path, capsys):
    src_db = _db(tmp_path, "src.db")
    dst_db = _db(tmp_path, "dst.db")

    mem = Memory(db_path=src_db)
    mem.add(["CLI import fact"], user_id="u1")

    out_file = str(tmp_path / "dump.json")
    mem.export(out_file)

    out, _ = _run(["import", "--db", dst_db, "--input", out_file], capsys)
    assert "1 stored" in out

    dst = Memory(db_path=dst_db)
    assert len(dst.get_all(user_id="u1")) == 1


def test_cli_import_dry_run(tmp_path, capsys):
    db = _db(tmp_path)
    mem = Memory(db_path=db)
    mem.add(["Dry run fact"], user_id="u1")

    out_file = str(tmp_path / "dump.json")
    mem.export(out_file)

    empty_db = _db(tmp_path, "empty.db")
    out, _ = _run(["import", "--db", empty_db, "--input", out_file, "--dry-run"], capsys)

    assert "dry-run" in out.lower()
    assert "1" in out
    # nothing was actually imported
    dst = Memory(db_path=empty_db)
    assert len(dst.get_all()) == 0
