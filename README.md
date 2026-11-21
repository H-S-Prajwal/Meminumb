# Meminumb

**Lightweight, reliable memory layer for AI agents.**

Meminumb stores facts about users across sessions so your AI agent can remember context — with two guarantees that common libraries miss:

1. **Atomic writes** — a failure never leaves orphaned data behind
2. **Explicit outcomes** — `add()` always tells you what happened to every fact, and why

---

## The problem Meminumb solves

Most AI memory libraries swallow failures silently. If your database write partially succeeds, you get orphaned entries and duplicate facts on retry. And if a fact is skipped (duplicate, embed error), you never find out why.

Meminumb fixes this by design:

| Feature | Meminumb | Typical library |
|---|---|---|
| Atomic writes (no orphaned data) | ✅ | ❌ |
| Explicit outcome per fact | ✅ | ❌ |
| Content-addressed IDs (idempotent) | ✅ | ❌ |
| Zero mandatory external deps | ✅ | ❌ |
| Pluggable embedders | ✅ | varies |

---

## Install

```bash
pip install meminumb                    # core only (SQLite, no embeddings API)
pip install "meminumb[local]"           # + sentence-transformers (offline)
pip install "meminumb[openai]"          # + OpenAI embeddings API
pip install "meminumb[dev]"             # + pytest, ruff (for contributors)
```

---

## Quickstart

```python
from meminumb import Memory

mem = Memory()   # uses offline DummyEmbedder by default

result = mem.add(
    ["Alice prefers dark mode", "Alice is a backend developer"],
    user_id="alice",
)
print(result)
# AddResult(stored=2, skipped=0, failed=0)

# Try adding a duplicate
result2 = mem.add(["Alice prefers dark mode"], user_id="alice")
print(result2)
# AddResult(stored=0, skipped=1, failed=0)

skip = result2.skipped[0]
print(skip.reason, skip.existing_id)
# SkipReason.DUPLICATE  3f2a1b8e...

# Search
hits = mem.search("what does Alice like in her editor?", user_id="alice")
print(hits[0].content)
# Alice prefers dark mode
```

### With local embeddings (semantic search, offline)

```python
from meminumb import Memory
from meminumb.embedder import LocalEmbedder

mem = Memory(embedder=LocalEmbedder())   # downloads ~90 MB model on first run
mem.add(["Bob enjoys hiking on weekends"], user_id="bob")
hits = mem.search("outdoor activities", user_id="bob")
print(hits[0].content)
# Bob enjoys hiking on weekends
```

---

## API reference

### `Memory(store=None, embedder=None, db_path=":memory:")`

| Parameter | Default | Description |
|---|---|---|
| `store` | `SQLiteStore(":memory:")` | Storage backend |
| `embedder` | `DummyEmbedder()` | Embedding backend |
| `db_path` | `":memory:"` | SQLite file path (pass a real path to persist) |

### `Memory.add(facts, user_id="", agent_id="", metadata=None) → AddResult`

Returns an `AddResult` with three lists:

```python
result.stored   # List[MemoryItem]   — successfully written
result.skipped  # List[SkippedItem]  — not written, with reason
result.failed   # List[SkippedItem]  — write attempted, raised error
result.all_succeeded  # bool
```

Each `SkippedItem` has:
- `.content` — the original fact
- `.reason` — `SkipReason.DUPLICATE` | `EMBED_FAILED` | `INSERT_FAILED`
- `.existing_id` — set when reason is DUPLICATE
- `.error` — error message when reason is EMBED_FAILED or INSERT_FAILED

### Other methods

```python
mem.search(query, user_id="", top_k=5)   # → List[MemoryItem]
mem.get(memory_id)                        # → MemoryItem | None
mem.get_all(user_id="")                   # → List[MemoryItem]
mem.delete(memory_id)                     # → bool
mem.clear(user_id="")                     # → int (count deleted)
```

---

## Persistent storage

```python
mem = Memory(db_path="~/.meminumb/myapp.db")
```

The database file is created automatically. Use the same path across sessions to persist memory.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

MIT — see [LICENSE](LICENSE).
